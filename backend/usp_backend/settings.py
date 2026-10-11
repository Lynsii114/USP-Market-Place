import os
import tempfile
from pathlib import Path
from urllib.parse import parse_qs, urlparse

import certifi
from dotenv import load_dotenv

load_dotenv()
os.environ.setdefault("SSL_CERT_FILE", certifi.where())

BASE_DIR = Path(__file__).resolve().parent.parent
SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-key")
DEBUG = os.getenv("DEBUG", "1") == "1"


def env_list(name, default=""):
    return [value.strip() for value in os.getenv(name, default).split(",") if value.strip()]


ALLOWED_HOSTS = env_list(
    "DJANGO_ALLOWED_HOSTS",
    "127.0.0.1,localhost,testserver,.vercel.app",
)
CSRF_TRUSTED_ORIGINS = env_list("CSRF_TRUSTED_ORIGINS")
CORS_ALLOWED_ORIGINS = env_list(
    "CORS_ALLOWED_ORIGINS",
    "http://localhost:5173,http://localhost:5174,http://127.0.0.1:5173,http://127.0.0.1:5174,https://usp-market-place.vercel.app",
)
CORS_ALLOWED_ORIGIN_SUFFIXES = env_list("CORS_ALLOWED_ORIGIN_SUFFIXES")

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


def db_ssl_ca_path(default_ca):
    ca_cert = os.getenv("DB_SSL_CA_CERT", "").strip()
    if ca_cert:
        ca_path = Path(tempfile.gettempdir()) / "aiven-ca.pem"
        ca_path.write_text(ca_cert.replace("\\n", "\n"), encoding="utf-8")
        return str(ca_path)
    return os.getenv("DB_SSL_CA", default_ca)


def db_ssl_options(ssl_mode, ca_path=None):
    ssl_mode = ssl_mode.upper()
    if ssl_mode in {"1", "TRUE", "REQUIRED", "REQUIRE"}:
        return {"ssl": {}}
    if ssl_mode in {"VERIFY_CA", "VERIFY_IDENTITY"}:
        ssl_options = {"ca": ca_path or db_ssl_ca_path(certifi.where())}
        if ssl_mode == "VERIFY_IDENTITY":
            ssl_options["check_hostname"] = True
        return {"ssl": ssl_options}
    return None


def database_config():
    db_host = os.getenv("DB_HOST")
    if db_host:
        required_db_env = ["DB_DATABASE", "DB_USERNAME", "DB_PASSWORD", "DB_SSL"]
        missing_db_env = [name for name in required_db_env if not os.getenv(name)]
        if missing_db_env:
            raise RuntimeError(f"Missing required database environment variables: {', '.join(missing_db_env)}")
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
        ssl_options = db_ssl_options(os.getenv("DB_SSL", ""))
        if ssl_options:
            config["default"]["OPTIONS"] = ssl_options
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
        ssl_value = query.get("ssl", query.get("sslmode", [""]))[0]
        ssl_options = db_ssl_options(ssl_value, query.get("ssl_ca", [None])[0])
        if ssl_options:
            config["default"]["OPTIONS"] = ssl_options
        return config

    raise RuntimeError("SQLite has been disabled. DATABASE_URL must use mysql+pymysql://")


DATABASES = database_config()
