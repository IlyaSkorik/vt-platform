"""Acceptance-link builder for staff invitations."""

from __future__ import annotations

from django.conf import settings

__all__ = ["InvitationTokenService"]

# The web-client route that accepts an invitation (token as a path segment):
# ``/staff/invitations/:token`` (see the SPA router).
_ACCEPT_PATH = "/staff/invitations"


class InvitationTokenService:
    """Build the full invitation-acceptance URL for the web client."""

    def build_accept_url(self, *, raw_token: str) -> str:
        base_url = getattr(settings, "FRONTEND_BASE_URL", "https://app.vzlyot-talantov.by")
        return f"{base_url.rstrip('/')}{_ACCEPT_PATH}/{raw_token}"
