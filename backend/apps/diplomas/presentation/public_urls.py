"""Public diploma verification routes (anyone-facing).

Mounted separately from the organizer :mod:`~apps.diplomas.presentation.urls`
router so the public read edge shares no routing, auth, or namespace with the
staff diplomas workspace.
"""

from __future__ import annotations

from django.urls import path

from .api.v1.diplomas.fonts import PublicBundledFontView
from .api.v1.public_views import PublicDiplomaVerificationView

app_name = "public_diplomas"

urlpatterns = [
    path(
        "public/diplomas/verify/<str:verification_token>",
        PublicDiplomaVerificationView.as_view(),
        name="verify",
    ),
    # The bundled font files. Public because a browser fetches an `@font-face` source with
    # no Authorization header — a token here would mean the editor previews in a fallback
    # face while the PDF uses the real one, which is the mismatch this exists to remove.
    path(
        "public/diploma-fonts/<str:family>/<str:variant>.ttf",
        PublicBundledFontView.as_view(),
        name="bundled-font",
    ),
]
