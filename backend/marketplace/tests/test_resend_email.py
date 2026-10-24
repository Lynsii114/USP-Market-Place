import json
from io import BytesIO, StringIO
import secrets
from types import SimpleNamespace
from unittest.mock import patch
from urllib.error import HTTPError, URLError

from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import SimpleTestCase, override_settings

from marketplace import services
from marketplace.exceptions import ApiError


@override_settings(
    EMAIL_PROVIDER="resend",
    RESEND_FROM_EMAIL="USP Marketplace <no-reply@example.com>",
    FRONTEND_URL="http://localhost:5173",
    EMAIL_HOST="smtp.gmail.com",
    EMAIL_BACKEND="django.core.mail.backends.console.EmailBackend",
    EMAIL_TIMEOUT=20,
)
class ResendEmailTests(SimpleTestCase):
    def setUp(self):
        self.key = secrets.token_urlsafe(32)
        self.key_settings = override_settings(RESEND_API_KEY=self.key)
        self.key_settings.enable()
        self.addCleanup(self.key_settings.disable)
        self.urlopen = patch("marketplace.services.urlopen").start()
        self.addCleanup(patch.stopall)
        self.urlopen.return_value.__enter__.return_value.status = 200

    def payload(self):
        return json.loads(self.urlopen.call_args.args[0].data)

    def test_resend_uses_https_despite_old_smtp_settings(self):
        services.send_email("Subject", "Body", "student@example.com")
        request = self.urlopen.call_args.args[0]
        self.assertEqual(request.full_url, "https://api.resend.com/emails")
        self.assertEqual(request.method, "POST")
        self.assertEqual(request.get_header("Authorization"), f"Bearer {self.key}")
        self.assertEqual(self.payload(), {
            "from": "USP Marketplace <no-reply@example.com>",
            "to": ["student@example.com"], "subject": "Subject", "text": "Body",
        })
        self.assertEqual(self.urlopen.call_args.kwargs["timeout"], 20)

    def test_missing_key_or_sender_fails_without_fallback(self):
        for mode in ("local", "railway"):
            for name in ("RESEND_API_KEY", "RESEND_FROM_EMAIL"):
                with self.subTest(mode=mode, missing=name), override_settings(DATABASE_MODE=mode, **{name: ""}):
                    with self.assertRaises(ApiError) as error:
                        services.send_email("Subject", "Body", "student@example.com")
                    self.assertIn(name, error.exception.detail)
        self.urlopen.assert_not_called()

    @patch("smtplib.SMTP", side_effect=AssertionError("SMTP must never be contacted"))
    def test_legacy_provider_values_always_send_https_locally_and_online(self, smtp):
        for mode in ("local", "railway"):
            for provider in ("smtp", "auto", "console", "resend"):
                with self.subTest(mode=mode, provider=provider), override_settings(DATABASE_MODE=mode, EMAIL_PROVIDER=provider):
                    services.send_email("Reset password", "Reset code", "student@example.com")
                    self.assertEqual(self.urlopen.call_args.args[0].full_url, "https://api.resend.com/emails")
        self.assertEqual(self.urlopen.call_count, 8)
        smtp.assert_not_called()

    def test_provider_rejection_redacts_key(self):
        body = json.dumps({"message": f"Rejected {self.key}"}).encode()
        self.urlopen.side_effect = HTTPError("https://api.resend.com/emails", 403, "Forbidden", {}, BytesIO(body))
        with self.assertLogs("marketplace.email", level="ERROR") as logs:
            with self.assertRaises(ApiError) as error:
                services.send_email("Subject", "Body", "student@example.com")
        self.assertEqual(error.exception.status, 502)
        self.assertNotIn(self.key, str(error.exception))
        self.assertNotIn(self.key, "\n".join(logs.output))

    def test_network_failure_remains_an_email_error(self):
        self.urlopen.side_effect = URLError("unreachable")
        with self.assertLogs("marketplace.email", level="ERROR"):
            with self.assertRaises(ApiError) as error:
                services.send_email("Subject", "Body", "student@example.com")
        self.assertEqual(error.exception.status, 502)

    def test_verification_keeps_code_and_uses_environment_frontend(self):
        for frontend in ("http://localhost:5173", "https://usp-market-place.vercel.app"):
            with self.subTest(frontend=frontend), override_settings(FRONTEND_URL=frontend):
                registration = {"email": "student@example.com", "pending_token": "test-pending"}
                with patch("marketplace.services.secrets.randbelow", return_value=123456):
                    services.send_verification_code(registration)
                self.assertEqual(registration["code_hash"], services.hash_verification_code("123456"))
                self.assertEqual(registration["attempts"], 0)
                self.assertIn("123456", self.payload()["text"])
                self.assertIn(frontend, self.payload()["text"])

    def test_verification_recipient_is_the_entered_student_email(self):
        for email in ("S11111111@student.usp.ac.fj", "S22222222@student.usp.ac.fj"):
            with self.subTest(email=email):
                services.send_verification_code({"email": email, "pending_token": "test-pending"})
                self.assertEqual(self.payload()["to"], [email])

    @patch("marketplace.services.PasswordReset")
    @patch("marketplace.services.User")
    def test_reset_keeps_existing_code_flow_and_production_frontend(self, users, resets):
        users.objects.filter.return_value.first.return_value = SimpleNamespace(email="student@example.com")
        with override_settings(FRONTEND_URL="https://usp-market-place.vercel.app"):
            with patch("marketplace.services.secrets.randbelow", return_value=123456):
                services.request_password_reset({"email": "student@example.com"})
        self.assertIn("123456", self.payload()["text"])
        self.assertIn("https://usp-market-place.vercel.app", self.payload()["text"])
        self.assertEqual(resets.objects.create.call_args.kwargs["code_hash"], services.hash_verification_code("123456"))

    def test_account_notifications_use_same_sender(self):
        result = services.send_account_action_email("Notice", "Body", "student@example.com")
        self.assertEqual(result["email_status"], "sent")
        self.assertEqual(self.payload()["subject"], "Notice")
        self.assertEqual(self.urlopen.call_count, 1)

    def test_check_command_does_not_send_or_reveal_key(self):
        output = StringIO()
        with patch("django.db.backends.base.base.BaseDatabaseWrapper.ensure_connection", side_effect=AssertionError("No database access")):
            call_command("test_email_delivery", check_only=True, stdout=output)
        self.assertIn("API key hidden", output.getvalue())
        self.assertNotIn(self.key, output.getvalue())
        self.urlopen.assert_not_called()

    def test_delivery_command_sends_one_email_without_database_access(self):
        with patch("django.db.backends.base.base.BaseDatabaseWrapper.ensure_connection", side_effect=AssertionError("No database access")):
            call_command("test_email_delivery", to="operator@example.com", stdout=StringIO())
        self.assertEqual(self.urlopen.call_count, 1)
        self.assertIn("http://localhost:5173", self.payload()["text"])

    def test_delivery_command_rejects_invalid_recipient(self):
        with self.assertRaises(CommandError):
            call_command("test_email_delivery", to="invalid", stdout=StringIO())
        self.urlopen.assert_not_called()

    @override_settings(EMAIL_PROVIDER="auto")
    def test_check_command_reports_effective_https_transport(self):
        output = StringIO()
        call_command("test_email_delivery", check_only=True, stdout=output)
        self.assertIn("Resend is the only email transport", output.getvalue())
        self.assertNotIn(self.key, output.getvalue())
        self.urlopen.assert_not_called()
