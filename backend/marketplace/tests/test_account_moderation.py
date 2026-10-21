from datetime import timedelta
from unittest.mock import patch

import pyotp
from django.test import Client, TestCase, override_settings
from django.utils import timezone

from marketplace import services
from marketplace.authentication import issue_token, token_user
from marketplace.exceptions import ApiError
from marketplace.models import AdminNotification, Item, User, UserNotification


@override_settings(PASSWORD_HASHERS=["django.contrib.auth.hashers.MD5PasswordHasher"], EMAIL_PROVIDER="resend")
class AccountModerationTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create(username="admin", email="admin@example.com", password_hash="hash", role="admin", verified=True)
        self.student = User.objects.create(username="student", email="student@example.com", password_hash=services.hash_password("Password314!"), verified=True, authenticator_secret=pyotp.random_base32(), authenticator_enabled=True)
        self.client = Client(HTTP_AUTHORIZATION=f"Bearer {issue_token(self.admin)}")
        self.reason = "Repeated harassment of other marketplace users."

    def suspend(self, **changes):
        return self.client.post(f"/api/admin/students/{self.student.id}/suspend", {"reason": self.reason, "duration_hours": 24, **changes}, content_type="application/json")

    @patch("marketplace.services.send_email")
    def test_suspension_persists_reason_expiry_and_emails_without_user_notification(self, send):
        start = timezone.now()
        response = self.suspend()
        self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual(response.json()["email_status"], "sent")
        self.student.refresh_from_db()
        self.assertEqual(self.student.status, "suspended")
        self.assertEqual(self.student.suspension_reason, self.reason)
        self.assertLess(abs((self.student.suspended_until - start).total_seconds() - 86400), 5)
        subject, body, recipient, _ = send.call_args.args
        self.assertIn("suspended", subject)
        self.assertIn(self.reason, body)
        self.assertIn("24 hours", body)
        self.assertIn("Fiji time", body)
        self.assertEqual(recipient, self.student.email)
        self.assertTrue(body.startswith("Dear student,\n\n"))
        self.assertIn("temporarily suspended, effective immediately", body)
        self.assertIn("request a review", body)
        self.assertTrue(body.endswith("Kind regards,\nUSP Marketplace Administration Team"))
        self.assertEqual(send.call_count, 1)
        self.assertFalse(UserNotification.objects.filter(user_id=self.student.id).exists())
        self.assertTrue(AdminNotification.objects.filter(title="Account suspended").exists())

    @patch("marketplace.services.send_email")
    def test_suspension_blocks_login_and_token_then_expiry_restores_both(self, send):
        old_token = issue_token(self.student)
        self.suspend()
        with self.assertRaises(ApiError):
            services.login_user({"username": "student", "password": "Password314!"})
        with self.assertRaises(ApiError):
            token_user(old_token)
        User.objects.filter(id=self.student.id).update(suspended_until=timezone.now() - timedelta(seconds=1))
        login = services.login_user({"username": "student", "password": "Password314!"})
        self.assertTrue(login["authenticator_required"])
        self.assertEqual(token_user(old_token).status, "active")
        verified = services.verify_authenticator({"user_id": self.student.id, "login_challenge": login["login_challenge"], "code": pyotp.TOTP(self.student.authenticator_secret).now()})
        self.assertIn("access_token", verified)

    @patch("marketplace.services.send_email")
    def test_suspension_rejects_live_session_and_login_with_expiry_message(self, send):
        login = services.login_user({"username": "student", "password": "Password314!"})
        student_client = Client(HTTP_AUTHORIZATION=f"Bearer {issue_token(self.student)}")
        self.assertEqual(student_client.get("/api/users/session").status_code, 200)
        self.suspend()
        for path in ("/api/users/session", "/api/items", f"/api/users/{self.student.id}/notifications"):
            response = student_client.get(path)
            self.assertEqual(response.status_code, 403)
            self.assertEqual(response.json()["code"], "account_suspended")
            self.assertIn("Fiji time", response.json()["detail"])
            self.assertIn("check your email", response.json()["detail"])
        anonymous = Client()
        for path, body in (
            ("/api/users/login", {"username": "student", "password": "Password314!"}),
            ("/api/users/verify-authenticator", {"user_id": self.student.id, "login_challenge": login["login_challenge"], "code": pyotp.TOTP(self.student.authenticator_secret).now()}),
        ):
            response = anonymous.post(path, body, content_type="application/json")
            self.assertEqual(response.status_code, 403)
            self.assertEqual(response.json()["code"], "account_suspended")
        User.objects.filter(id=self.student.id).update(suspended_until=timezone.now() - timedelta(seconds=1))
        self.assertEqual(student_client.get("/api/users/session").status_code, 200)
        self.assertEqual(anonymous.get("/api/users/session").status_code, 401)

    @patch("marketplace.services.send_email")
    def test_expired_suspension_restores_access_on_authenticated_request(self, send):
        token = issue_token(self.student)
        User.objects.filter(id=self.student.id).update(status="suspended", suspended_until=timezone.now() - timedelta(seconds=1))
        response = Client(HTTP_AUTHORIZATION=f"Bearer {token}").get(f"/api/users/{self.student.id}/notifications")
        self.assertEqual(response.status_code, 200)
        self.student.refresh_from_db()
        self.assertEqual(self.student.status, "active")

    @patch("marketplace.services.send_email")
    def test_reason_and_duration_are_validated_before_mutation_or_email(self, send):
        for changes in ({"reason": ""}, {"reason": "   "}, {"reason": "short"}, {"reason": None}, {"reason": ["not", "text"]}, {"reason": "x" * 501}, {"duration_hours": 0}, {"duration_hours": 8761}, {"duration_hours": 1.5}, {"duration_hours": None}):
            with self.subTest(changes=changes):
                self.assertEqual(self.suspend(**changes).status_code, 422)
        send.assert_not_called()
        self.student.refresh_from_db()
        self.assertEqual(self.student.status, "active")

    @patch("marketplace.services.send_email")
    def test_manual_reactivation_clears_expiry_and_sends_email(self, send):
        self.suspend()
        reason = "The student's appeal has been reviewed and approved."
        response = self.client.post(f"/api/admin/students/{self.student.id}/reactivate", {"reason": reason}, content_type="application/json")
        self.assertEqual(response.status_code, 200, response.content)
        self.student.refresh_from_db()
        self.assertEqual(self.student.status, "active")
        self.assertIsNone(self.student.suspended_until)
        self.assertEqual(self.student.suspension_reason, "")
        self.assertIn("reactivated", send.call_args.args[0])
        self.assertIn(reason, send.call_args.args[1])
        self.assertTrue(UserNotification.objects.filter(user_id=self.student.id, title="Account reactivated", message__contains=reason).exists())
        self.assertTrue(AdminNotification.objects.filter(title="Account reactivated", message__contains=reason).exists())
        self.assertTrue(services.login_user({"username": "student", "password": "Password314!"})["authenticator_required"])

    @patch("marketplace.services.send_email")
    def test_reactivation_requires_reconsideration_reason_and_suspended_account(self, send):
        self.suspend()
        send.reset_mock()
        path = f"/api/admin/students/{self.student.id}/reactivate"
        self.assertEqual(self.client.post(path, {}, content_type="application/json").status_code, 422)
        self.student.refresh_from_db()
        self.assertEqual(self.student.status, "suspended")
        send.assert_not_called()
        body = {"reason": "The original suspension was applied in error."}
        self.assertEqual(self.client.post(path, body, content_type="application/json").status_code, 200)
        self.assertEqual(self.client.post(path, body, content_type="application/json").status_code, 409)
        self.assertEqual(send.call_count, 1)

    @patch("marketplace.services.send_email")
    def test_suspended_student_stays_visible_in_students_and_listing_seller(self, send):
        self.suspend()
        response = self.client.get("/api/admin/students")
        self.assertEqual(response.status_code, 200)
        student = next(row for row in response.json() if row["id"] == self.student.id)
        self.assertEqual(student["status"], "suspended")
        self.assertEqual(student["suspension_reason"], self.reason)
        item = Item.objects.create(name="Student book", price=10, description="Book", category="Books", contact="Library", stock=1, seller_id=self.student.id, seller_username=self.student.username)
        seller = services.serialize_admin_item(item)["seller"]
        self.assertEqual(seller["status"], "suspended")
        self.assertEqual(seller["suspension_reason"], self.reason)

    @patch("marketplace.services.send_email")
    def test_suspended_seller_listings_are_hidden_and_checkout_is_blocked(self, send):
        buyer = User.objects.create(username="buyer", email="buyer@example.com", password_hash="hash", verified=True)
        item = Item.objects.create(name="Campus textbook", price=20, stock=3, seller_id=self.student.id, seller_username=self.student.username)
        client = Client(HTTP_AUTHORIZATION=f"Bearer {issue_token(buyer)}")
        self.assertEqual(client.get(f"/api/items/{item.id}").status_code, 200)
        self.suspend()
        for viewer in (Client(), client):
            self.assertNotIn(item.id, [row["id"] for row in viewer.get("/api/items").json()])
            self.assertEqual(viewer.get(f"/api/items/{item.id}").status_code, 404)
            self.assertEqual(viewer.get(f"/api/users/{self.student.id}/items").json(), [])
        self.assertEqual(client.post(f"/api/items/{item.id}/conversation", {}, content_type="application/json").status_code, 404)
        checkout = {"checkout_id": "suspended-seller-cart", "payment_method": "cash", "delivery_method": "self_pickup", "items": [{"item_id": item.id, "quantity": 1}]}
        self.assertEqual(client.post("/api/checkout", checkout, content_type="application/json").status_code, 404)
        with self.assertRaises(ApiError) as error:
            services.purchase_item(item.id, buyer.id)
        self.assertEqual(error.exception.status, 404)
        item.refresh_from_db()
        self.assertEqual(item.stock, 3)
        self.assertEqual(item.status, "available")
        self.assertEqual(client.get("/api/users/session").status_code, 200)
        self.assertIn(item.id, [row["id"] for row in self.client.get("/api/admin/listings").json()])

    @patch("marketplace.services.send_email")
    def test_reactivation_restores_public_listings_without_restoring_hidden_items(self, send):
        item = Item.objects.create(name="Campus textbook", price=20, stock=3, seller_id=self.student.id, seller_username=self.student.username)
        hidden = Item.objects.create(name="Moderated listing", price=20, stock=1, status="hidden", removed_reason="Under review", seller_id=self.student.id, seller_username=self.student.username)
        self.suspend()
        response = self.client.post(f"/api/admin/students/{self.student.id}/reactivate", {"reason": "The appeal was reviewed and approved."}, content_type="application/json")
        self.assertEqual(response.status_code, 200)
        ids = [row["id"] for row in Client().get("/api/items").json()]
        self.assertIn(item.id, ids)
        self.assertNotIn(hidden.id, ids)
        hidden.refresh_from_db()
        self.assertEqual(hidden.status, "hidden")

    @patch("marketplace.services.send_email")
    def test_seller_listings_return_after_timed_suspension_expires(self, send):
        item = Item.objects.create(name="Campus textbook", price=20, stock=3, seller_id=self.student.id, seller_username=self.student.username)
        self.suspend()
        User.objects.filter(id=self.student.id).update(suspended_until=timezone.now() - timedelta(seconds=1))
        self.assertIn(item.id, [row["id"] for row in Client().get("/api/items").json()])
        self.assertEqual(Client().get(f"/api/items/{item.id}").status_code, 200)
        self.assertEqual(len(Client().get(f"/api/users/{self.student.id}/items").json()), 1)

    @patch("marketplace.services.send_email")
    def test_delete_requires_reason_then_emails_deleted_account_address(self, send):
        self.student.name = "Alex Kumar"
        self.student.save(update_fields=["name"])
        path = f"/api/admin/students/{self.student.id}"
        self.assertEqual(self.client.delete(path, {}, content_type="application/json").status_code, 422)
        for reason in ("", "   ", "short", "x" * 501, None, ["not", "text"]):
            with self.subTest(reason=reason):
                self.assertEqual(self.client.delete(path, {"reason": reason}, content_type="application/json").status_code, 422)
        self.assertTrue(User.objects.filter(id=self.student.id).exists())
        send.assert_not_called()
        Item.objects.create(name="Student book", price=10, description="Book", category="Books", contact="Library", stock=1, seller_id=self.student.id, seller_username=self.student.username)
        with patch("marketplace.services.notify_user") as notify_user:
            response = self.client.delete(path, {"reason": self.reason}, content_type="application/json")
        notify_user.assert_not_called()
        self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual(response.json()["email_status"], "sent")
        self.assertFalse(User.objects.filter(id=self.student.id).exists())
        self.assertFalse(Item.objects.filter(seller_id=self.student.id).exists())
        self.assertEqual(send.call_args.args[2], "student@example.com")
        self.assertIn(self.reason, send.call_args.args[1])
        self.assertTrue(send.call_args.args[1].startswith("Dear Alex Kumar,\n\n"))
        self.assertIn("permanently deleted", send.call_args.args[1])
        self.assertTrue(send.call_args.args[1].endswith("Kind regards,\nUSP Marketplace Administration Team"))
        self.assertEqual(send.call_count, 1)
        self.assertFalse(UserNotification.objects.filter(user_id=self.student.id).exists())
        self.assertTrue(AdminNotification.objects.filter(title="Student account deleted", message__contains=self.reason).exists())

    @patch("marketplace.services.send_email", side_effect=RuntimeError("Resend unavailable"))
    def test_email_failure_is_reported_without_reversing_action(self, send):
        response = self.suspend()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["email_status"], "failed")
        self.student.refresh_from_db()
        self.assertEqual(self.student.status, "suspended")
        self.assertFalse(UserNotification.objects.filter(user_id=self.student.id).exists())

    @override_settings(EMAIL_PROVIDER="console", EMAIL_BACKEND="django.core.mail.backends.console.EmailBackend")
    @patch("marketplace.services.send_email")
    def test_legacy_console_setting_does_not_change_provider_acceptance(self, send):
        self.assertEqual(self.suspend().json()["email_status"], "sent")

    @patch("marketplace.services.send_email")
    def test_student_cannot_suspend_or_delete_accounts(self, send):
        self.client = Client(HTTP_AUTHORIZATION=f"Bearer {issue_token(self.student)}")
        self.assertEqual(self.suspend().status_code, 403)
        self.assertEqual(self.client.post(f"/api/admin/students/{self.student.id}/reactivate", {"reason": self.reason}, content_type="application/json").status_code, 403)
        self.assertEqual(self.client.delete(f"/api/admin/students/{self.student.id}", {"reason": self.reason}, content_type="application/json").status_code, 403)
        send.assert_not_called()
