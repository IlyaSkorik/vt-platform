"""Root URL configuration.

Mounts the OpenAPI schema/documentation, health probes, and the Django admin.
Each bounded context declares its own routes under ``presentation/urls.py``;
those are mounted here under the versioned ``/api/v1/`` prefix (ARCH-001 §14,
API-000 §2) as contexts expose endpoints. No business endpoints exist during
bootstrap.
"""

from __future__ import annotations

from django.conf import settings
from django.conf.urls.static import static
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
    path("api/v1/", include("apps.organization.presentation.urls")),
    # The platform operator's own console: connected organizations and their terms.
    path("api/v1/", include("apps.platform.presentation.urls")),
    path("api/v1/", include("apps.participants.presentation.urls")),
    # Composition edge (owned by no single context — e.g. GET /users/me).
    path("api/v1/", include("apps.composition.presentation.urls")),
    path("api/v1/", include("apps.competitions.presentation.urls")),
    # Personal, user-owned teacher directory (reusable across applications).
    path("api/v1/", include("apps.teachers.presentation.urls")),
    # Applicant-facing application (order) lifecycle.
    path("api/v1/", include("apps.applications.presentation.urls")),
    # Standalone diplomas workspace (template library + assignments).
    path("api/v1/", include("apps.diplomas.presentation.urls")),
    # The organizer's programme constructor (running order + its public editions).
    path("api/v1/", include("apps.programs.presentation.urls")),
    # The jury's protocols: results per nomination, and their publication.
    path("api/v1/", include("apps.results.presentation.urls")),
    # Public, unauthenticated participant catalog (dedicated read model).
    path("api/v1/", include("apps.competitions.presentation.public_urls")),
    # Public, unauthenticated diploma verification (the printed QR's target).
    path("api/v1/", include("apps.diplomas.presentation.public_urls")),
    # Public, unauthenticated programme screens (one slug per published edition).
    path("api/v1/", include("apps.programs.presentation.public_urls")),
    # Public, unauthenticated results: a published protocol, and a competition's index of them.
    path("api/v1/", include("apps.results.presentation.public_urls")),
    # The participant's own issued documents ("Мои документы").
    path("api/v1/", include("apps.diplomas.presentation.me_urls")),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
