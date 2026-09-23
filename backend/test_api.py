import os
import random
import re
from unittest.mock import patch

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "usp_backend.settings")

import django
import pytest
from django.test import Client

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


def test_signup_login_and_create_hidden_listing():
    payload = unique_student_payload()
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


def test_signup_rejects_non_usp_email():
    payload = unique_student_payload()
    payload["email"] = "person@gmail.com"

    response = client.post("/api/users/signup", payload, content_type="application/json")

    assert response.status_code == 422
    assert "USP student email" in response.json()["detail"]


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
