"""Local development using the existing XAMPP MySQL database."""
import os

from .settings import *  # noqa: F403

DEBUG = True
ALLOWED_HOSTS = ["localhost", "127.0.0.1", "testserver"]
DATABASES = {
    "default": {
        "ENGINE": "usp_backend.mysql_backend",
        "NAME": os.getenv("LOCAL_DB_DATABASE", "usp_marketplace"),
        "USER": os.getenv("LOCAL_DB_USERNAME", "root"),
        "PASSWORD": os.getenv("LOCAL_DB_PASSWORD", ""),
        "HOST": os.getenv("LOCAL_DB_HOST", "127.0.0.1"),
        "PORT": os.getenv("LOCAL_DB_PORT", "3306"),
        "OPTIONS": {"connect_timeout": 5, "read_timeout": 10, "write_timeout": 10},
    }
}
AUTO_ENSURE_SCHEMA = False
LOCAL_DB_SYNC = False
LOCAL_DB_SYNC_ON_START = False
CORS_ALLOWED_ORIGINS = ["http://localhost:5173", "http://127.0.0.1:5173"]
CORS_ALLOWED_ORIGIN_SUFFIXES = []
