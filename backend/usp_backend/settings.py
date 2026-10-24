import os
from pathlib import Path
from urllib.parse import urlsplit

import certifi
from django.core.exceptions import ImproperlyConfigured
from dotenv import load_dotenv


# Local .env values never override variables supplied by Railway.
load_dotenv(Path(__file__).resolve().parent.parent / ".env", override=False)
os.environ.setdefault("SSL_CERT_FILE", certifi.where())

BASE_DIR = Path(__file__).resolve().parent.parent
DATABASE_MODE = os.getenv(
    "DATABASE_MODE", "railway" if os.getenv("RAILWAY_ENVIRONMENT_ID") else "local"
).strip().lower()
if DATABASE_MODE not in {"local", "railway"}:
    raise ImproperlyConfigured("DATABASE_MODE must be local or railway.")

SECRET_KEY = os.getenv("SECRET_KEY", "")
if not SECRET_KEY.strip() or SECRET_KEY == "dev-secret-key":
    raise ImproperlyConfigured(
        "Set SECRET_KEY to a unique secret in the environment or backend/.env."
    )
DEBUG = os.getenv("DEBUG", "false").strip().lower() in {"1", "true", "yes", "on"}


ALLOWED_HOSTS = [
    host.strip()
    for host in os.getenv("ALLOWED_HOSTS", "127.0.0.1,localhost,[::1],testserver").split(",")
    if host.strip()
]
if DATABASE_MODE == "railway" and not os.getenv("ALLOWED_HOSTS", "").strip():
    raise ImproperlyConfigured("Set ALLOWED_HOSTS to the Railway backend hostname.")
CORS_ALLOWED_ORIGINS = [
    origin.strip().rstrip("/")
    for origin in os.getenv(
        "CORS_ALLOWED_ORIGINS",
        "" if DATABASE_MODE == "railway" else
        "http://localhost:5173,http://127.0.0.1:5173,http://localhost:5174,http://127.0.0.1:5174",
    ).split(",")
    if origin.strip()
]
CSRF_TRUSTED_ORIGINS = [
    origin.strip().rstrip("/")
    for origin in os.getenv("CSRF_TRUSTED_ORIGINS", ",".join(CORS_ALLOWED_ORIGINS)).split(",")
    if origin.strip()
]
# Never create/alter existing Railway tables during WSGI startup.
AUTO_ENSURE_SCHEMA = DATABASE_MODE == "local" and os.getenv("AUTO_ENSURE_SCHEMA", "1") == "1"

# Railway terminates HTTPS at its trusted reverse proxy.
SECURE_PROXY_SSL_HEADER = (
    ("HTTP_X_FORWARDED_PROTO", "https") if DATABASE_MODE == "railway" else None
)
SECURE_SSL_REDIRECT = not DEBUG and DATABASE_MODE == "railway"
# Railway's internal HTTP probe must receive 200, not an HTTPS redirect.
SECURE_REDIRECT_EXEMPT = [r"^api/health$"]
SESSION_COOKIE_SECURE = not DEBUG
CSRF_COOKIE_SECURE = not DEBUG
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_HSTS_SECONDS = 3600 if not DEBUG and DATABASE_MODE == "railway" else 0
SECURE_HSTS_INCLUDE_SUBDOMAINS = False
SECURE_HSTS_PRELOAD = False
X_FRAME_OPTIONS = "DENY"

INSTALLED_APPS = [
    "django.contrib.staticfiles",
    "marketplace.apps.MarketplaceConfig",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "usp_backend.middleware.JsonCorsMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "marketplace.authentication.ApiIdentityMiddleware",
]

ROOT_URLCONF = "usp_backend.urls"
WSGI_APPLICATION = "usp_backend.wsgi.application"
DEFAULT_AUTO_FIELD = "django.db.models.AutoField"
USE_TZ = True
TIME_ZONE = "UTC"
STATIC_URL = "static/"
FRONTEND_URL = os.getenv(
    "FRONTEND_URL",
    "https://usp-market-place.vercel.app" if DATABASE_MODE == "railway" else "http://localhost:5173",
).strip().rstrip("/")
frontend_url = urlsplit(FRONTEND_URL)
if (
    frontend_url.scheme not in {"http", "https"}
    or not frontend_url.hostname
    or frontend_url.username
    or frontend_url.password
    or frontend_url.query
    or frontend_url.fragment
    or (DATABASE_MODE == "railway" and frontend_url.scheme != "https")
):
    raise ImproperlyConfigured("FRONTEND_URL must be an absolute frontend URL (HTTPS on Railway), without credentials, query, or fragment.")
# Keep local demonstrations independent from production email credentials.
# Local runs use Gmail SMTP; Railway uses Resend HTTPS exclusively.
EMAIL_PROVIDER = "smtp" if DATABASE_MODE == "local" else "resend"
RESEND_API_KEY = os.getenv("RESEND_API_KEY", "").strip()
RESEND_FROM_EMAIL = os.getenv("RESEND_FROM_EMAIL", "").strip()
EMAIL_TIMEOUT = int(os.getenv("EMAIL_TIMEOUT", "20"))
if DATABASE_MODE == "local":
    EMAIL_HOST = os.getenv("EMAIL_HOST", "smtp.gmail.com").strip()
    EMAIL_PORT = int(os.getenv("EMAIL_PORT", "587"))
    EMAIL_USE_TLS = os.getenv("EMAIL_USE_TLS", "1").strip().lower() in {"1", "true", "yes", "on"}
    EMAIL_USE_SSL = os.getenv("EMAIL_USE_SSL", "0").strip().lower() in {"1", "true", "yes", "on"}
    EMAIL_HOST_USER = os.getenv("EMAIL_HOST_USER", "").strip()
    # Google app passwords are commonly displayed with spaces between groups.
    EMAIL_HOST_PASSWORD = os.getenv("EMAIL_HOST_PASSWORD", "").replace(" ", "").strip()
    DEFAULT_FROM_EMAIL = os.getenv("DEFAULT_FROM_EMAIL", EMAIL_HOST_USER).strip()
    if EMAIL_USE_TLS and EMAIL_USE_SSL:
        raise ImproperlyConfigured("Use either EMAIL_USE_TLS or EMAIL_USE_SSL, not both.")
    EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
else:
    # No SMTP transport or credentials are read in Railway.
    EMAIL_BACKEND = "django.core.mail.backends.dummy.EmailBackend"
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
    """Select Railway explicitly; keep local XAMPP settings separate."""
    if DATABASE_MODE == "railway":
        required = ("DB_HOST", "DB_PORT", "DB_USER", "DB_DATABASE", "DB_PASSWORD")
        missing = [name for name in required if not os.getenv(name, "").strip()]
        if missing:
            raise ImproperlyConfigured("Set required Railway variables: " + ", ".join(missing))
        try:
            port = int(os.environ["DB_PORT"])
        except ValueError:
            raise ImproperlyConfigured("DB_PORT must be an integer.") from None
        if not 1 <= port <= 65535:
            raise ImproperlyConfigured("DB_PORT must be between 1 and 65535.")
        return {
            "default": {
                "ENGINE": "usp_backend.mysql_backend",
                "NAME": os.environ["DB_DATABASE"],
                "USER": os.environ["DB_USER"],
                "PASSWORD": os.environ["DB_PASSWORD"],
                "HOST": os.environ["DB_HOST"],
                "PORT": str(port),
                "CONN_MAX_AGE": 60,
                "CONN_HEALTH_CHECKS": True,
                "OPTIONS": {"connect_timeout": 5, "read_timeout": 10, "write_timeout": 10},
            }
        }
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
