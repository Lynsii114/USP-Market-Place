import os
from urllib.parse import urlparse

from django.conf import settings
from django.http import HttpResponse


class JsonCorsMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response
        from marketplace.schema import ensure_schema

        ensure_schema()
        if os.getenv("LOCAL_DB_SYNC_ON_START", "0") == "1":
            from marketplace.db_sync import sync_cloud_to_local

            sync_cloud_to_local()

    def __call__(self, request):
        if request.method == "OPTIONS":
            response = HttpResponse()
        else:
            response = self.get_response(request)
            from marketplace.db_sync import should_sync_request, sync_cloud_to_local

            if should_sync_request(request, response):
                sync_cloud_to_local()

        origin = request.headers.get("Origin")
        if self.is_origin_allowed(origin):
            response["Access-Control-Allow-Origin"] = origin
            response["Access-Control-Allow-Credentials"] = "true"
            response["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS"
            response["Access-Control-Allow-Headers"] = "Content-Type, Authorization"
        return response

    @staticmethod
    def is_origin_allowed(origin):
        if not origin:
            return False
        if origin in settings.CORS_ALLOWED_ORIGINS:
            return True
        hostname = urlparse(origin).hostname or ""
        return any(hostname == suffix.lstrip(".") or hostname.endswith(suffix) for suffix in settings.CORS_ALLOWED_ORIGIN_SUFFIXES)
