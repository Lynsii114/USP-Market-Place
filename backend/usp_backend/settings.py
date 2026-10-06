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
EMAIL_HOST = os.getenv("EMAIL_HOST", "")
EMAIL_PORT = int(os.getenv("EMAIL_PORT", "587"))
EMAIL_USE_TLS = os.getenv("EMAIL_USE_TLS", "1") == "1"
EMAIL_USE_SSL = os.getenv("EMAIL_USE_SSL", "0") == "1"
if EMAIL_USE_TLS and EMAIL_USE_SSL:
    raise RuntimeError("Set only one of EMAIL_USE_TLS or EMAIL_USE_SSL to 1")
EMAIL_HOST_USER = os.getenv("EMAIL_HOST_USER", "")
EMAIL_HOST_PASSWORD = os.getenv("EMAIL_HOST_PASSWORD", "").replace(" ", "")
DEFAULT_FROM_EMAIL = os.getenv("DEFAULT_FROM_EMAIL", EMAIL_HOST_USER or "no-reply@usp-marketplace.local")
SMTP_EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
CONSOLE_EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"
EMAIL_PROVIDER = os.getenv("EMAIL_PROVIDER", "auto").strip().lower()
if EMAIL_PROVIDER not in {"auto", "smtp", "resend", "console"}:
    raise RuntimeError("EMAIL_PROVIDER must be auto, smtp, resend, or console")
EMAIL_BACKEND = os.getenv(
    "EMAIL_BACKEND",
    SMTP_EMAIL_BACKEND if EMAIL_HOST else CONSOLE_EMAIL_BACKEND,
)
if EMAIL_PROVIDER == "smtp":
    EMAIL_BACKEND = SMTP_EMAIL_BACKEND
elif EMAIL_PROVIDER in {"console", "resend"}:
    EMAIL_BACKEND = CONSOLE_EMAIL_BACKEND
elif DEBUG and EMAIL_HOST and not (EMAIL_HOST_USER and EMAIL_HOST_PASSWORD) and EMAIL_BACKEND == SMTP_EMAIL_BACKEND:
    EMAIL_BACKEND = CONSOLE_EMAIL_BACKEND
RESEND_API_KEY = os.getenv("RESEND_API_KEY", "")
RESEND_FROM_EMAIL = os.getenv("RESEND_FROM_EMAIL", DEFAULT_FROM_EMAIL)
MICROSOFT_CLIENT_ID = os.getenv("MICROSOFT_CLIENT_ID", "")
MICROSOFT_TENANT_ID = os.getenv("MICROSOFT_TENANT_ID", "")
ALLOW_NON_USP_EMAILS = os.getenv("ALLOW_NON_USP_EMAILS", "1") == "1"


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
