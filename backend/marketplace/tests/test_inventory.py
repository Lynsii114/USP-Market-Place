from unittest.mock import patch
import hashlib

import pyotp
from django.test import TestCase, Client, override_settings
from django.core import signing

from marketplace import services
from marketplace.authentication import issue_token
from marketplace.exceptions import ApiError
from marketplace.models import User, Item, Purchase, Conversation, Category


class InventoryTests(TestCase):
    def setUp(self):
        services.CATEGORY_TABLE_READY = True
        self.seller = self.user("seller")
        self.buyer = self.user("buyer")
        self.other = self.user("other")
        self.admin = self.user("administrator", role="admin")
        self.item = Item.objects.create(
            name="IS314 textbook", price=20, description="Used textbook",
            category="Books", contact="Campus pickup", stock=3,
            seller_id=self.seller.id, seller_username=self.seller.username,
        )

    def user(self, username, role="student"):
        return User.objects.create(username=username, email=f"{username}@example.com", password_hash="hash", role=role, status="active", verified=True)

    def client_for(self, user):
        return Client(HTTP_AUTHORIZATION=f"Bearer {issue_token(user)}")

    def payload(self, **updates):
        return {"name": "New book", "price": 10, "description": "Good condition", "category": "Books", "contact": "Library", "stock": 2, "seller_id": self.seller.id, **updates}

    def checkout(self, item=None, buyer=None, **updates):
        return services.checkout_cart((buyer or self.buyer).id, {
            "payment_method": "cash", "delivery_method": "self_pickup",
            "items": [{"item_id": (item or self.item).id, "quantity": 1}], **updates,
        })

    def pending(self):
        self.checkout()
        return Purchase.objects.get(item_id=self.item.id)

    def test_listing_rejects_bad_stock_and_price(self):
        client = self.client_for(self.seller)
        for field, values in {
            "stock": [-1, -0.5, 1.9, True, None, "1.5", "", 2147483648],
            "price": [-1, 0, "0", -0.0, "NaN", "Infinity", True, None, 1e20],
        }.items():
            for value in values:
                with self.subTest(field=field, value=value):
                    response = client.post("/api/items", self.payload(**{field: value}), content_type="application/json")
                    self.assertEqual(response.status_code, 422, response.content)
        self.assertEqual(Item.objects.count(), 1)

    def test_required_text_lengths_and_categories(self):
        client = self.client_for(self.seller)
        for field, value in [("name", " "), ("name", None), ("contact", 123), ("name", "a" * 257), ("description", "a" * 1001), ("category", "Invented")]:
            with self.subTest(field=field, value=value):
                response = client.post("/api/items", self.payload(**{field: value}), content_type="application/json")
                self.assertEqual(response.status_code, 422)
        Category.objects.create(name="Stationery")
        response = client.post("/api/items", self.payload(name="  Notebook  ", category="Stationery", stock="0", price=0.01), content_type="application/json")
        self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual(response.json()["name"], "Notebook")
        self.assertEqual(response.json()["status"], "sold")

    def test_partial_edit_validates_fields(self):
        client = self.client_for(self.seller)
        response = client.put(f"/api/items/{self.item.id}", {"stock": 2.7}, content_type="application/json")
        self.assertEqual(response.status_code, 422)
        response = client.put(f"/api/items/{self.item.id}", {"description": "  Updated  "}, content_type="application/json")
        self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual(response.json()["description"], "Updated")

    def test_price_must_be_positive_on_edit_without_changing_saved_price(self):
        client = self.client_for(self.seller)
        for price in (0, "0", -1):
            with self.subTest(price=price):
                response = client.put(f"/api/items/{self.item.id}", {"price": price}, content_type="application/json")
                self.assertEqual(response.status_code, 422)
                self.assertIn("greater than 0", response.json()["detail"])
                self.item.refresh_from_db()
                self.assertEqual(self.item.price, 20)
        response = client.put(f"/api/items/{self.item.id}", {"price": 0.01}, content_type="application/json")
        self.assertEqual(response.status_code, 200)

    def test_sold_and_empty_listings_hidden_from_browse_but_kept_in_my_listings(self):
        items = []
        for name, stock, status in (("Sold hoodie", 0, "sold"), ("Manually sold", 3, "sold"), ("Empty stock", 0, "available"), ("Reserved book", 1, "reserved")):
            items.append(Item.objects.create(name=name, stock=stock, status=status, price=10, description="Inventory visibility test", category="Books", contact="Campus", seller_id=self.seller.id, seller_username=self.seller.username))
        for client in (Client(), self.client_for(self.buyer), self.client_for(self.seller)):
            with self.subTest(client=client):
                public_ids = {item["id"] for item in client.get("/api/items").json()}
                self.assertTrue({item.id for item in items[:3]}.isdisjoint(public_ids))
                self.assertIn(self.item.id, public_ids)
                self.assertIn(items[3].id, public_ids)
        storefront = Client().get(f"/api/users/{self.seller.id}/items").json()
        self.assertTrue({item.id for item in items[:3]}.isdisjoint({item["id"] for item in storefront}))
        own_ids = {item["id"] for item in self.client_for(self.seller).get(f"/api/users/{self.seller.id}/items").json()}
        self.assertTrue({item.id for item in items}.issubset(own_ids))

    def test_final_unit_payment_removes_listing_from_browse_not_seller_history(self):
        self.item.stock = 1
        self.item.save()
        order = self.pending()
        services.confirm_payment_received(order.id, self.seller.id)
        public_ids = {item["id"] for item in Client().get("/api/items").json()}
        self.assertNotIn(self.item.id, public_ids)
        history = self.client_for(self.seller).get(f"/api/users/{self.seller.id}/items").json()
        self.assertEqual(history[0]["status"], "sold")

    def test_zero_stock_clears_manual_reservation(self):
        self.item.status = "reserved"
        self.item.reserved_buyer_id = self.buyer.id
        self.item.reserved_buyer_username = self.buyer.username
        self.item.save()
        result = services.update_item(self.item.id, self.seller.id, {"stock": 0})
        self.assertEqual((result["status"], result["reserved_buyer_id"]), ("sold", None))

    def test_authentication_required_and_impersonation_rejected(self):
        route = f"/api/items/{self.item.id}?seller_id={self.seller.id}"
        self.assertEqual(Client().put(route, {"stock": 1}, content_type="application/json").status_code, 401)
        self.assertEqual(self.client_for(self.other).put(route, {"stock": 1}, content_type="application/json").status_code, 403)
        self.assertEqual(self.client_for(self.other).put(f"/api/items/{self.item.id}", {"stock": 1}, content_type="application/json").status_code, 403)
        self.assertEqual(self.client_for(self.seller).put(route, {"stock": 1}, content_type="application/json").status_code, 200)

    def test_invalid_expired_and_password_changed_tokens(self):
        route = f"/api/users/{self.seller.id}/sales"
        self.assertEqual(Client(HTTP_AUTHORIZATION="Bearer fake").get(route).status_code, 401)
        with patch("django.core.signing.time.time", return_value=1):
            token = issue_token(self.seller)
        self.assertEqual(Client(HTTP_AUTHORIZATION=f"Bearer {token}").get(route).status_code, 401)
        client = self.client_for(self.seller)
        self.seller.password_hash = "changed"
        self.seller.save()
        self.assertEqual(client.get(route).status_code, 401)

    def test_suspended_user_and_admin_access(self):
        client = self.client_for(self.seller)
        self.assertEqual(client.get(f"/api/admin/listings?admin_id={self.admin.id}").status_code, 403)
        self.assertEqual(self.client_for(self.admin).get("/api/admin/listings").status_code, 200)
        self.seller.status = "suspended"
        self.seller.save()
        self.assertEqual(client.delete(f"/api/items/{self.item.id}").status_code, 403)

    def test_private_account_routes(self):
        client = self.client_for(self.other)
        for suffix in ("sales", "purchases", "notifications", "conversations", "messages/unread"):
            with self.subTest(suffix=suffix):
                self.assertEqual(client.get(f"/api/users/{self.buyer.id}/{suffix}").status_code, 403)

    def test_public_viewer_id_cannot_disclose_payment_number(self):
        self.item.payment_number = "+6799000000"
        self.item.save()
        route = f"/api/items/{self.item.id}?user_id={self.seller.id}"
        self.assertNotIn("payment_number", Client().get(route).json())
        self.assertNotIn("payment_number", self.client_for(self.other).get(route).json())
        self.assertEqual(self.client_for(self.seller).get(route).json()["payment_number"], "+6799000000")

    def test_seller_hidden_listing_stays_hidden_on_edit_and_reactivates_explicitly(self):
        services.update_item_seller_status(self.item.id, self.seller.id, "hidden")
        result = services.update_item(self.item.id, self.seller.id, {"description": "Changed"})
        self.assertEqual(result["status"], "hidden")
        services.update_item_seller_status(self.item.id, self.seller.id, "available")
        self.item.refresh_from_db()
        self.assertEqual(self.item.status, "available")

    def test_admin_hidden_and_removed_listings_reject_seller_mutations(self):
        Conversation.objects.create(item_id=self.item.id, seller_id=self.seller.id, buyer_id=self.buyer.id)
        for action in (services.hide_listing, services.remove_listing):
            action(self.admin.id, self.item.id, "Moderation")
            for mutation in (
                lambda: services.update_item(self.item.id, self.seller.id, {"description": "Changed"}),
                lambda: services.update_item_seller_status(self.item.id, self.seller.id, "available"),
                lambda: services.reserve_item(self.item.id, self.seller.id, self.buyer.id),
                lambda: services.delete_item(self.item.id, self.seller.id),
            ):
                with self.assertRaises(ApiError):
                    mutation()
            self.item.refresh_from_db()
            self.assertIn(self.item.status, {"hidden", "removed"})

    def test_hidden_listing_not_public_or_purchasable(self):
        services.hide_listing(self.admin.id, self.item.id, "Review")
        self.assertEqual(Client().get(f"/api/items/{self.item.id}").status_code, 404)
        self.assertEqual(Client().get(f"/api/users/{self.seller.id}/items").json(), [])
        self.assertEqual(self.client_for(self.seller).get(f"/api/items/{self.item.id}").status_code, 200)
        for route in ("/api/checkout", f"/api/items/{self.item.id}/purchase"):
            response = self.client_for(self.buyer).post(route, {"payment_method": "cash", "delivery_method": "self_pickup", "items": [{"item_id": self.item.id, "quantity": 1}]}, content_type="application/json")
            self.assertEqual(response.status_code, 404, response.content)
        self.assertFalse(Purchase.objects.exists())
        self.item.refresh_from_db()
        self.assertEqual(self.item.stock, 3)

    def test_checkout_rejects_fractional_boolean_and_zero_quantities(self):
        for quantity in (1.5, True, 0, -1, "1.5", 2147483648):
            with self.subTest(quantity=quantity), self.assertRaises(ApiError):
                self.checkout(items=[{"item_id": self.item.id, "quantity": quantity}])
        self.assertFalse(Purchase.objects.exists())

    def test_cash_lifecycle_and_confirmation_retry(self):
        order = self.pending()
        self.item.refresh_from_db()
        self.assertEqual((self.item.stock, self.item.status), (3, "reserved"))
        with self.assertRaises(ApiError):
            services.update_item(self.item.id, self.seller.id, {"stock": 1})
        services.confirm_payment_received(order.id, self.seller.id)
        with self.assertRaises(ApiError):
            services.confirm_payment_received(order.id, self.seller.id)
        self.item.refresh_from_db()
        self.assertEqual((self.item.stock, self.item.status), (2, "available"))
        services.update_seller_order_stage(order.id, self.seller.id, "preparing_item")
        services.update_seller_order_stage(order.id, self.seller.id, "ready_for_collection")
        with self.assertRaises(ApiError):
            services.update_seller_order_stage(order.id, self.seller.id, "preparing_item")
        services.confirm_order_received(order.id, self.buyer.id)
        with self.assertRaises(ApiError):
            services.cancel_order(order.id, self.buyer.id)

    def test_cancel_is_idempotent_and_terminal(self):
        order = self.pending()
        services.cancel_order(order.id, self.buyer.id)
        services.cancel_order(order.id, self.buyer.id)
        self.item.refresh_from_db()
        self.assertEqual((self.item.stock, self.item.status, self.item.reserved_buyer_id), (3, "available", None))
        for stage in ("preparing_item", "ready_for_collection"):
            with self.assertRaises(ApiError):
                services.update_seller_order_stage(order.id, self.seller.id, stage)

    def test_cancellation_preserves_admin_hide(self):
        order = self.pending()
        services.hide_listing(self.admin.id, self.item.id, "Review")
        services.cancel_order(order.id, self.buyer.id)
        self.item.refresh_from_db()
        self.assertEqual((self.item.stock, self.item.status, self.item.reserved_buyer_id), (3, "hidden", None))

    def test_cancellation_does_not_overwrite_unrelated_reservation(self):
        order = self.pending()
        Item.objects.filter(id=self.item.id).update(reserved_buyer_id=self.other.id, reserved_buyer_username=self.other.username)
        services.cancel_order(order.id, self.buyer.id)
        self.item.refresh_from_db()
        self.assertEqual((self.item.status, self.item.reserved_buyer_id), ("reserved", self.other.id))

    def test_restore_rebuilds_pending_order_reservation(self):
        order = self.pending()
        services.hide_listing(self.admin.id, self.item.id, "Review")
        services.restore_listing(self.admin.id, self.item.id)
        self.item.refresh_from_db()
        self.assertEqual((self.item.status, self.item.reserved_buyer_id), ("reserved", self.buyer.id))
        with self.assertRaises(ApiError):
            self.checkout(buyer=self.other)
        services.confirm_payment_received(order.id, self.seller.id)
        self.item.refresh_from_db()
        self.assertEqual(self.item.stock, 2)

    def test_active_order_blocks_delete_and_duplicate_checkout(self):
        order = self.pending()
        with self.assertRaises(ApiError):
            services.delete_item(self.item.id, self.seller.id)
        with self.assertRaises(ApiError):
            self.checkout()
        services.confirm_payment_received(order.id, self.seller.id)
        with self.assertRaises(ApiError):
            services.delete_item(self.item.id, self.seller.id)

    def test_approved_payment_cannot_restore_stock_by_cancellation(self):
        self.checkout(payment_method="mpaisa", payment_details={"phone_number": "9000000", "authorization_code": "123456"})
        order = Purchase.objects.get(item_id=self.item.id)
        self.assertEqual(order.payment_status, "approved")
        with self.assertRaises(ApiError):
            services.cancel_order(order.id, self.buyer.id)
        self.item.refresh_from_db()
        self.assertEqual(self.item.stock, 2)

    def test_multi_item_failure_rolls_back_all_orders_and_stock(self):
        other_item = Item.objects.create(name="Calculator", price=30, description="Used", category="Electronics", contact="Campus", stock=1, seller_id=self.seller.id, seller_username=self.seller.username)
        with self.assertRaises(ApiError):
            self.checkout(items=[{"item_id": self.item.id, "quantity": 1}, {"item_id": other_item.id, "quantity": 2}])
        self.assertFalse(Purchase.objects.exists())
        self.item.refresh_from_db()
        self.assertEqual((self.item.stock, self.item.status), (3, "available"))

    def test_json_list_rejected_cleanly(self):
        self.assertEqual(self.client_for(self.seller).post("/api/items", [], content_type="application/json").status_code, 422)

    def test_mfa_requires_password_challenge_before_access_token(self):
        self.seller.password_hash = services.hash_password("secret123")
        self.seller.authenticator_secret = pyotp.random_base32()
        self.seller.authenticator_enabled = True
        self.seller.save()
        client = Client()
        login = client.post("/api/users/login", {"username": self.seller.username, "password": "secret123"}, content_type="application/json")
        self.assertEqual(login.status_code, 200, login.content)
        self.assertNotIn("access_token", login.json())
        payload = {"user_id": self.seller.id, "code": pyotp.TOTP(self.seller.authenticator_secret).now()}
        self.assertEqual(client.post("/api/users/verify-authenticator", payload, content_type="application/json").status_code, 401)
        payload["login_challenge"] = login.json()["login_challenge"]
        response = client.post("/api/users/verify-authenticator", payload, content_type="application/json")
        self.assertEqual(response.status_code, 200, response.content)
        self.assertIn("access_token", response.json())

    def test_legacy_password_is_upgraded_on_login(self):
        self.seller.password_hash = hashlib.sha256(b"secret123").hexdigest()
        self.seller.save()
        result = services.login_user({"username": self.seller.username, "password": "secret123"})
        self.assertIn("login_challenge", result)
        self.seller.refresh_from_db()
        self.assertTrue(self.seller.password_hash.startswith("pbkdf2_sha256$"))
