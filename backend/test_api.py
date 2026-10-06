import os
import random
import re
import smtplib
from unittest.mock import MagicMock, patch

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "usp_backend.settings")

import django
import pytest
from django.test import Client
from django.test.utils import override_settings

django.setup()

from marketplace.models import Item, PasswordReset, PendingRegistration, User
from marketplace.schema import ensure_schema

ensure_schema()

client = Client()


@pytest.fixture(autouse=True)
def cleanup_test_records():
    yield
    Item.objects.filter(name__startswith="__test_").delete()
    User.objects.filter(username__startswith="__test_").delete()
    PendingRegistration.objects.filter(username__startswith="__test_").delete()
    PasswordReset.objects.filter(user__username__startswith="__test_").delete()


def unique_student_payload():
    suffix = random.randint(10_000_000, 99_999_999)
    return {
        "username": f"__test_user_{suffix}",
        "email": f"S{suffix}@student.usp.ac.fj",
        "password": "secret123",
    }


def test_health_check():
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


@override_settings(ALLOW_NON_USP_EMAILS=True)
def test_signup_login_and_create_hidden_listing():
    payload = unique_student_payload()
    payload["email"] = f"test{payload['username'].rsplit('_', 1)[-1]}@gmail.com"
    with patch("marketplace.services.send_email") as send_email:
        signup = client.post("/api/users/signup", payload, content_type="application/json")
        verification_message = send_email.call_args.args[1]

    assert signup.status_code == 200
    assert signup.json()["verification_required"] is True
    assert signup.json()["user"] is None
    assert not User.objects.filter(email=payload["email"]).exists()
    assert PendingRegistration.objects.filter(email=payload["email"]).exists()

    code = re.search(r"\b\d{6}\b", verification_message).group()
    verification = client.post(
        "/api/users/verify-email",
        {"email": payload["email"], "code": code},
        content_type="application/json",
    )
    assert verification.status_code == 200
    assert verification.json()["authenticator_setup_required"] is True
    user = User.objects.get(id=verification.json()["user_id"])
    assert User.objects.filter(email=payload["email"]).exists()
    assert not PendingRegistration.objects.filter(email=payload["email"]).exists()

    login = client.post(
        "/api/users/login",
        {"username": payload["username"], "password": payload["password"]},
        content_type="application/json",
    )
    assert login.status_code == 200
    login_data = login.json()
    assert login_data["authenticator_setup_required"] is True
    assert login_data["authenticator_qr"].startswith("data:image/png;base64,")
    authenticator = client.post(
        "/api/users/verify-authenticator",
        {"user_id": login_data["user_id"], "code": __import__("pyotp").TOTP(login_data["authenticator_secret"]).now()},
        content_type="application/json",
    )
    assert authenticator.status_code == 200
    assert authenticator.json()["user"]["id"] == user.id

    listing = client.post(
        "/api/items",
        {
            "name": "__test_django_listing",
            "price": 10,
            "description": "Hidden test listing",
            "category": "Books",
            "contact": "test",
            "stock": 1,
            "seller_id": user.id,
        },
        content_type="application/json",
    )
    assert listing.status_code == 200
    assert listing.json()["status"] == "available"


def test_cancel_verification_removes_pending_registration():
    payload = unique_student_payload()
    with patch("marketplace.services.send_email"):
        signup = client.post("/api/users/signup", payload, content_type="application/json")

    assert signup.status_code == 200
    assert PendingRegistration.objects.filter(email=payload["email"]).exists()
    assert not User.objects.filter(email=payload["email"]).exists()

    cancel = client.post(
        "/api/users/cancel-verification",
        {"email": payload["email"]},
        content_type="application/json",
    )
    assert cancel.status_code == 200
    assert cancel.json()["deleted"] is True
    assert not PendingRegistration.objects.filter(email=payload["email"]).exists()


@override_settings(ALLOW_NON_USP_EMAILS=False)
def test_signup_rejects_non_usp_email_when_testing_option_is_disabled():
    payload = unique_student_payload()
    payload["email"] = "person@gmail.com"

    response = client.post("/api/users/signup", payload, content_type="application/json")

    assert response.status_code == 422
    assert "USP student email" in response.json()["detail"]


@override_settings(ALLOW_NON_USP_EMAILS=True)
def test_signup_rejects_invalid_email_format():
    payload = unique_student_payload()
    payload["email"] = "not-an-email"

    response = client.post("/api/users/signup", payload, content_type="application/json")

    assert response.status_code == 422
    assert response.json()["detail"] == "Enter a valid email address"


@override_settings(ALLOW_NON_USP_EMAILS=True, EMAIL_HOST="smtp.gmail.com")
def test_signup_returns_json_error_when_smtp_fails():
    payload = unique_student_payload()
    payload["email"] = "person@gmail.com"

    with patch(
        "marketplace.services.send_mail",
        side_effect=smtplib.SMTPAuthenticationError(535, b"authentication failed"),
    ):
        response = client.post("/api/users/signup", payload, content_type="application/json")

    assert response.status_code == 502
    assert response.json()["detail"] == (
        "Gmail rejected the SMTP login. Check EMAIL_HOST_USER and use a current "
        "16-character Google App Password for EMAIL_HOST_PASSWORD."
    )
    assert not PendingRegistration.objects.filter(email=payload["email"]).exists()


@override_settings(ALLOW_NON_USP_EMAILS=True, EMAIL_HOST="smtp.gmail.com")
def test_signup_identifies_smtp_connection_failures_without_exposing_details():
    payload = unique_student_payload()
    payload["email"] = "person@gmail.com"

    with patch("marketplace.services.send_mail", side_effect=smtplib.SMTPServerDisconnected("closed")):
        response = client.post("/api/users/signup", payload, content_type="application/json")

    assert response.status_code == 502
    assert response.json()["detail"] == "SMTP email delivery failed (SMTPServerDisconnected). Check the backend terminal for details."
    assert not PendingRegistration.objects.filter(email=payload["email"]).exists()


@override_settings(
    EMAIL_PROVIDER="resend",
    EMAIL_HOST="smtp.gmail.com",
    RESEND_API_KEY="test-api-key",
    RESEND_FROM_EMAIL="sender@example.com",
)
def test_email_provider_can_select_resend_even_when_smtp_is_configured():
    from marketplace.services import send_email

    response = MagicMock()
    response.__enter__.return_value.status = 200
    with patch("marketplace.services.urlopen", return_value=response) as urlopen:
        send_email("Test", "Test message", "recipient@example.com")

    request = urlopen.call_args.args[0]
    assert request.full_url == "https://api.resend.com/emails"
    assert request.get_header("Authorization") == "Bearer test-api-key"


@override_settings(EMAIL_PROVIDER="resend", RESEND_API_KEY="")
def test_resend_provider_reports_missing_api_key():
    from marketplace.exceptions import ApiError
    from marketplace.services import send_email

    with pytest.raises(ApiError, match="EMAIL_PROVIDER=resend requires RESEND_API_KEY"):
        send_email("Test", "Test message", "recipient@example.com")


@override_settings(
    EMAIL_BACKEND="django.core.mail.backends.smtp.EmailBackend",
    EMAIL_HOST="smtp.gmail.com",
    EMAIL_PORT=465,
    EMAIL_USE_TLS=False,
    EMAIL_USE_SSL=True,
)
def test_gmail_implicit_ssl_configuration_is_supported():
    from django.core.mail import get_connection

    connection = get_connection()

    assert connection.host == "smtp.gmail.com"
    assert connection.port == 465
    assert connection.use_tls is False
    assert connection.use_ssl is True


def test_unexpected_api_errors_return_json_and_log_traceback(caplog):
    with patch("marketplace.views.services.login_user", side_effect=RuntimeError("test failure")):
        response = client.post(
            "/api/users/login",
            {"username": "missing", "password": "secret"},
            content_type="application/json",
        )

    assert response.status_code == 500
    assert response.json()["detail"] == "Unexpected server error. Check the backend terminal for details."
    assert "Unexpected error while handling marketplace API request" in caplog.text
    assert "RuntimeError: test failure" in caplog.text


def test_password_reset_code_changes_password_once():
    payload = unique_student_payload()
    user = User.objects.create(
        username=payload["username"],
        student_id=payload["email"].split("@", 1)[0],
        email=payload["email"],
        password_hash=__import__("marketplace.services", fromlist=["hash_password"]).hash_password("oldpass"),
        authenticator_secret="JBSWY3DPEHPK3PXP",
        authenticator_enabled=True,
    )

    with patch("marketplace.services.send_email") as send_email:
        request = client.post(
            "/api/users/request-password-reset",
            {"email": payload["email"]},
            content_type="application/json",
        )
        reset_message = send_email.call_args.args[1]

    assert request.status_code == 200
    code = re.search(r"\b\d{6}\b", reset_message).group()
    reset = client.post(
        "/api/users/reset-password",
        {"email": payload["email"], "code": code, "password": "newpass"},
        content_type="application/json",
    )
    assert reset.status_code == 200
    assert User.objects.get(id=user.id).password_hash != __import__("marketplace.services", fromlist=["hash_password"]).hash_password("oldpass")

    reused = client.post(
        "/api/users/reset-password",
        {"email": payload["email"], "code": code, "password": "anotherpass"},
        content_type="application/json",
    )
    assert reused.status_code == 400
