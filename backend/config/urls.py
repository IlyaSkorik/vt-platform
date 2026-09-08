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
from django.urls import include, path, re_path

from config.api_docs import redoc_view, schema_view, swagger_ui_view
from config.seo import llms_txt, robots_txt, sitemap_xml
from config.spa import spa_index
from config.status import status_json, status_page


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
    # The probes above answer a load balancer; these answer a person and an
    # uptime monitor. Public and unauthenticated by design (config.status).
    path("status", status_page, name="status"),
    path("status.json", status_json, name="status-json"),
    # What a crawler reads first. Served from the API rather than shipped as a
    # static file because the sitemap has to name the competitions that exist
    # right now, not the ones that existed at the last frontend build.
    path("robots.txt", robots_txt, name="robots-txt"),
    path("sitemap.xml", sitemap_xml, name="sitemap-xml"),
    # The same map written for a language model instead of a crawler (llmstxt.org),
    # and generated for the same reason: it names the competitions that exist right
    # now, and a stale answer about a deadline is worse than no answer.
    path("llms.txt", llms_txt, name="llms-txt"),
    # OpenAPI 3.1 contract + docs (drf-spectacular, API-000 §25). Open in DEBUG;
    # behind HTTP Basic auth everywhere else, and unmounted if a deployment never
    # configured credentials — see config/api_docs.py for why it fails closed.
    path("api/schema/", schema_view, name="schema"),
    path("api/schema/swagger-ui/", swagger_ui_view, name="swagger-ui"),
    path("api/schema/redoc/", redoc_view, name="redoc"),
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
    # The participant's own notification feed ("Уведомления").
    path("api/v1/", include("apps.notifications.presentation.urls")),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

# The SPA shell, served with its <head> already resolved (config.spa).
#
# Mounted last so it can never shadow a real route, and the negative lookahead
# keeps it away from /api/ entirely: a client silently parsing an HTML page as
# its JSON payload is a far worse failure than a 404. Whether a bundle is
# actually configured is decided inside the view, per request, rather than here —
# read at import time the setting could not be overridden in a test, nor changed
# without rebuilding the URLconf. Unconfigured, the view raises Http404 and the
# address behaves exactly as if this pattern were absent.
urlpatterns += [
    re_path(
        # `(?:…)` and not `(…)`: a capturing group here is handed to the view as a
        # positional argument, and `spa_index` takes only the request.
        r"^(?!api/|admin/|static/|media/|healthz|readyz|status(?:\.json)?$|robots\.txt|sitemap\.xml).*$",
        spa_index,
    ),
]
