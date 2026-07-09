from __future__ import annotations

from apps.organization.application.exceptions import OrganizationNotFoundError
from apps.organization.application.interfaces import EmailGateway, OrganizationRepository
from apps.organization.domain.events import StaffInvitationIssued

__all__ = ["SendInvitationEmailHandler"]


class SendInvitationEmailHandler:
    def __init__(self, *, emails: EmailGateway, organizations: OrganizationRepository) -> None:
        self._emails = emails
        self._organizations = organizations

    def __call__(self, event: StaffInvitationIssued) -> None:
        organization = self._organizations.get(event.organization_id)
        if organization is None:
            raise OrganizationNotFoundError(f"Organization with ID {event.organization_id} not found.")

        self._emails.send_staff_invitation(
            recipient_email=event.email,
            organization_name=organization.name,
            role=event.role,
            expires_at=event.expires_at,
            token=event.raw_token,
        )
