from datetime import timedelta

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from marketplace.demo_catalog import DEMO_MARKER
from marketplace.models import Item, Purchase, User
from marketplace.schema import ensure_schema


ORDER_REFERENCE_PREFIX = "showcase-order-"


class Command(BaseCommand):
    help = "Create completed showcase orders in the isolated local SQLite database."

    def add_arguments(self, parser):
        parser.add_argument(
            "--count",
            type=int,
            default=1000,
            help="Target number of completed showcase orders (maximum 1000).",
        )

    def execute(self, *args, **options):
        if settings.SETTINGS_MODULE == "usp_backend.local_settings" and settings.DATABASES["default"]["ENGINE"] == "django.db.backends.sqlite3":
            ensure_schema()
        return super().execute(*args, **options)

    @transaction.atomic
    def handle(self, *args, **options):
        if settings.SETTINGS_MODULE != "usp_backend.local_settings" or settings.DATABASES["default"]["ENGINE"] != "django.db.backends.sqlite3":
            raise CommandError("Use --settings=usp_backend.local_settings for this demo command")
        count = options["count"]
        if not 0 <= count <= 1000:
            raise CommandError("--count must be between 0 and 1000")

        buyer = User.objects.filter(username="demo_buyer").first()
        if not buyer:
            raise CommandError("Run seed_inventory_demo first to create the local demo buyer.")
        items = list(
            Item.objects.filter(
                description__startswith=DEMO_MARKER,
                status="available",
                stock__gt=0,
            ).exclude(seller_id=buyer.id).order_by("id")
        )
        if not items:
            raise CommandError("Run seed_inventory_demo first to create showcase listings.")

        existing_references = set(
            Purchase.objects.filter(
                payment_reference__startswith=ORDER_REFERENCE_PREFIX
            ).values_list("payment_reference", flat=True)
        )
        now = timezone.now()
        orders = []
        for index in range(count):
            reference = f"{ORDER_REFERENCE_PREFIX}{index + 1:06d}"
            if reference in existing_references:
                continue
            item = items[index % len(items)]
            amount = round(item.price, 2)
            orders.append(Purchase(
                buyer_id=buyer.id,
                buyer_username=buyer.username,
                item_id=item.id,
                item_name=item.name,
                price=item.price,
                category=item.category,
                seller_id=item.seller_id,
                seller_username=item.seller_username,
                seller_contact=item.contact,
                quantity=1,
                total_amount=amount,
                payment_method="visa",
                delivery_method="self_pickup",
                subtotal=amount,
                final_total=amount,
                status="completed",
                order_stage="completed",
                payment_status="paid",
                payment_reference=reference,
            ))

        Purchase.objects.bulk_create(orders, batch_size=250)
        for index, order in enumerate(orders):
            order.purchased_at = now - timedelta(
                days=(index * 37) % 90,
                hours=(index * 11) % 24,
            )
        if orders:
            Purchase.objects.bulk_update(orders, ["purchased_at"], batch_size=250)

        self.stdout.write(self.style.SUCCESS(
            f"Completed showcase orders: {len(orders)} added; "
            f"{count - len(orders)} already existed. Listing stock was not changed."
        ))
