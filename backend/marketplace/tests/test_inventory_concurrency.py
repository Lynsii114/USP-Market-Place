"""Exercise real row locks when running Django tests against MySQL.

SQLite deliberately skips these tests: it cannot prove MySQL locking behavior.
"""
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier

from django.db import connections, close_old_connections
from django.test import TransactionTestCase, skipUnlessDBFeature

from marketplace import services
from marketplace.exceptions import ApiError
from marketplace.models import User, Item, Purchase


@skipUnlessDBFeature("has_select_for_update")
class InventoryConcurrencyTests(TransactionTestCase):
    def setUp(self):
        self.seller = User.objects.create(username="lock_seller", email="seller@example.com", password_hash="hash")
        self.buyers = [User.objects.create(username=f"lock_buyer_{i}", email=f"buyer{i}@example.com", password_hash="hash") for i in range(2)]
        self.item = Item.objects.create(name="Last calculator", price=20, description="Used", category="Electronics", contact="Campus", stock=1, seller_id=self.seller.id, seller_username=self.seller.username)

    def race(self, first, second):
        barrier = Barrier(2)

        def run(action):
            close_old_connections()
            try:
                barrier.wait(timeout=10)
                action()
                return "ok"
            except ApiError as exc:
                return exc.status
            finally:
                connections.close_all()

        with ThreadPoolExecutor(max_workers=2) as pool:
            futures = [pool.submit(run, action) for action in (first, second)]
            return [future.result(timeout=20) for future in futures]

    def checkout(self, buyer):
        return services.checkout_cart(buyer.id, {"payment_method": "cash", "delivery_method": "self_pickup", "items": [{"item_id": self.item.id, "quantity": 1}]})

    def test_two_buyers_cannot_reserve_the_same_unit(self):
        outcomes = self.race(lambda: self.checkout(self.buyers[0]), lambda: self.checkout(self.buyers[1]))
        self.assertEqual(outcomes.count("ok"), 1)
        self.assertEqual(Purchase.objects.filter(item_id=self.item.id).count(), 1)
        self.item.refresh_from_db()
        self.assertEqual((self.item.stock, self.item.status), (1, "reserved"))

    def test_delete_and_checkout_never_leave_an_orphan_order(self):
        outcomes = self.race(lambda: services.delete_item(self.item.id, self.seller.id), lambda: self.checkout(self.buyers[0]))
        self.assertEqual(outcomes.count("ok"), 1)
        if Item.objects.filter(id=self.item.id).exists():
            self.assertEqual(Purchase.objects.filter(item_id=self.item.id).count(), 1)
        else:
            self.assertFalse(Purchase.objects.filter(item_id=self.item.id).exists())
