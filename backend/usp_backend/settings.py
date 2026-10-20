import os
from pathlib import Path

import certifi
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent.parent / ".env")
os.environ.setdefault("SSL_CERT_FILE", certifi.where())

BASE_DIR = Path(__file__).resolve().parent.parent
SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-key")
DEBUG = True


ALLOWED_HOSTS = ["127.0.0.1", "localhost", "[::1]", "testserver"]
CORS_ALLOWED_ORIGINS = [
    "http://localhost:5173", "http://127.0.0.1:5173",
    "http://localhost:5174", "http://127.0.0.1:5174",
]
CSRF_TRUSTED_ORIGINS = CORS_ALLOWED_ORIGINS.copy()
AUTO_ENSURE_SCHEMA = os.getenv("AUTO_ENSURE_SCHEMA", "1") == "1"

INSTALLED_APPS = [
    "django.contrib.staticfiles",
    "marketplace.apps.MarketplaceConfig",
]

MIDDLEWARE = [
    "usp_backend.middleware.JsonCorsMiddleware",
    "django.middleware.common.CommonMiddleware",
    "marketplace.authentication.ApiIdentityMiddleware",
]

ROOT_URLCONF = "usp_backend.urls"
WSGI_APPLICATION = "usp_backend.wsgi.application"
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
EMAIL_TIMEOUT = int(os.getenv("EMAIL_TIMEOUT", "20"))
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
    """Use only this computer's MySQL server; remote database settings are ignored."""
    host = os.getenv("LOCAL_DB_HOST", "127.0.0.1")
    if host not in {"localhost", "127.0.0.1", "::1"}:
        raise RuntimeError("LOCAL_DB_HOST must be a loopback address for local-only use")
    return {
        "default": {
            "ENGINE": "usp_backend.mysql_backend",
            "NAME": os.getenv("LOCAL_DB_DATABASE", "usp_marketplace"),
            "USER": os.getenv("LOCAL_DB_USERNAME", "root"),
            "PASSWORD": os.getenv("LOCAL_DB_PASSWORD", ""),
            "HOST": host,
            "PORT": os.getenv("LOCAL_DB_PORT", "3306"),
            "CONN_MAX_AGE": 0,
            "OPTIONS": {"connect_timeout": 5, "read_timeout": 10, "write_timeout": 10},
        }
    }


DATABASES = database_config()
