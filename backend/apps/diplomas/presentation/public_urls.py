"""Public diploma verification routes (anyone-facing).

Mounted separately from the organizer :mod:`~apps.diplomas.presentation.urls`
router so the public read edge shares no routing, auth, or namespace with the
staff diplomas workspace.
"""

from __future__ import annotations

from django.urls import path

from .api.v1.public_views import PublicDiplomaVerificationView

app_name = "public_diplomas"

urlpatterns = [
    path(
        "public/diplomas/verify/<str:verification_token>",
        PublicDiplomaVerificationView.as_view(),
        name="verify",
    ),
]
