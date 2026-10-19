from django.core.management.base import BaseCommand
from marketplace.schema import ensure_item_quantity_field


class Command(BaseCommand):
    help = "Add and backfill the persistent multiple-unit listing flag."

    def handle(self, *args, **options):
        ensure_item_quantity_field()
        self.stdout.write(self.style.SUCCESS("Listing quantity field is ready."))
