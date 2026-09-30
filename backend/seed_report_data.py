"""Adds sample COMPLETED orders so the Reports tab has data to show.

    python seed_report_data.py          # add ~40 sample orders
    python seed_report_data.py --clear  # remove them again

Sample rows are tagged with buyer_username = "seed_buyer".
"""
import os
import random
import sys
from datetime import timedelta

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "usp_backend.settings")

import django

django.setup()

from django.utils import timezone

from marketplace.models import Purchase
from marketplace.schema import ensure_schema

TAG = "seed_buyer"
ITEMS = [  # (item_id, name, category, price)
    (9001, "Calculus Textbook", "Books", 45.0),
    (9002, "Scientific Calculator", "Electronics", 30.0),
    (9003, "USP Hoodie", "Clothes", 25.0),
    (9004, "Desk Lamp", "Home and Living", 18.0),
    (9005, "Laptop Stand", "Electronics", 35.0),
    (9006, "Study Guide Bundle", "Books", 12.0),
]

ensure_schema()

if "--clear" in sys.argv:
    deleted, _ = Purchase.objects.filter(buyer_username=TAG).delete()
    print(f"Removed {deleted} sample orders.")
    sys.exit(0)

now = timezone.now()
for _ in range(40):
    item_id, name, category, price = random.choice(ITEMS)
    quantity = random.choice([1, 1, 1, 2])
    total = price * quantity
    purchase = Purchase.objects.create(
        buyer_id=0, buyer_username=TAG, item_id=item_id, item_name=name, price=price,
        category=category, seller_id=0, seller_username="seed_seller", quantity=quantity,
        total_amount=total, subtotal=total, final_total=total,
        status="completed", order_stage="completed",
    )
    Purchase.objects.filter(id=purchase.id).update(purchased_at=now - timedelta(days=random.randint(0, 60), hours=random.randint(0, 23)))
print("Added 40 sample completed orders. Run with --clear to remove them.")
