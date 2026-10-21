"""Exercise environment loading without starting Django or connecting to a database."""
import os
from io import StringIO
from pathlib import Path
import runpy
import secrets
import unittest
from unittest.mock import patch

from django.core.exceptions import ImproperlyConfigured
from dotenv import load_dotenv


SETTINGS_PATH = Path(__file__).resolve().parents[2] / "usp_backend" / "settings.py"


class SecurityConfigurationTests(unittest.TestCase):
    def load_settings(self, environment, dotenv_text=""):
        with patch.dict(os.environ, environment, clear=True):
            with patch("dotenv.load_dotenv", side_effect=lambda *args, **kwargs: load_dotenv(stream=StringIO(dotenv_text), **kwargs)):
                return runpy.run_path(str(SETTINGS_PATH))

    def test_missing_empty_and_retired_keys_fail_without_exposing_values(self):
        for key in (None, "", "  ", "dev-secret-key"):
            with self.subTest(key_present=key is not None):
                environment = {} if key is None else {"SECRET_KEY": key}
                with self.assertRaises(ImproperlyConfigured) as error:
                    self.load_settings(environment)
                self.assertEqual(
                    str(error.exception),
                    "Set SECRET_KEY to a unique secret in the environment or backend/.env.",
                )

    def test_local_dotenv_loads_key_and_development_options(self):
        key = secrets.token_urlsafe(64)
        settings = self.load_settings({}, f"SECRET_KEY={key}\nDEBUG=true\nALLOWED_HOSTS=localhost, 127.0.0.1,\n")
        self.assertTrue(settings["SECRET_KEY"] == key)
        self.assertTrue(settings["DEBUG"])
        self.assertEqual(settings["ALLOWED_HOSTS"], ["localhost", "127.0.0.1"])

    def test_railway_environment_takes_precedence_over_dotenv(self):
        key = secrets.token_urlsafe(64)
        settings = self.load_settings(
            {"SECRET_KEY": key, "DEBUG": "false", "ALLOWED_HOSTS": "app.up.railway.app, example.com"},
            f"SECRET_KEY={secrets.token_urlsafe(64)}\nDEBUG=true\nALLOWED_HOSTS=localhost\n",
        )
        self.assertTrue(settings["SECRET_KEY"] == key)
        self.assertFalse(settings["DEBUG"])
        self.assertEqual(settings["ALLOWED_HOSTS"], ["app.up.railway.app", "example.com"])

    def test_debug_is_disabled_by_default(self):
        settings = self.load_settings({"SECRET_KEY": secrets.token_urlsafe(64)})
        self.assertFalse(settings["DEBUG"])

    def test_resend_and_local_frontend_defaults(self):
        settings = self.load_settings({"SECRET_KEY": secrets.token_urlsafe(64)})
        self.assertEqual(settings["EMAIL_PROVIDER"], "resend")
        self.assertEqual(settings["FRONTEND_URL"], "http://localhost:5173")
        self.assertEqual(settings["RESEND_FROM_EMAIL"], "")

    def test_resend_ignores_unused_smtp_tls_conflict(self):
        settings = self.load_settings({
            "SECRET_KEY": secrets.token_urlsafe(64), "EMAIL_PROVIDER": "resend",
            "EMAIL_USE_TLS": "1", "EMAIL_USE_SSL": "1",
        })
        self.assertEqual(settings["EMAIL_PROVIDER"], "resend")

    def test_resend_overrides_stale_gmail_backend_in_local_and_railway(self):
        for base in ({"SECRET_KEY": secrets.token_urlsafe(64)}, self.railway_environment()):
            for provider in ("resend", "auto"):
                with self.subTest(mode=base.get("DATABASE_MODE", "local"), provider=provider):
                    settings = self.load_settings(dict(base, EMAIL_PROVIDER=provider,
                        EMAIL_HOST="smtp.gmail.com", EMAIL_PORT="587",
                        EMAIL_BACKEND="django.core.mail.backends.smtp.EmailBackend",
                        EMAIL_USE_TLS="1", EMAIL_USE_SSL="1",
                        RESEND_API_KEY=secrets.token_urlsafe(32),
                        RESEND_FROM_EMAIL="Marketplace <no-reply@example.com>"))
                    self.assertEqual(settings["EMAIL_BACKEND"], settings["CONSOLE_EMAIL_BACKEND"])
                    self.assertEqual(settings["effective_email_provider"], "resend")

    def test_auto_without_resend_key_preserves_legacy_smtp(self):
        settings = self.load_settings({"SECRET_KEY": secrets.token_urlsafe(64),
            "EMAIL_PROVIDER": "auto", "EMAIL_HOST": "smtp.gmail.com"})
        self.assertEqual(settings["effective_email_provider"], "smtp")
        self.assertEqual(settings["EMAIL_BACKEND"], settings["SMTP_EMAIL_BACKEND"])

    def test_frontend_url_validation_and_railway_override(self):
        environment = self.railway_environment()
        self.assertEqual(self.load_settings(environment)["FRONTEND_URL"], "https://usp-market-place.vercel.app")
        environment["FRONTEND_URL"] = "https://shop.example.com/"
        self.assertEqual(self.load_settings(environment)["FRONTEND_URL"], "https://shop.example.com")
        for value in ("", "localhost:5173", "http://localhost:5173", "https://user:password@example.com", "https://example.com?token=value"):
            with self.subTest(value=value), self.assertRaises(ImproperlyConfigured):
                self.load_settings(dict(environment, FRONTEND_URL=value))

    def test_debug_truthy_values(self):
        for value in ("1", "TRUE", " yes ", "On"):
            with self.subTest(value=value):
                settings = self.load_settings({"SECRET_KEY": secrets.token_urlsafe(64), "DEBUG": value})
                self.assertTrue(settings["DEBUG"])

    def railway_environment(self):
        return {
            "DATABASE_MODE": "railway",
            "SECRET_KEY": secrets.token_urlsafe(64),
            "ALLOWED_HOSTS": "api.example.com",
            "DB_HOST": "mysql.example.com",
            "DB_PORT": "39149",
            "DB_USER": "root",
            "DB_DATABASE": "railway",
            "DB_PASSWORD": secrets.token_urlsafe(32),
        }

    def test_railway_database_and_security_without_connecting(self):
        environment = self.railway_environment()
        environment.update({
            "AUTO_ENSURE_SCHEMA": "1",
            "CORS_ALLOWED_ORIGINS": "https://shop.vercel.app/, https://shop.example.com",
        })
        settings = self.load_settings(environment)
        database = settings["DATABASES"]["default"]
        self.assertEqual(database["ENGINE"], "usp_backend.mysql_backend")
        self.assertEqual(database["HOST"], environment["DB_HOST"])
        self.assertEqual(database["PORT"], "39149")
        self.assertEqual(database["NAME"], "railway")
        self.assertTrue(database["PASSWORD"] == environment["DB_PASSWORD"])
        self.assertFalse(settings["AUTO_ENSURE_SCHEMA"])
        self.assertTrue(settings["SECURE_SSL_REDIRECT"])
        self.assertTrue(settings["CSRF_COOKIE_SECURE"])
        self.assertEqual(settings["SECURE_PROXY_SSL_HEADER"], ("HTTP_X_FORWARDED_PROTO", "https"))
        self.assertEqual(settings["CORS_ALLOWED_ORIGINS"], ["https://shop.vercel.app", "https://shop.example.com"])
        self.assertEqual(settings["CSRF_TRUSTED_ORIGINS"], settings["CORS_ALLOWED_ORIGINS"])

    def test_railway_missing_variables_never_fall_back_to_local_database(self):
        for name in ("DB_HOST", "DB_PORT", "DB_USER", "DB_DATABASE", "DB_PASSWORD", "ALLOWED_HOSTS"):
            with self.subTest(name=name):
                environment = self.railway_environment()
                del environment[name]
                with self.assertRaises(ImproperlyConfigured) as error:
                    self.load_settings(environment)
                self.assertIn(name, str(error.exception))

    def test_railway_detection(self):
        environment = self.railway_environment()
        del environment["DATABASE_MODE"]
        environment["RAILWAY_ENVIRONMENT_ID"] = "test-environment"
        settings = self.load_settings(environment)
        self.assertEqual(settings["DATABASE_MODE"], "railway")
        self.assertFalse(settings["AUTO_ENSURE_SCHEMA"])

    def test_local_database_is_preserved_despite_remote_variables(self):
        environment = self.railway_environment()
        environment.update({"DATABASE_MODE": "local", "DEBUG": "true", "LOCAL_DB_DATABASE": "xampp_test"})
        settings = self.load_settings(environment)
        database = settings["DATABASES"]["default"]
        self.assertEqual(database["HOST"], "127.0.0.1")
        self.assertEqual(database["PORT"], "3306")
        self.assertEqual(database["NAME"], "xampp_test")
        self.assertTrue(settings["AUTO_ENSURE_SCHEMA"])
        self.assertFalse(settings["SECURE_SSL_REDIRECT"])

    def test_invalid_database_mode_and_port_are_rejected(self):
        environment = self.railway_environment()
        environment["DATABASE_MODE"] = "typo"
        with self.assertRaises(ImproperlyConfigured):
            self.load_settings(environment)
        for value in ("invalid", "0", "65536"):
            environment = self.railway_environment()
            environment["DB_PORT"] = value
            with self.subTest(port=value), self.assertRaises(ImproperlyConfigured):
                self.load_settings(environment)
