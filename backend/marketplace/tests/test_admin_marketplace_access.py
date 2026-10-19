from types import SimpleNamespace
from unittest.mock import patch

from django.test import RequestFactory, SimpleTestCase

from marketplace.authentication import ApiIdentityMiddleware


class AdminMarketplaceAccessTests(SimpleTestCase):
    def dispatch(self, name, method="POST", role="admin", path="/api/items"):
        request = getattr(RequestFactory(), method.lower())(
            path, data={} if method != "GET" else None,
            content_type="application/json", HTTP_AUTHORIZATION="Bearer test-token",
        )
        view = lambda request: None
        view.__name__ = name
        user = SimpleNamespace(id=7, role=role, status="active")
        with patch("marketplace.authentication.token_user", return_value=user):
            return ApiIdentityMiddleware(lambda request: None).process_view(request, view, (), {})

    def test_admin_cannot_perform_customer_mutations(self):
        actions = {
            "items_collection": "POST", "item_detail": "PUT",
            "purchase_item": "POST", "checkout_cart": "POST",
            "item_conversation": "POST", "item_reservation": "POST",
            "seller_item_status": "POST", "seller_order_stage": "POST",
            "confirm_payment_received": "POST", "confirm_cash_payment": "POST",
            "cancel_order": "POST", "buyer_order_received": "POST",
            "report_user_activity": "POST", "rating_review": "POST",
            "conversation_detail": "POST",
        }
        for action, method in actions.items():
            with self.subTest(action=action):
                self.assertEqual(self.dispatch(action, method).status_code, 403)
        self.assertEqual(self.dispatch("item_detail", "DELETE").status_code, 403)

    def test_admin_can_browse_and_moderate(self):
        for name in ("items_collection", "item_detail", "list_seller_items", "seller_reviews"):
            with self.subTest(name=name):
                self.assertIsNone(self.dispatch(name, "GET"))
        self.assertIsNone(self.dispatch("admin_hide_listing", path="/api/admin/listings/1/hide"))
        self.assertIsNone(self.dispatch("user_notification_detail", "DELETE"))

    def test_customer_actions_remain_available_to_students(self):
        for name in ("items_collection", "checkout_cart", "item_conversation", "report_user_activity", "rating_review"):
            with self.subTest(name=name):
                self.assertIsNone(self.dispatch(name, role="student"))

    def test_students_cannot_switch_identity_to_admin(self):
        response = self.dispatch("admin_dashboard", "GET", role="student", path="/api/admin/dashboard")
        self.assertEqual(response.status_code, 403)
