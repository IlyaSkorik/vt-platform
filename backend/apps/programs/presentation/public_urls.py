"""Public program routes (anyone-facing).

Mounted separately from the organizer :mod:`~apps.programs.presentation.urls` router so
the public read edge shares no routing, auth, or namespace with the staff constructor.
"""

from __future__ import annotations

from django.urls import path

from .api.v1.public_views import PublicProgramDetailView

app_name = "public_programs"

urlpatterns = [
    path("public/programs/<str:slug>", PublicProgramDetailView.as_view(), name="detail"),
]
