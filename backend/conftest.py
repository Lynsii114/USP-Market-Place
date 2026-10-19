"""All pytest runs are confined to an in-memory database, before collection."""
import os

os.environ["DJANGO_SETTINGS_MODULE"] = "usp_backend.test_settings"

import django

django.setup()

from marketplace.schema import ensure_schema

ensure_schema()
