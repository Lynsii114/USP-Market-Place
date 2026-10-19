from django.http import JsonResponse
from django.urls import include, path


def root(request):
    return JsonResponse(
        {
            "name": "USP Marketplace API",
            "status": "ok",
            "health": "/api/health",
        }
    )


urlpatterns = [
    path("", root),
    path("api/", include("marketplace.urls")),
]
