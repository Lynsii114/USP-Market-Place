import os

from django.conf import settings

ADMIN_EMAIL = os.getenv("ADMIN_EMAIL", "Admin@usp.ac.fj")
# The familiar default is confined to explicit local development.
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "Admin12345" if settings.DEBUG else "")
ADMIN_USERNAME = "Admin"

