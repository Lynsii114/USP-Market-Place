import os
import random
import re
import smtplib
import ssl
from datetime import timedelta
from unittest.mock import patch

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "usp_backend.settings")

import django
import pytest
from django.test import Client
from django.test import override_settings
from django.utils import timezone

django.setup()

from marketplace.models import AdminNotification, Item, PasswordReset, PendingRegistration, Purchase, RatingReview, User, UserNotification
from marketplace.exceptions import ApiError
from marketplace.schema import ensure_schema
from marketplace.services import PENDING_REGISTRATIONS, VERIFICATION_CODE_TTL, hash_verification_code, send_email

ensure_schema()

client = Client()


@pytest.fixture(autouse=True)
def cleanup_test_records():
    PENDING_REGISTRATIONS.clear()
    yield
    PENDING_REGISTRATIONS.clear()
    AdminNotification.objects.filter(actor_username__startswith="__test_").delete()
    UserNotification.objects.filter(actor_username__startswith="__test_").delete()
    RatingReview.objects.filter(reviewer_username__startswith="__test_").delete()
    Purchase.objects.filter(item_name__startswith="__test_").delete()
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
    assert signup.json()["pending_token"]
    assert signup.json()["user"] is None
    assert not User.objects.filter(email=payload["email"]).exists()
    assert not PendingRegistration.objects.filter(email=payload["email"]).exists()

    code = re.search(r"\b\d{6}\b", verification_message).group()
    assert f"Your 6-digit verification code is: {code}" in verification_message
    assert "USP Marketplace System" in verification_message
    verification = client.post(
        "/api/users/verify-email",
        {"email": payload["email"], "code": code, "pending_token": signup.json()["pending_token"]},
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


def test_public_items_show_listings_from_all_accounts():
    suffix = random.randint(10_000_000, 99_999_999)
    first_user = User.objects.create(
        username=f"__test_seller_one_{suffix}",
        student_id=f"S{suffix}",
        email=f"S{suffix}@student.usp.ac.fj",
        password_hash="hash",
        status="active",
        verified=True,
    )
    second_user = User.objects.create(
        username=f"__test_seller_two_{suffix}",
        student_id=f"S{suffix + 1}",
        email=f"S{suffix + 1}@student.usp.ac.fj",
        password_hash="hash",
        status="active",
        verified=True,
    )
    created_items = []

    try:
        for seller, name in [
            (first_user, "Scientific Calculator"),
            (second_user, f"Cross Account Textbook {suffix}"),
        ]:
            response = client.post(
                "/api/items",
                {
                    "name": name,
                    "price": 10,
                    "description": "Cross-account visibility test listing",
                    "category": "Books",
                    "contact": "test",
                    "stock": 1,
                    "seller_id": seller.id,
                },
                content_type="application/json",
            )
            assert response.status_code == 200
            created_items.append(response.json())

        items = client.get("/api/items")

        assert items.status_code == 200
        listed_item_ids = {item["id"] for item in items.json()}
        assert {item["id"] for item in created_items}.issubset(listed_item_ids)
    finally:
        Item.objects.filter(id__in=[item["id"] for item in created_items]).delete()


def create_active_test_user(prefix, suffix):
    return User.objects.create(
        username=f"__test_{prefix}_{suffix}",
        student_id=f"S{suffix}",
        email=f"S{suffix}@student.usp.ac.fj",
        password_hash="hash",
        status="active",
        verified=True,
    )


def create_test_item(seller, suffix, name=None):
    return Item.objects.create(
        name=name or f"__test_notification_item_{suffix}",
        price=10,
        description="Notification test listing",
        category="Books",
        contact="test",
        stock=1,
        status="available",
        seller_id=seller.id,
        seller_username=seller.username,
    )


def test_order_notifications_go_to_buyer_and_seller_not_admin():
    suffix = random.randint(10_000_000, 99_999_999)
    buyer = create_active_test_user("buyer", suffix)
    seller = create_active_test_user("seller", suffix + 1)
    item = create_test_item(seller, suffix)

    response = client.post(f"/api/items/{item.id}/purchase?buyer_id={buyer.id}", {}, content_type="application/json")

    assert response.status_code == 200
    buyer_notifications = client.get(f"/api/users/{buyer.id}/notifications")
    seller_notifications = client.get(f"/api/users/{seller.id}/notifications")
    assert buyer_notifications.status_code == 200
    assert seller_notifications.status_code == 200
    assert any(notification["title"] == "Order confirmed" for notification in buyer_notifications.json())
    assert any(
        notification["title"] == "New order placed" and notification["category"] == "sale"
        for notification in seller_notifications.json()
    )
    assert not AdminNotification.objects.filter(actor_username=buyer.username, category="checkout").exists()


def test_cash_checkout_records_success_and_decrements_purchased_quantity():
    suffix = random.randint(10_000_000, 99_999_999)
    buyer = create_active_test_user("quantity_buyer", suffix)
    seller = create_active_test_user("quantity_seller", suffix + 1)
    item = create_test_item(seller, suffix, name=f"__test_quantity_item_{suffix}")
    item.stock = 3
    item.save(update_fields=["stock"])

    response = client.post(
        f"/api/items/{item.id}/purchase?buyer_id={buyer.id}",
        {
            "quantity": 2,
            "payment_method": "cash",
            "delivery_method": "self_pickup",
        },
        content_type="application/json",
    )

    assert response.status_code == 200
    item.refresh_from_db()
    assert item.stock == 1
    assert item.status == "available"
    assert item.reserved_buyer_id is None
    purchase = Purchase.objects.get(item_id=item.id, buyer_id=buyer.id)
    assert purchase.quantity == 2
    assert purchase.total_amount == 20
    assert purchase.order_stage == "payment_confirmed"
    assert purchase.payment_status == "approved"
    purchase_history = client.get(f"/api/users/{buyer.id}/purchases")
    assert purchase_history.status_code == 200
    assert any(order["item_id"] == item.id and order["quantity"] == 2 for order in purchase_history.json())


@pytest.mark.parametrize(("payment_method", "payment_details"), [
    ("mycash", {"phone_number": "+679 9000000", "authorization_code": "123456"}),
    ("mpaisa", {"phone_number": "+679 8111222", "authorization_code": "123456"}),
    ("visa", {
        "cardholder_name": "Demo Buyer",
        "card_number": "4242 4242 4242 4242",
        "expiry": "12/30",
        "security_code": "123",
    }),
    ("cash", {}),
])
def test_checkout_simulates_success_and_marks_listing_sold(payment_method, payment_details):
    suffix = random.randint(10_000_000, 99_999_999)
    buyer = create_active_test_user("checkout_buyer", suffix)
    seller = create_active_test_user("checkout_seller", suffix + 1)
    item = create_test_item(seller, suffix, name=f"__test_checkout_item_{suffix}")

    response = client.post(
        f"/api/checkout?buyer_id={buyer.id}",
        {
            "payment_method": payment_method,
            "delivery_method": "self_pickup",
            "payment_details": payment_details,
            "items": [{"item_id": item.id, "quantity": 1}],
        },
        content_type="application/json",
    )

    assert response.status_code == 200
    assert response.json()["payment"]["status"] == "approved"
    assert response.json()["payment"]["method"] == payment_method
    assert response.json()["payment"]["reference"].startswith("DEMO-")
    assert response.json()["total"] == 10
    purchase = Purchase.objects.get(item_id=item.id, buyer_id=buyer.id)
    assert purchase.payment_status == "approved"
    assert purchase.payment_method == payment_method
    assert purchase.payment_reference == response.json()["payment"]["reference"]
    item.refresh_from_db()
    assert item.stock == 0
    assert item.status == "sold"
    history = client.get(f"/api/users/{buyer.id}/purchases")
    assert history.status_code == 200
    assert history.json()[0]["payment_status"] == "approved"


@pytest.mark.parametrize(("payment_method", "payment_details"), [
    ("mpaisa", {"phone_number": "+679 8111222", "authorization_code": "123456"}),
    ("mycash", {"phone_number": "+679 9000000", "authorization_code": "123456"}),
    ("visa", {
        "cardholder_name": "Demo Buyer",
        "card_number": "4242 4242 4242 4242",
        "expiry": "12/30",
        "security_code": "123",
    }),
    ("cash", {}),
])
def test_forced_payment_failure_does_not_create_order_or_change_stock(payment_method, payment_details):
    suffix = random.randint(10_000_000, 99_999_999)
    buyer = create_active_test_user("forced_failure_buyer", suffix)
    seller = create_active_test_user("forced_failure_seller", suffix + 1)
    item = create_test_item(seller, suffix, name=f"__test_forced_failure_{suffix}")
    item.stock = 3
    item.save(update_fields=["stock"])

    response = client.post(
        f"/api/checkout?buyer_id={buyer.id}",
        {
            "payment_method": payment_method,
            "payment_details": payment_details,
            "delivery_method": "self_pickup",
            "force_failure": True,
            "items": [{"item_id": item.id, "quantity": 1}],
        },
        content_type="application/json",
    )

    assert response.status_code == 402
    assert "simulated failure" in response.json()["detail"]
    assert Purchase.objects.filter(item_id=item.id, buyer_id=buyer.id).count() == 0
    item.refresh_from_db()
    assert item.stock == 3
    assert item.status == "available"


@pytest.mark.parametrize(("payment_method", "payment_details"), [
    ("visa", {
        "cardholder_name": "Demo Buyer",
        "card_number": "4000 0000 0000 9995",
        "expiry": "12/30",
        "security_code": "123",
    }),
    ("mycash", {"phone_number": "+679 9000000", "authorization_code": "000000"}),
    ("mpaisa", {"phone_number": "+679 8111222", "authorization_code": "000000"}),
])
def test_insufficient_funds_failure_preserves_stock_and_creates_no_order(payment_method, payment_details):
    suffix = random.randint(10_000_000, 99_999_999)
    buyer = create_active_test_user("insufficient_buyer", suffix)
    seller = create_active_test_user("insufficient_seller", suffix + 1)
    item = create_test_item(seller, suffix, name=f"__test_insufficient_{suffix}")
    response = client.post(
        f"/api/checkout?buyer_id={buyer.id}",
        {
            "payment_method": payment_method,
            "payment_details": payment_details,
            "delivery_method": "self_pickup",
            "items": [{"item_id": item.id, "quantity": 1}],
        },
        content_type="application/json",
    )

    assert response.status_code == 402
    assert "insufficient funds" in response.json()["detail"]
    assert Purchase.objects.filter(item_id=item.id, buyer_id=buyer.id).count() == 0
    item.refresh_from_db()
    assert item.stock == 1
    assert item.status == "available"


def test_failed_multi_item_payment_does_not_partially_create_orders_or_reduce_stock():
    suffix = random.randint(10_000_000, 99_999_999)
    buyer = create_active_test_user("multi_failure_buyer", suffix)
    seller = create_active_test_user("multi_failure_seller", suffix + 1)
    first_item = create_test_item(seller, suffix, name=f"__test_multi_first_{suffix}")
    second_item = create_test_item(seller, suffix + 2, name=f"__test_multi_second_{suffix}")

    response = client.post(
        f"/api/checkout?buyer_id={buyer.id}",
        {
            "payment_method": "mycash",
            "payment_details": {"phone_number": "+679 9000000", "authorization_code": "000000"},
            "delivery_method": "delivery",
            "force_failure": False,
            "items": [
                {"item_id": first_item.id, "quantity": 1},
                {"item_id": second_item.id, "quantity": 1},
            ],
        },
        content_type="application/json",
    )

    assert response.status_code == 402
    assert Purchase.objects.filter(buyer_id=buyer.id, item_id__in=[first_item.id, second_item.id]).count() == 0
    first_item.refresh_from_db()
    second_item.refresh_from_db()
    assert first_item.stock == second_item.stock == 1
    assert first_item.status == second_item.status == "available"


def test_checkout_cash_payment_is_simulated_and_marks_listing_sold():
    suffix = random.randint(10_000_000, 99_999_999)
    buyer = create_active_test_user("cash_buyer", suffix)
    seller = create_active_test_user("cash_seller", suffix + 1)
    item = create_test_item(seller, suffix, name=f"__test_cash_item_{suffix}")

    response = client.post(
        f"/api/checkout?buyer_id={buyer.id}",
        {
            "payment_method": "cash",
            "delivery_method": "delivery",
            "items": [{"item_id": item.id, "quantity": 1}],
        },
        content_type="application/json",
    )

    assert response.status_code == 200
    assert response.json()["payment"]["status"] == "approved"
    assert response.json()["total"] == 15
    purchase = Purchase.objects.get(item_id=item.id, buyer_id=buyer.id)
    assert purchase.order_stage == "payment_confirmed"
    assert purchase.payment_status == "approved"
    assert purchase.payment_reference.startswith("DEMO-")
    assert purchase.total_amount == 15
    item.refresh_from_db()
    assert item.status == "sold"
    assert item.stock == 0
    assert item.reserved_buyer_id is None


def test_cash_order_is_ready_for_seller_progress_after_simulated_payment():
    suffix = random.randint(10_000_000, 99_999_999)
    buyer = create_active_test_user("cash_confirm_buyer", suffix)
    seller = create_active_test_user("cash_confirm_seller", suffix + 1)
    item = create_test_item(seller, suffix, name=f"__test_cash_confirm_item_{suffix}")

    checkout = client.post(
        f"/api/checkout?buyer_id={buyer.id}",
        {
            "payment_method": "cash",
            "delivery_method": "self_pickup",
            "items": [{"item_id": item.id, "quantity": 1}],
        },
        content_type="application/json",
    )
    purchase = Purchase.objects.get(item_id=item.id, buyer_id=buyer.id)
    stage_before_payment = client.post(
        f"/api/orders/{purchase.id}/seller-stage",
        {"seller_id": seller.id, "stage": "preparing_item"},
        content_type="application/json",
    )
    rejected_confirmation = client.post(
        f"/api/orders/{purchase.id}/cash-payment",
        {"seller_id": buyer.id},
        content_type="application/json",
    )
    confirmed = client.post(
        f"/api/orders/{purchase.id}/cash-payment",
        {"seller_id": seller.id},
        content_type="application/json",
    )

    assert checkout.status_code == 200
    assert stage_before_payment.status_code == 200
    assert rejected_confirmation.status_code == 403
    assert confirmed.status_code == 400
    assert purchase.payment_status == "approved"
    assert purchase.payment_reference.startswith("DEMO-")
    preparing = client.post(
        f"/api/orders/{purchase.id}/seller-stage",
        {"seller_id": seller.id, "stage": "preparing_item"},
        content_type="application/json",
    )
    assert preparing.status_code == 200
    item.refresh_from_db()
    assert item.status == "sold"
    assert item.stock == 0
    buyer_history = client.get(f"/api/users/{buyer.id}/purchases")
    assert buyer_history.status_code == 200
    assert buyer_history.json()[0]["payment_status"] == "approved"
    assert buyer_history.json()[0]["payment_reference"].startswith("DEMO-")


def test_failed_cash_checkout_creates_no_order_and_leaves_listing_available():
    suffix = random.randint(10_000_000, 99_999_999)
    buyer = create_active_test_user("cash_cancel_buyer", suffix)
    seller = create_active_test_user("cash_cancel_seller", suffix + 1)
    item = create_test_item(seller, suffix, name=f"__test_cash_cancel_item_{suffix}")
    item.stock = 3
    item.save(update_fields=["stock"])

    response = client.post(
        f"/api/checkout?buyer_id={buyer.id}",
        {
            "payment_method": "cash",
            "delivery_method": "self_pickup",
            "force_failure": True,
            "items": [{"item_id": item.id, "quantity": 2}],
        },
        content_type="application/json",
    )
    assert response.status_code == 402
    assert Purchase.objects.filter(item_id=item.id, buyer_id=buyer.id).count() == 0
    item.refresh_from_db()
    assert item.stock == 3
    assert item.status == "available"


def test_sold_listing_cannot_be_purchased_twice():
    suffix = random.randint(10_000_000, 99_999_999)
    buyer = create_active_test_user("cash_duplicate_buyer", suffix)
    seller = create_active_test_user("cash_duplicate_seller", suffix + 1)
    item = create_test_item(seller, suffix, name=f"__test_cash_duplicate_item_{suffix}")
    payload = {
        "payment_method": "cash",
        "delivery_method": "self_pickup",
        "items": [{"item_id": item.id, "quantity": 1}],
    }

    first_checkout = client.post(
        f"/api/checkout?buyer_id={buyer.id}",
        payload,
        content_type="application/json",
    )
    repeated_checkout = client.post(
        f"/api/checkout?buyer_id={buyer.id}",
        {
            **payload,
            "payment_method": "mycash",
        },
        content_type="application/json",
    )

    assert first_checkout.status_code == 200
    assert repeated_checkout.status_code == 400
    assert Purchase.objects.filter(item_id=item.id, buyer_id=buyer.id).count() == 1


def test_cash_checkout_decrements_only_purchased_quantity():
    suffix = random.randint(10_000_000, 99_999_999)
    buyer = create_active_test_user("cash_quantity_buyer", suffix)
    seller = create_active_test_user("cash_quantity_seller", suffix + 1)
    item = create_test_item(seller, suffix, name=f"__test_cash_quantity_item_{suffix}")
    item.stock = 3
    item.save(update_fields=["stock"])

    checkout = client.post(
        f"/api/checkout?buyer_id={buyer.id}",
        {
            "payment_method": "cash",
            "delivery_method": "self_pickup",
            "items": [{"item_id": item.id, "quantity": 2}],
        },
        content_type="application/json",
    )
    assert checkout.status_code == 200
    assert checkout.json()["payment"]["status"] == "approved"
    item.refresh_from_db()
    assert item.stock == 1
    assert item.status == "available"


def test_seller_reviews_are_publicly_viewable():
    suffix = random.randint(10_000_000, 99_999_999)
    buyer = create_active_test_user("review_buyer", suffix)
    seller = create_active_test_user("review_seller", suffix + 1)
    item = create_test_item(seller, suffix, name=f"__test_review_item_{suffix}")
    review = RatingReview.objects.create(
        reviewer_id=buyer.id,
        reviewer_username=buyer.username,
        item_id=item.id,
        item_name=item.name,
        seller_id=seller.id,
        seller_username=seller.username,
        rating=4,
        review="Helpful seller and smooth pickup",
    )

    response = client.get(f"/api/users/{seller.id}/reviews")

    assert response.status_code == 200
    data = response.json()
    assert data["seller"]["username"] == seller.username
    assert data["average_rating"] == 4
    assert data["review_count"] == 1
    assert data["reviews"][0]["id"] == review.id


def test_admin_dashboard_total_sales_uses_purchase_totals():
    suffix = random.randint(10_000_000, 99_999_999)
    admin = User.objects.create(
        username=f"__test_admin_{suffix}",
        student_id=f"A{suffix}",
        email=f"admin{suffix}@student.usp.ac.fj",
        password_hash="hash",
        role="admin",
        status="active",
        verified=True,
    )
    buyer = create_active_test_user("dashboard_buyer", suffix + 1)
    seller = create_active_test_user("dashboard_seller", suffix + 2)
    item = Item.objects.create(
        name=f"Dashboard Sale Item {suffix}",
        price=15,
        description="Dashboard total sales item",
        category="Books",
        contact="test",
        stock=4,
        status="available",
        seller_id=seller.id,
        seller_username=seller.username,
    )
    cancelled_item = Item.objects.create(
        name=f"Dashboard Cancelled Item {suffix}",
        price=99,
        description="Cancelled sale should not count",
        category="Books",
        contact="test",
        stock=1,
        status="available",
        seller_id=seller.id,
        seller_username=seller.username,
    )

    try:
        initial_dashboard = client.get(f"/api/admin/dashboard?admin_id={admin.id}")
        assert initial_dashboard.status_code == 200
        initial_total_sales = initial_dashboard.json()["total_sales"]
        initial_todays_sales = initial_dashboard.json()["todays_sales"]

        purchase_response = client.post(
            f"/api/items/{item.id}/purchase?buyer_id={buyer.id}",
            {"quantity": 2, "payment_method": "cash", "delivery_method": "self_pickup"},
            content_type="application/json",
        )
        cancelled_response = client.post(
            f"/api/items/{cancelled_item.id}/purchase?buyer_id={buyer.id}",
            {"payment_method": "cash", "delivery_method": "self_pickup"},
            content_type="application/json",
        )
        assert purchase_response.status_code == 200
        assert cancelled_response.status_code == 200
        cancelled_purchase = Purchase.objects.get(item_id=cancelled_item.id, buyer_id=buyer.id)
        cancel_response = client.post(
            f"/api/orders/{cancelled_purchase.id}/cancel",
            {"user_id": buyer.id},
            content_type="application/json",
        )
        assert cancel_response.status_code == 200

        dashboard = client.get(f"/api/admin/dashboard?admin_id={admin.id}")

        assert dashboard.status_code == 200
        data = dashboard.json()
        assert data["total_sales"] == initial_total_sales + 30
        assert data["todays_sales"] == initial_todays_sales + 30
    finally:
        Purchase.objects.filter(item_id__in=[item.id, cancelled_item.id]).delete()
        Item.objects.filter(id__in=[item.id, cancelled_item.id]).delete()


def test_cancel_order_notifies_buyer_and_seller_and_marks_read():
    suffix = random.randint(10_000_000, 99_999_999)
    buyer = create_active_test_user("cancel_buyer", suffix)
    seller = create_active_test_user("cancel_seller", suffix + 1)
    item = create_test_item(seller, suffix)
    purchase_response = client.post(f"/api/items/{item.id}/purchase?buyer_id={buyer.id}", {}, content_type="application/json")
    assert purchase_response.status_code == 200

    from marketplace.models import Purchase

    purchase = Purchase.objects.get(item_id=item.id, buyer_id=buyer.id)
    cancel_response = client.post(
        f"/api/orders/{purchase.id}/cancel",
        {"user_id": buyer.id},
        content_type="application/json",
    )

    assert cancel_response.status_code == 200
    assert cancel_response.json()["order_stage"] == "cancelled"
    buyer_notifications = client.get(f"/api/users/{buyer.id}/notifications").json()
    seller_notifications = client.get(f"/api/users/{seller.id}/notifications").json()
    buyer_cancel_notification = next(notification for notification in buyer_notifications if notification["title"] == "Order cancelled")
    assert any(notification["title"] == "Order cancelled" for notification in seller_notifications)
    assert buyer_cancel_notification["is_read"] is False

    viewed_response = client.post(f"/api/users/{buyer.id}/notifications/{buyer_cancel_notification['id']}")

    assert viewed_response.status_code == 200
    assert viewed_response.json()["is_read"] is True


def test_message_notification_goes_to_receiver():
    suffix = random.randint(10_000_000, 99_999_999)
    buyer = create_active_test_user("message_buyer", suffix)
    seller = create_active_test_user("message_seller", suffix + 1)
    item = create_test_item(seller, suffix)

    conversation_response = client.post(
        f"/api/items/{item.id}/conversation",
        {"buyer_id": buyer.id},
        content_type="application/json",
    )
    assert conversation_response.status_code == 200
    conversation_id = conversation_response.json()["id"]

    message_response = client.post(
        f"/api/conversations/{conversation_id}",
        {"sender_id": buyer.id, "body": "Is this still available?"},
        content_type="application/json",
    )

    assert message_response.status_code == 200
    notifications = client.get(f"/api/users/{seller.id}/notifications")
    assert notifications.status_code == 200
    assert any(notification["title"] == "New message" for notification in notifications.json())


def test_reports_still_notify_admin():
    suffix = random.randint(10_000_000, 99_999_999)
    reporter = create_active_test_user("reporter", suffix)
    seller = create_active_test_user("reported_seller", suffix + 1)
    item = create_test_item(seller, suffix)

    response = client.post(
        "/api/reports",
        {
            "reporter_id": reporter.id,
            "target_type": "listing",
            "target_id": item.id,
            "reason": "Suspicious listing details",
        },
        content_type="application/json",
    )

    assert response.status_code == 200
    assert AdminNotification.objects.filter(actor_username=reporter.username, category="report").exists()


def test_cancel_verification_removes_pending_registration():
    payload = unique_student_payload()
    with patch("marketplace.services.send_email"):
        signup = client.post("/api/users/signup", payload, content_type="application/json")

    assert signup.status_code == 200
    assert signup.json()["pending_token"] in PENDING_REGISTRATIONS
    assert not PendingRegistration.objects.filter(email=payload["email"]).exists()
    assert not User.objects.filter(email=payload["email"]).exists()

    cancel = client.post(
        "/api/users/cancel-verification",
        {"email": payload["email"], "pending_token": signup.json()["pending_token"]},
        content_type="application/json",
    )
    assert cancel.status_code == 200
    assert cancel.json()["deleted"] is True
    assert signup.json()["pending_token"] not in PENDING_REGISTRATIONS
    assert not PendingRegistration.objects.filter(email=payload["email"]).exists()


def test_signup_resumes_existing_database_pending_registration():
    payload = unique_student_payload()
    code = "123456"
    PendingRegistration.objects.create(
        username=payload["username"],
        student_id=payload["email"].split("@", 1)[0],
        email=payload["email"],
        password_hash="stored-password-hash",
        code_hash=hash_verification_code(code),
        expires_at=timezone.now() + VERIFICATION_CODE_TTL,
    )

    response = client.post("/api/users/signup", payload, content_type="application/json")

    assert response.status_code == 200
    assert response.json()["verification_required"] is True
    assert response.json()["pending_token"] == ""
    assert "already been sent" in response.json()["message"]
    assert PendingRegistration.objects.filter(email=payload["email"]).count() == 1

    verification = client.post(
        "/api/users/verify-email",
        {"email": payload["email"], "code": code},
        content_type="application/json",
    )
    assert verification.status_code == 200
    assert verification.json()["authenticator_setup_required"] is True
    assert User.objects.filter(email=payload["email"]).exists()
    assert not PendingRegistration.objects.filter(email=payload["email"]).exists()


def test_signup_resumes_existing_in_memory_pending_registration():
    payload = unique_student_payload()
    with patch("marketplace.services.send_email") as send_email:
        first_signup = client.post("/api/users/signup", payload, content_type="application/json")
        retry_signup = client.post("/api/users/signup", payload, content_type="application/json")

    assert first_signup.status_code == 200
    assert retry_signup.status_code == 200
    assert retry_signup.json()["verification_required"] is True
    assert retry_signup.json()["pending_token"] == first_signup.json()["pending_token"]
    assert "already been sent" in retry_signup.json()["message"]
    assert send_email.call_count == 1


def test_cancel_verification_without_token_removes_in_memory_registration():
    payload = unique_student_payload()
    with patch("marketplace.services.send_email"):
        signup = client.post("/api/users/signup", payload, content_type="application/json")

    response = client.post(
        "/api/users/cancel-verification",
        {"email": payload["email"]},
        content_type="application/json",
    )

    assert response.status_code == 200
    assert response.json()["deleted"] is True
    assert signup.json()["pending_token"] not in PENDING_REGISTRATIONS


def test_signup_rejects_non_usp_email():
    payload = unique_student_payload()
    payload["email"] = "person@gmail.com"

    response = client.post("/api/users/signup", payload, content_type="application/json")

    assert response.status_code == 422
    assert response.json()["detail"] == "SXXXXXXXX@student.usp.ac.fj"
    assert not User.objects.filter(username=payload["username"]).exists()
    assert not PendingRegistration.objects.filter(username=payload["username"]).exists()


def test_signup_rejects_student_email_without_eight_digits():
    payload = unique_student_payload()
    payload["email"] = "S1234567@student.usp.ac.fj"

    response = client.post("/api/users/signup", payload, content_type="application/json")

    assert response.status_code == 422
    assert response.json()["detail"] == "SXXXXXXXX@student.usp.ac.fj"
    assert not User.objects.filter(username=payload["username"]).exists()
    assert not PendingRegistration.objects.filter(username=payload["username"]).exists()


def test_signup_returns_email_delivery_error_and_allows_retry():
    payload = unique_student_payload()
    with patch("marketplace.services.send_email", side_effect=ApiError("Failed to send verification email: SMTP authentication failed", 502)):
        response = client.post("/api/users/signup", payload, content_type="application/json")

    assert response.status_code == 502
    assert response.json()["detail"] == "Failed to send verification email: SMTP authentication failed"
    assert not User.objects.filter(email=payload["email"]).exists()
    assert not PendingRegistration.objects.filter(email=payload["email"]).exists()
    assert not PENDING_REGISTRATIONS


@override_settings(EMAIL_HOST="", RESEND_API_KEY="")
def test_send_email_requires_smtp_provider():
    with pytest.raises(ApiError) as exc_info:
        send_email("Subject", "Message", "S12345678@student.usp.ac.fj", "Failed to send verification email")

    assert exc_info.value.status == 500
    assert "SMTP is not configured" in exc_info.value.detail


@override_settings(
    EMAIL_HOST="smtp.gmail.com",
    EMAIL_HOST_USER="noreply@uspmarketplacecommunity.com",
    EMAIL_HOST_PASSWORD="shortpass123",
    DEFAULT_FROM_EMAIL="USP Marketplace <noreply@uspmarketplacecommunity.com>",
)
def test_gmail_smtp_requires_app_password_length():
    with pytest.raises(ApiError) as exc_info:
        send_email("Subject", "Message", "S12345678@student.usp.ac.fj", "Failed to send verification email")

    assert exc_info.value.status == 500
    assert "16-character Gmail App Password" in exc_info.value.detail


@override_settings(EMAIL_HOST="smtp.gmail.com")
def test_gmail_disconnect_error_explains_auth_setup():
    detail = __import__("marketplace.services", fromlist=["describe_email_exception"]).describe_email_exception(
        smtplib.SMTPServerDisconnected("Connection unexpectedly closed")
    )

    assert "Gmail closed the SMTP authentication connection" in detail
    assert "App Password" in detail


def test_tls_certificate_error_is_not_reported_as_invalid_email_header():
    detail = __import__("marketplace.services", fromlist=["describe_email_exception"]).describe_email_exception(
        ssl.SSLCertVerificationError("certificate verify failed")
    )

    assert "SMTP TLS certificate verification failed" in detail
    assert "invalid header" not in detail


def test_resend_verification_waits_one_minute():
    payload = unique_student_payload()
    with patch("marketplace.services.send_email") as send_email:
        signup = client.post("/api/users/signup", payload, content_type="application/json")
        resend_too_soon = client.post(
            "/api/users/resend-verification",
            {"email": payload["email"], "pending_token": signup.json()["pending_token"]},
            content_type="application/json",
        )

        registration = PENDING_REGISTRATIONS[signup.json()["pending_token"]]
        registration["expires_at"] = timezone.now() + VERIFICATION_CODE_TTL - timedelta(seconds=61)
        resend_after_countdown = client.post(
            "/api/users/resend-verification",
            {"email": payload["email"], "pending_token": signup.json()["pending_token"]},
            content_type="application/json",
        )

    assert signup.status_code == 200
    assert resend_too_soon.status_code == 429
    assert "Resend code available in" in resend_too_soon.json()["detail"]
    assert resend_after_countdown.status_code == 200
    assert resend_after_countdown.json()["message"] == "Verification code sent successfully"
    assert send_email.call_count == 2


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
    verification = client.post(
        "/api/users/verify-password-reset",
        {"email": payload["email"], "code": code},
        content_type="application/json",
    )
    assert verification.status_code == 200
    assert verification.json()["message"] == "Reset code verified. Choose a new password."

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


def test_password_reset_code_must_be_verified_before_password_form():
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
    rejected = client.post(
        "/api/users/verify-password-reset",
        {"email": payload["email"], "code": "000000" if code != "000000" else "111111"},
        content_type="application/json",
    )
    assert rejected.status_code == 400
    assert PasswordReset.objects.filter(user=user).latest("created_at").attempts == 1

    accepted = client.post(
        "/api/users/verify-password-reset",
        {"email": payload["email"], "code": code},
        content_type="application/json",
    )
    assert accepted.status_code == 200
