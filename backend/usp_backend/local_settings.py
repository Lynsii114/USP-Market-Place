"""Explicitly isolated laptop demo and test settings. Never connects to MySQL."""
import os

# Satisfy the base configuration parser; the connection below replaces it before
# Django loads apps or opens a database connection.
os.environ.setdefault("DATABASE_URL", "mysql+pymysql://unused:unused@127.0.0.1/unused")
from .settings import *  # noqa: F403,E402

DEBUG = True
SECRET_KEY = "local-inventory-demo-only-do-not-deploy"
ALLOWED_HOSTS = ["127.0.0.1", "localhost", "testserver"]
DATABASES = {"default": {"ENGINE": "django.db.backends.sqlite3", "NAME": BASE_DIR / "inventory-demo.db"}}
AUTO_ENSURE_SCHEMA = True
LOCAL_DB_SYNC = False
LOCAL_DB_SYNC_ON_START = False
CORS_ALLOWED_ORIGINS = ["http://localhost:5173", "http://127.0.0.1:5173"]
CORS_ALLOWED_ORIGIN_SUFFIXES = []
