import logging
import sys

from django.apps import AppConfig
from django.core.management.base import BaseCommand
from django.db import DatabaseError


logger = logging.getLogger(__name__)


class MarketplaceConfig(AppConfig):
    default_auto_field = "django.db.models.AutoField"
    name = "marketplace"

    def ready(self):
        if len(sys.argv) < 2 or sys.argv[1] != "runserver":
            return
        if getattr(BaseCommand.check_migrations, "_usp_marketplace_guarded", False):
            return

        original_check_migrations = BaseCommand.check_migrations

        def check_migrations(command, *args, **kwargs):
            try:
                return original_check_migrations(command, *args, **kwargs)
            except DatabaseError as exc:
                logger.warning("Skipping migration check because the database is unavailable: %s", exc)

        check_migrations._usp_marketplace_guarded = True
        BaseCommand.check_migrations = check_migrations
