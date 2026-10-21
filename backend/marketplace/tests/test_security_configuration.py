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

    def test_debug_truthy_values(self):
        for value in ("1", "TRUE", " yes ", "On"):
            with self.subTest(value=value):
                settings = self.load_settings({"SECRET_KEY": secrets.token_urlsafe(64), "DEBUG": value})
                self.assertTrue(settings["DEBUG"])
