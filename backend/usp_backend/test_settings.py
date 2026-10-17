from .local_settings import *  # noqa: F403

# Standalone pytest also remains isolated; it never opens the demo database.
DATABASES = {"default": {"ENGINE": "django.db.backends.sqlite3", "NAME": ":memory:"}}
