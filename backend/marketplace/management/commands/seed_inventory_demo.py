from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from marketplace.models import Item, Category, User
from marketplace.services import get_or_create_admin_user, hash_password, hide_listing


class Command(BaseCommand):
    help = "Create local inventory demonstration records; refuses non-local settings."

    @transaction.atomic
    def handle(self, *args, **options):
        if settings.SETTINGS_MODULE != "usp_backend.local_settings" or settings.DATABASES["default"]["ENGINE"] != "django.db.backends.sqlite3":
            raise CommandError("Use --settings=usp_backend.local_settings for this demo command")
        admin = get_or_create_admin_user()
        for name in ("Books", "Electronics", "Clothing", "Furniture", "Footwares"):
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
        self.stdout.write(self.style.SUCCESS("Local demo ready. Admin@usp.ac.fj / Admin12345. Student accounts: demo_seller or demo_buyer / Demo314! (authenticator setup on first login)."))
