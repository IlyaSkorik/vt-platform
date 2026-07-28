"""Public programme routes (anyone-facing).

Mounted separately from the organizer :mod:`~apps.programs.presentation.urls` router so
the public edge shares no routing, auth, or namespace with the staff constructor.

The two writes here look surprising for a "public" router and are not: they are how the
host drives the day from the link the organizer handed them. Authorization is per
*edition* rather than per user - a link either was granted control or was not - and one
that was not refuses indistinguishably from a slug that does not exist.
"""

from __future__ import annotations

from django.urls import path

from .api.v1.public_views import (
    PublicProgramDetailView,
    PublicProgramOrderView,
    PublicProgramRowProgressView,
)

app_name = "public_programs"

urlpatterns = [
    path("public/programs/<str:slug>", PublicProgramDetailView.as_view(), name="detail"),
    path("public/programs/<str:slug>/order", PublicProgramOrderView.as_view(), name="order"),
    path(
        "public/programs/<str:slug>/rows/<str:item_id>/progress",
        PublicProgramRowProgressView.as_view(),
        name="row-progress",
    ),
]
