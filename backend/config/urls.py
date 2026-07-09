"""Root URL configuration.

Mounts the OpenAPI schema/documentation, health probes, and the Django admin.
Each bounded context declares its own routes under ``presentation/urls.py``;
those are mounted here under the versioned ``/api/v1/`` prefix (ARCH-001 §14,
API-000 §2) as contexts expose endpoints. No business endpoints exist during
bootstrap.
"""

from __future__ import annotations

from django.contrib import admin
from django.http import HttpRequest, JsonResponse
from django.urls import include, path
from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularRedocView,
    SpectacularSwaggerView,
)


def healthz(_request: HttpRequest) -> JsonResponse:
    """Liveness probe (ARCH-001 §17.4)."""
    return JsonResponse({"status": "ok"})


def readyz(_request: HttpRequest) -> JsonResponse:
    """Readiness probe (ARCH-001 §17.4)."""
    return JsonResponse({"status": "ready"})


urlpatterns = [
    path("admin/", admin.site.urls),
    path("healthz", healthz, name="healthz"),
    path("readyz", readyz, name="readyz"),
    # OpenAPI 3.1 contract + docs (drf-spectacular, API-000 §25).
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path(
        "api/schema/swagger-ui/",
        SpectacularSwaggerView.as_view(url_name="schema"),
        name="swagger-ui",
    ),
    path(
        "api/schema/redoc/",
        SpectacularRedocView.as_view(url_name="schema"),
        name="redoc",
    ),
    # Versioned bounded-context routers (ARCH-001 §14, API-000 §2).
    path("api/v1/", include("apps.identity.presentation.urls")),
    path("api/v1/", include("apps.participants.presentation.urls")),
    # Composition edge (owned by no single context — e.g. GET /users/me).
    path("api/v1/", include("apps.composition.presentation.urls")),
]
