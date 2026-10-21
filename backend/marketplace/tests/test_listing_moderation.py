from unittest.mock import patch

from django.test import Client, TestCase, override_settings

from marketplace import services
from marketplace.authentication import issue_token
from marketplace.exceptions import ApiError
from marketplace.models import AdminNotification, Item, Purchase, User, UserNotification


@override_settings(EMAIL_PROVIDER="resend")
class ListingModerationTests(TestCase):
    def setUp(self):
        email_patch = patch("marketplace.services.send_email")
        self.send = email_patch.start()
        self.addCleanup(email_patch.stop)
        self.admin = User.objects.create(username="admin", email="admin@example.com", role="admin", password_hash="hash", verified=True)
        self.seller = User.objects.create(name="Alex Kumar", username="seller", email="seller@example.com", password_hash="hash", verified=True)
        self.item = Item.objects.create(name="Campus textbook", price=20, stock=3, seller_id=self.seller.id, seller_username=self.seller.username)
        self.client = Client(HTTP_AUTHORIZATION=f"Bearer {issue_token(self.admin)}")
        self.reason = "The description contains misleading information about the item."

    def act(self, action="warn", **changes):
        return self.client.post(f"/api/admin/listings/{self.item.id}/{action}", {"reason": self.reason, "confirmed": True, "expected_status": "available", **changes}, content_type="application/json")

    def test_warning_sends_formal_email_without_changing_listing(self):
        response = self.act()
        self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual(response.json()["email_status"], "sent")
        self.item.refresh_from_db()
        self.assertEqual(self.item.status, "available")
        self.assertEqual(self.item.stock, 3)
        subject, body, recipient, _ = self.send.call_args.args
        self.assertIn("Formal warning", subject)
        self.assertTrue(body.startswith("Dear Alex Kumar,\n\n"))
        self.assertIn(self.item.name, body)
        self.assertIn(f"#{self.item.id}", body)
        self.assertIn(self.reason, body)
        self.assertIn("request a review", body)
        self.assertTrue(body.endswith("Kind regards,\nUSP Marketplace Administration Team"))
        self.assertEqual(recipient, self.seller.email)
        self.assertEqual(self.send.call_count, 1)
        self.assertTrue(AdminNotification.objects.filter(title="Listing warning issued", message__contains=self.reason).exists())
        self.assertFalse(UserNotification.objects.exists())

    def test_removal_permanently_deletes_listing_and_cannot_be_restored(self):
        response = self.act("remove", reason="This item is prohibited under the marketplace rules.")
        self.assertEqual(response.status_code, 200, response.content)
        self.assertFalse(Item.objects.filter(id=self.item.id).exists())
        self.assertIsNone(response.json()["listing"])
        self.assertEqual(response.json()["removed_id"], self.item.id)
        self.assertEqual(Client().get(f"/api/items/{self.item.id}").status_code, 404)
        self.assertNotIn(self.item.id, [row["id"] for row in self.client.get("/api/admin/listings").json()])
        self.assertNotIn(self.item.id, [row["id"] for row in self.client.get("/api/admin/listings?search=Campus").json()])
        self.assertIn("Notice of listing removal", self.send.call_args.args[0])
        self.assertIn("This item is prohibited under the marketplace rules.", self.send.call_args.args[1])
        self.assertIn(f"#{self.item.id}", self.send.call_args.args[1])
        self.assertIn("permanently deleted", self.send.call_args.args[1])
        self.assertIn("no longer visible or available for purchase", self.send.call_args.args[1])
        self.assertTrue(AdminNotification.objects.filter(title="Listing removed").exists())
        with self.assertRaises(ApiError):
            services.update_item_seller_status(self.item.id, self.seller.id, "available")
        self.assertEqual(self.send.call_count, 1)
        self.assertEqual(self.act("remove").status_code, 404)
        self.assertEqual(self.client.post(f"/api/admin/listings/{self.item.id}/restore", {}, content_type="application/json").status_code, 404)
        self.assertEqual(self.send.call_count, 1)

    def test_permanent_removal_preserves_existing_purchase_history(self):
        buyer = User.objects.create(username="buyer", email="buyer@example.com", password_hash="hash", verified=True)
        order = Purchase.objects.create(
            buyer_id=buyer.id, buyer_username=buyer.username, item_id=self.item.id,
            item_name=self.item.name, price=20, category="Books", seller_id=self.seller.id,
            seller_username=self.seller.username, quantity=1, total_amount=20,
            status="completed", order_stage="completed", payment_status="paid",
        )
        buyer_client = Client(HTTP_AUTHORIZATION=f"Bearer {issue_token(buyer)}")
        history_url = f"/api/users/{buyer.id}/purchases"
        before = buyer_client.get(history_url).json()
        self.assertEqual(self.act("remove").status_code, 200)
        self.assertFalse(Item.objects.filter(id=self.item.id).exists())
        self.assertTrue(Purchase.objects.filter(id=order.id).exists())
        self.assertEqual(buyer_client.get(history_url).json(), before)

    def test_both_actions_require_explicit_confirmation_and_valid_reason(self):
        for action in ("warn", "remove"):
            for changes in ({"confirmed": False}, {"confirmed": None}, {"confirmed": "true"}, {"reason": "short"}, {"reason": " "}, {"reason": None}, {"reason": "x" * 501}):
                with self.subTest(action=action, changes=changes):
                    self.assertEqual(self.act(action, **changes).status_code, 422)
        self.send.assert_not_called()
        self.assertFalse(AdminNotification.objects.exists())
        self.item.refresh_from_db()
        self.assertEqual(self.item.status, "available")

    def test_changed_or_missing_listing_is_not_moderated(self):
        self.assertEqual(self.act(expected_status="reserved").status_code, 409)
        item_id = self.item.id
        self.item.delete()
        response = self.client.post(f"/api/admin/listings/{item_id}/warn", {"reason": self.reason, "confirmed": True}, content_type="application/json")
        self.assertEqual(response.status_code, 404)
        self.send.assert_not_called()

    def test_missing_seller_cannot_receive_warning_or_removal(self):
        self.seller.delete()
        for action in ("warn", "remove"):
            self.assertEqual(self.act(action).status_code, 409)
        self.item.refresh_from_db()
        self.assertEqual(self.item.status, "available")
        self.send.assert_not_called()

    def test_customer_and_anonymous_cannot_warn_or_remove(self):
        for client in (Client(), Client(HTTP_AUTHORIZATION=f"Bearer {issue_token(self.seller)}")):
            self.client = client
            for action in ("warn", "remove"):
                self.assertIn(self.act(action).status_code, (401, 403))
        self.send.assert_not_called()

    def test_email_failure_reports_action_complete_without_claiming_delivery(self):
        self.send.side_effect = RuntimeError("Resend unavailable")
        response = self.act("remove")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["email_status"], "failed")
        self.assertFalse(Item.objects.filter(id=self.item.id).exists())
        self.assertTrue(AdminNotification.objects.filter(message__contains="Email status: failed").exists())
