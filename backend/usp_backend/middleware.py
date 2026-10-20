from django.conf import settings
from django.http import HttpResponse


class JsonCorsMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

        if settings.AUTO_ENSURE_SCHEMA:
            from marketplace.schema import ensure_schema

            ensure_schema()

    def __call__(self, request):
        if request.method == "OPTIONS":
            response = HttpResponse()
        else:
            response = self.get_response(request)

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
        return origin in settings.CORS_ALLOWED_ORIGINS
