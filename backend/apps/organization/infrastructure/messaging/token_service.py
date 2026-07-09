"""Acceptance-link builder for staff invitations."""

from __future__ import annotations

from django.conf import settings

__all__ = ["InvitationTokenService"]


class InvitationTokenService:
    """Build the full invitation-acceptance URL for the web client."""

    def build_accept_url(self, *, raw_token: str) -> str:
        base_url = getattr(settings, "STAFF_INVITATION_ACCEPT_URL_BASE", "https://app.vzlyot-talantov.by")
        return f"{base_url.rstrip('/')}/staff/invitations/accept?token={raw_token}"
