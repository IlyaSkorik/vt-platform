"""Public programme routes (anyone-facing).

Mounted separately from the organizer :mod:`~apps.programs.presentation.urls` router so
the public edge shares no routing, auth, or namespace with the staff constructor.

The writes here look surprising for a "public" router and are not: they are how the host
drives the day from the link the organizer handed them. Authorization is per *edition*
rather than per user - a link either was granted control or was not - and one that was
not refuses indistinguishably from a slug that does not exist.

Two of them write what only the host ever reads back - who is standing behind the stage,
and the line she wrote to herself about an act. They are routed beside the others because
the credential is the same one; what keeps them private is that no other edition's payload
has a field for them at all.
"""

from __future__ import annotations

from django.urls import path

from .api.v1.public_views import (
    PublicProgramDetailView,
    PublicProgramOrderView,
    PublicProgramRowBackstageView,
    PublicProgramRowNoteView,
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
    path(
        "public/programs/<str:slug>/rows/<str:item_id>/backstage",
        PublicProgramRowBackstageView.as_view(),
        name="row-backstage",
    ),
    path(
        "public/programs/<str:slug>/rows/<str:item_id>/note",
        PublicProgramRowNoteView.as_view(),
        name="row-note",
    ),
]
