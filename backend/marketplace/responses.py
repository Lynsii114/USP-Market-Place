import json

from django.http import JsonResponse

from .exceptions import ApiError


def json_body(request):
    try:
        return json.loads(request.body.decode("utf-8") or "{}")
    except json.JSONDecodeError as exc:
        raise ApiError("Invalid JSON body", 400) from exc


def error_response(detail, status=400):
    return JsonResponse({"detail": detail}, status=status)


def method_not_allowed():
    return error_response("Method not allowed", 405)


def api_response(data, safe=True, status=200):
    return JsonResponse(data, safe=safe, status=status)


def handle_api_error(exc):
    return error_response(exc.detail, exc.status)

