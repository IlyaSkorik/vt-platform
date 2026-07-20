from __future__ import annotations

from apps.organization.application.exceptions import OrganizationNotFoundError
from apps.organization.application.interfaces import (
    EmailGateway,
    InvitationTokenService,
    OrganizationRepository,
)
from apps.organization.domain.events import StaffInvitationIssued

__all__ = ["SendInvitationEmailHandler"]


class SendInvitationEmailHandler:
    def __init__(
        self,
        *,
        emails: EmailGateway,
        organizations: OrganizationRepository,
        token_service: InvitationTokenService,
    ) -> None:
        self._emails = emails
        self._organizations = organizations
        self._token_service = token_service

    def __call__(self, event: StaffInvitationIssued) -> None:
        organization = self._organizations.get(event.organization_id)
        if organization is None:
            raise OrganizationNotFoundError(f"Organization with ID {event.organization_id} not found.")

        # The email must carry the full web-client acceptance link, not the raw
        # token secret on its own.
        accept_url = self._token_service.build_accept_url(raw_token=event.raw_token)
        self._emails.send_staff_invitation(
            recipient_email=event.email,
            organization_name=organization.name,
            role=event.role,
            expires_at=event.expires_at,
            token=accept_url,
        )
