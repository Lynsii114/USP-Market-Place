import os
import random

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "usp_backend.settings")

import django
import pytest
from django.test import Client

django.setup()

from marketplace.models import Item, User
from marketplace.schema import ensure_schema

ensure_schema()

client = Client()


@pytest.fixture(autouse=True)
def cleanup_test_records():
    yield
    Item.objects.filter(name__startswith="__test_").delete()
    User.objects.filter(username__startswith="__test_").delete()


def unique_student_payload():
    suffix = random.randint(10_000_000, 99_999_999)
    return {
        "username": f"__test_user_{suffix}",
        "email": f"s{suffix}@student.usp.ac.fj",
        "password": "secret123",
    }


def test_health_check():
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_signup_login_and_create_hidden_listing():
    payload = unique_student_payload()
    signup = client.post("/api/users/signup", payload, content_type="application/json")
    assert signup.status_code == 200
    user = signup.json()["user"]

    login = client.post(
        "/api/users/login",
        {"username": payload["username"], "password": payload["password"]},
        content_type="application/json",
    )
    assert login.status_code == 200
    assert login.json()["user"]["id"] == user["id"]

    listing = client.post(
        "/api/items",
        {
            "name": "__test_django_listing",
            "price": 10,
            "description": "Hidden test listing",
            "category": "Books",
            "contact": "test",
            "stock": 1,
            "seller_id": user["id"],
        },
        content_type="application/json",
    )
    assert listing.status_code == 200
    assert listing.json()["status"] == "available"
