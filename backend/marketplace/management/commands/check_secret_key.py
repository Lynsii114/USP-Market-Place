from django.conf import settings
from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = "Confirm Django loaded SECRET_KEY without displaying its value."
    requires_system_checks = []

    def handle(self, *args, **options):
        if not settings.SECRET_KEY.strip() or settings.SECRET_KEY == "dev-secret-key":
            raise CommandError("SECRET_KEY is missing or uses the retired fallback.")
        self.stdout.write(self.style.SUCCESS("SECRET_KEY loaded successfully (value hidden)."))
