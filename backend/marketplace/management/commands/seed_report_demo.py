from datetime import datetime, timedelta, timezone
from random import Random

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone as django_timezone

from marketplace.demo_catalog import DEMO_MARKER
from marketplace.models import Item, Purchase, User


BUYER_USERNAME = "report_load_demo_buyer"
REFERENCE_PREFIX = "REPORT-LOAD-"


class Command(BaseCommand):
    help = "Add 1000 completed purchases to the isolated local report demo database."

    @transaction.atomic
    def handle(self, *args, **options):
        if settings.SETTINGS_MODULE != "usp_backend.local_settings" or settings.DATABASES["default"]["ENGINE"] != "django.db.backends.sqlite3":
            raise CommandError("Use --settings=usp_backend.local_settings for this demo command")

        items = list(Item.objects.filter(description__startswith=DEMO_MARKER).order_by("id"))
        if not items:
            raise CommandError("Seed showcase listings with seed_inventory_demo before adding report orders")
        buyer = User.objects.filter(username="demo_buyer").first()
        if buyer is None:
            raise CommandError("Seed showcase listings with seed_inventory_demo before adding report orders")

        existing = set(Purchase.objects.filter(payment_reference__startswith=REFERENCE_PREFIX).values_list("payment_reference", flat=True))
        random = Random(314)
        end_day = django_timezone.localdate()
        start_day = end_day - timedelta(days=364)
        purchases = []
        dates = {}
        for index in range(1000):
            item = items[random.randrange(len(items))]
            quantity = random.choice((1, 1, 1, 2, 3))
            unit_price = round(float(item.price), 2)
            total = round(unit_price * quantity, 2)
            reference = f"{REFERENCE_PREFIX}{index + 1:04d}"
            if reference in existing:
                continue
            purchased_day = start_day + timedelta(days=index % 365)
            purchased_at = datetime.combine(purchased_day, datetime.min.time(), tzinfo=timezone.utc) + timedelta(hours=8 + index % 12, minutes=index % 60)
            purchase = Purchase(
                buyer_id=buyer.id, buyer_username=BUYER_USERNAME,
                item_id=item.id, item_name=item.name, price=unit_price,
                category=item.category, seller_id=item.seller_id,
                seller_username=item.seller_username, quantity=quantity,
                total_amount=total, subtotal=total, final_total=total,
                payment_method="visa", payment_status="paid",
                payment_reference=reference, status="completed", order_stage="completed",
            )
            purchases.append(purchase)
            dates[reference] = purchased_at

        Purchase.objects.bulk_create(purchases, batch_size=200)
        for purchase in Purchase.objects.filter(payment_reference__in=dates):
            Purchase.objects.filter(pk=purchase.pk).update(purchased_at=dates[purchase.payment_reference])

        total = Purchase.objects.filter(payment_reference__startswith=REFERENCE_PREFIX).count()
        self.stdout.write(self.style.SUCCESS(f"Report demo: {len(purchases)} added, {total} tagged completed orders total. Existing orders and listing stock were preserved."))
