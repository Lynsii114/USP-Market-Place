import os
from unittest.mock import patch

from django.test import SimpleTestCase

from usp_backend.middleware import JsonCorsMiddleware
from usp_backend.settings import database_config


class LocalConfigurationTests(SimpleTestCase):
    def test_legacy_remote_configuration_cannot_select_a_remote_database(self):
        with patch.dict(os.environ, {
            "DB_HOST": "remote.example.com",
            "DATABASE_URL": "mysql://user:password@remote.example.com/remote",
        }, clear=True):
            database = database_config()["default"]
        self.assertEqual(database["HOST"], "127.0.0.1")
        self.assertEqual(database["NAME"], "usp_marketplace")

    def test_remote_local_database_host_is_rejected(self):
        with patch.dict(os.environ, {"LOCAL_DB_HOST": "remote.example.com"}, clear=True):
            with self.assertRaisesMessage(RuntimeError, "loopback"):
                database_config()

    def test_cors_accepts_local_frontend_and_rejects_external_sites(self):
        self.assertTrue(JsonCorsMiddleware.is_origin_allowed("http://localhost:5173"))
        self.assertFalse(JsonCorsMiddleware.is_origin_allowed("https://remote.example.com"))
