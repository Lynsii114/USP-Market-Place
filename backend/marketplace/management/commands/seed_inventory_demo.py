import base64
from io import BytesIO
from pathlib import Path

from PIL import Image
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from marketplace.models import Item, Category, User
from marketplace.services import get_or_create_admin_user, hash_password, hide_listing
from marketplace.category_catalog import BUILTIN_CATEGORIES
from marketplace.demo_catalog import DEMO_CATALOG, DEMO_MARKER
from marketplace.schema import ensure_schema


def category_photo(relative_path):
    path = Path(__file__).resolve().parents[4] / "frontend" / relative_path
    with Image.open(path) as image:
        image.thumbnail((640, 480))
        output = BytesIO()
        image.convert("RGB").save(output, format="JPEG", quality=75)
    return "data:image/jpeg;base64," + base64.b64encode(output.getvalue()).decode("ascii")


class Command(BaseCommand):
    help = "Create local showcase listings plus sample inventory; refuses non-local settings."

    def add_arguments(self, parser):
        parser.add_argument(
            "--count",
            type=int,
            default=75,
            help="Target number of generated active showcase listings (maximum 1000).",
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
        admin = get_or_create_admin_user()
        for name, _ in BUILTIN_CATEGORIES:
            Category.objects.get_or_create(name=name)
        for username in ("demo_seller", "demo_buyer"):
            User.objects.get_or_create(username=username, defaults={"email": f"{username}@example.com", "password_hash": hash_password("Demo314!"), "status": "active", "verified": True})
        samples = [
            ("IS314 textbook", "Books", 25, 5, "available"),
            ("Scientific calculator", "Electronics", 35, 2, "available"),
            ("Campus hoodie", "Clothing", 20, 0, "sold"),
            ("Desk lamp (inactive)", "Furniture", 15, 3, "hidden"),
            ("Headphones (under review)", "Electronics", 40, 2, "moderated"),
        ]
        for name, category, price, stock, status in samples:
            item, created = Item.objects.get_or_create(name=name, seller_id=admin.id, defaults={"seller_username": admin.username, "category": category, "price": price, "stock": stock, "description": "Local inventory demo. Pickup at Laucala campus library.", "contact": "Arrange campus pickup", "status": "hidden" if status == "moderated" else status})
            if created and status == "moderated":
                hide_listing(admin.id, item.id, "Demo moderation restriction")
        sellers = [admin]
        for index, name in enumerate(("Demo Student A", "Demo Student B", "Demo Student C"), 1):
            seller, _ = User.objects.get_or_create(username=f"showcase_seller_{index}", defaults={
                "name": name, "email": f"showcase_seller_{index}@example.com",
                "password_hash": hash_password("Demo314!"), "status": "active", "verified": True,
            })
            sellers.append(seller)
        created_count = 0
        counter = 0
        for category, (photo_path, entries) in DEMO_CATALOG.items():
            photo = category_photo(photo_path)
            for name, price in entries:
                seller = sellers[counter % len(sellers)]
                status = "sold" if counter in (8, 26, 50) else "hidden" if counter in (17, 42, 66) else "available"
                if status != "available":
                    seller = admin
                _, created = Item.objects.get_or_create(
                    name=name, seller_id=seller.id, description__startswith=DEMO_MARKER,
                    defaults={"seller_username": seller.username, "category": category,
                        "price": price, "stock": 0 if status == "sold" else 1 + counter % 4,
                        "status": status, "photo": photo, "payment_method": "cash",
                        "contact": "Arrange pickup through marketplace messages",
                        "description": f"{DEMO_MARKER} {name}. {'New and unopened where applicable.' if category == 'Personal Care' else 'Good condition; suitable for student use.'} Pickup at Laucala campus by arrangement. Fictional demo listing; photo represents the category."},
                )
                created_count += int(created)
                counter += 1
        generated_marker = f"{DEMO_MARKER} [Generated showcase listing]"
        existing_names = set(
            Item.objects.filter(description__startswith=generated_marker).values_list("name", flat=True)
        )
        catalog_entries = [
            (category, photo_path, name, price)
            for category, (photo_path, entries) in DEMO_CATALOG.items()
            for name, price in entries
        ]
        photo_cache = {}
        generated_items = []
        for index in range(count):
            category, photo_path, base_name, price = catalog_entries[index % len(catalog_entries)]
            name = f"{base_name} - Showcase {index + 1:04d}"
            if name in existing_names:
                continue
            seller = sellers[index % len(sellers)]
            if photo_path not in photo_cache:
                photo_cache[photo_path] = category_photo(photo_path)
            generated_items.append(Item(
                name=name,
                price=price,
                description=f"{generated_marker} {name}. Fictional showcase listing for local demonstration.",
                category=category,
                contact="Arrange pickup through marketplace messages",
                payment_method="cash",
                photo=photo_cache[photo_path],
                stock=1 + index % 4,
                status="available",
                seller_id=seller.id,
                seller_username=seller.username,
            ))
        Item.objects.bulk_create(generated_items, batch_size=250)
        self.stdout.write(self.style.SUCCESS(
            f"Showcase: {len(generated_items)} generated listings added; "
            f"{count - len(generated_items)} already existed. "
            "Generated listings are active. Existing records were preserved."
        ))
        self.stdout.write(self.style.SUCCESS("Local demo ready. Admin@usp.ac.fj / Admin12345. Student accounts: demo_seller or demo_buyer / Demo314! (authenticator setup on first login)."))
