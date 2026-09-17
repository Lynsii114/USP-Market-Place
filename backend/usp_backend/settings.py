import os
from pathlib import Path
from urllib.parse import urlparse

from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent
SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-key")
DEBUG = os.getenv("DEBUG", "1") == "1"
ALLOWED_HOSTS = ["127.0.0.1", "localhost", "testserver"]

INSTALLED_APPS = [
    "django.contrib.contenttypes",
    "django.contrib.staticfiles",
    "marketplace.apps.MarketplaceConfig",
]

MIDDLEWARE = [
    "usp_backend.middleware.JsonCorsMiddleware",
    "django.middleware.common.CommonMiddleware",
]

ROOT_URLCONF = "usp_backend.urls"
DEFAULT_AUTO_FIELD = "django.db.models.AutoField"
USE_TZ = True
TIME_ZONE = "UTC"
STATIC_URL = "static/"


def database_config():
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        raise RuntimeError("DATABASE_URL is required. Set it to your MySQL database URL in backend/.env")

    parsed = urlparse(database_url)
    if parsed.scheme.startswith("mysql"):
        return {
            "default": {
                "ENGINE": "usp_backend.mysql_backend",
                "NAME": parsed.path.lstrip("/"),
                "USER": parsed.username or "",
                "PASSWORD": parsed.password or "",
                "HOST": parsed.hostname or "localhost",
                "PORT": str(parsed.port or 3306),
            }
        }

    raise RuntimeError("SQLite has been disabled. DATABASE_URL must use mysql+pymysql://")


DATABASES = database_config()
