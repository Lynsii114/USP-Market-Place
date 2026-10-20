"""Explicitly isolated laptop demo and test settings. Never connects to MySQL."""
from .settings import *  # noqa: F403,E402

DEBUG = True
SECRET_KEY = "local-inventory-demo-only-do-not-deploy"
ALLOWED_HOSTS = ["127.0.0.1", "localhost", "testserver"]
DATABASES = {"default": {"ENGINE": "django.db.backends.sqlite3", "NAME": BASE_DIR / "inventory-demo.db"}}
AUTO_ENSURE_SCHEMA = True
CORS_ALLOWED_ORIGINS = ["http://localhost:5173", "http://127.0.0.1:5173"]
