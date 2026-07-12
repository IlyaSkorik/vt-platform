"""Public Festival Catalog routes (participant-facing).

Mounted separately from the organizer :mod:`~apps.competitions.presentation.urls`
router so the public read edge shares no routing, auth, or namespace with the
staff control panel.
"""

from __future__ import annotations

from django.urls import path

from .api.v1.public_views import PublicFestivalCatalogView, PublicFestivalDetailView

app_name = "public_catalog"

urlpatterns = [
    path("public/festivals", PublicFestivalCatalogView.as_view(), name="festivals"),
    path(
        "public/festivals/<str:festival_id>",
        PublicFestivalDetailView.as_view(),
        name="festival-detail",
    ),
]
