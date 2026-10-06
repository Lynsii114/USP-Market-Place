import os
from pathlib import Path
from urllib.parse import parse_qs, urlparse

import certifi
from dotenv import load_dotenv

load_dotenv()
os.environ.setdefault("SSL_CERT_FILE", certifi.where())

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
EMAIL_BACKEND = os.getenv(
    "EMAIL_BACKEND",
    "django.core.mail.backends.smtp.EmailBackend" if os.getenv("EMAIL_HOST") else "django.core.mail.backends.console.EmailBackend",
)
EMAIL_HOST = os.getenv("EMAIL_HOST", "")
EMAIL_PORT = int(os.getenv("EMAIL_PORT", "587"))
EMAIL_USE_TLS = os.getenv("EMAIL_USE_TLS", "1") == "1"
EMAIL_USE_SSL = os.getenv("EMAIL_USE_SSL", "0") == "1"
EMAIL_HOST_USER = os.getenv("EMAIL_HOST_USER", "")
EMAIL_HOST_PASSWORD = os.getenv("EMAIL_HOST_PASSWORD", "").replace(" ", "")
DEFAULT_FROM_EMAIL = os.getenv("DEFAULT_FROM_EMAIL", "no-reply@usp-marketplace.local")
EMAIL_TIMEOUT = int(os.getenv("EMAIL_TIMEOUT", "20"))
RESEND_API_KEY = os.getenv("RESEND_API_KEY", "")
RESEND_FROM_EMAIL = os.getenv("RESEND_FROM_EMAIL", DEFAULT_FROM_EMAIL)
MICROSOFT_CLIENT_ID = os.getenv("MICROSOFT_CLIENT_ID", "")
MICROSOFT_TENANT_ID = os.getenv("MICROSOFT_TENANT_ID", "")

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
        },
    },
    "loggers": {
        "marketplace.email": {
            "handlers": ["console"],
            "level": os.getenv("EMAIL_LOG_LEVEL", "INFO"),
            "propagate": False,
        },
    },
}


def database_config():
    db_host = os.getenv("DB_HOST")
    if db_host:
        config = {
            "default": {
                "ENGINE": "usp_backend.mysql_backend",
                "NAME": os.getenv("DB_DATABASE", ""),
                "USER": os.getenv("DB_USERNAME", ""),
                "PASSWORD": os.getenv("DB_PASSWORD", ""),
                "HOST": db_host,
                "PORT": os.getenv("DB_PORT", "3306"),
            }
        }
        ssl_mode = os.getenv("DB_SSL", "").upper()
        if ssl_mode in {"1", "TRUE", "REQUIRED"}:
            config["default"]["OPTIONS"] = {"ssl": {}}
        elif ssl_mode in {"VERIFY_CA", "VERIFY_IDENTITY"}:
            ssl_options = {"ca": os.getenv("DB_SSL_CA", certifi.where())}
            if ssl_mode == "VERIFY_IDENTITY":
                ssl_options["check_hostname"] = True
            config["default"]["OPTIONS"] = {"ssl": ssl_options}
        return config

    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        raise RuntimeError("DATABASE_URL or DB_HOST is required. Set your MySQL database details in backend/.env")

    parsed = urlparse(database_url)
    if parsed.scheme.startswith("mysql"):
        config = {
            "default": {
                "ENGINE": "usp_backend.mysql_backend",
                "NAME": parsed.path.lstrip("/"),
                "USER": parsed.username or "",
                "PASSWORD": parsed.password or "",
                "HOST": parsed.hostname or "localhost",
                "PORT": str(parsed.port or 3306),
            }
        }
        query = parse_qs(parsed.query)
        ssl_value = query.get("ssl", query.get("sslmode", [""]))[0].upper()
        if ssl_value in {"1", "TRUE", "REQUIRED", "REQUIRE"}:
            config["default"]["OPTIONS"] = {"ssl": {}}
        elif ssl_value in {"VERIFY_CA", "VERIFY_IDENTITY"}:
            ssl_options = {"ca": query.get("ssl_ca", [certifi.where()])[0]}
            if ssl_value == "VERIFY_IDENTITY":
                ssl_options["check_hostname"] = True
            config["default"]["OPTIONS"] = {"ssl": ssl_options}
        return config

    raise RuntimeError("SQLite has been disabled. DATABASE_URL must use mysql+pymysql://")


DATABASES = database_config()
