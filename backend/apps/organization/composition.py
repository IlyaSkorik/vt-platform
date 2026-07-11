"""Composition root for the Organization bounded context.

The one place framework-free use cases and services are wired to their concrete
infrastructure adapters (ARCH-001 §7.3, Dependency Inversion). Callers — the
management command, the (Phase 3) API views, the (Phase 2) ``/users/me``
composition edge — ask this module for a fully-assembled handler or service and
stay ignorant of *which* repository, clock, hasher, or event transport sits
behind each port. Swapping an adapter (or a fake, in tests) changes only here.

Every adapter is stateless and cheap to build, so handlers/services are assembled
per call; there is no shared mutable state.
"""

from __future__ import annotations

from datetime import datetime

from django.conf import settings
from django.core.mail import EmailMessage

from apps.organization.application.handlers import (
    AcceptStaffInvitationHandler,
    GetOrganizationProfileHandler,
    GetStaffInvitationHandler,
    InviteStaffHandler,
    ProvisionOwnerHandler,
    SendInvitationEmailHandler,
)
from apps.organization.application.interfaces import EmailGateway, InvitationTokenService
from apps.organization.application.read_models import StaffMembershipReader
from apps.organization.domain.events import StaffInvitationIssued
from apps.organization.domain.value_objects import OrganizationName, StaffEmail, StaffRole
from apps.organization.infrastructure.messaging import (
    EventDispatcher,
    Sha256InvitationTokenHasher,
)
from apps.organization.infrastructure.read_models import DjangoOrganizationDirectory
from apps.organization.infrastructure.repositories import (
    DjangoOrganizationRepository,
    DjangoStaffInvitationRepository,
    DjangoStaffMembershipRepository,
)
from apps.organization.infrastructure.system import SystemClock, Uuid7Generator

__all__ = [
    "build_accept_staff_invitation_handler",
    "build_get_organization_profile_handler",
    "build_get_staff_invitation_handler",
    "build_invite_staff_handler",
    "build_organization_directory",
    "build_provision_owner_handler",
    "build_staff_membership_read_service",
]


def _build_event_dispatcher() -> EventDispatcher:
    dispatcher = EventDispatcher()
    dispatcher.subscribe(
        StaffInvitationIssued,
        SendInvitationEmailHandler(
            emails=_build_email_gateway(),
            organizations=DjangoOrganizationRepository(),
        ),
    )
    return dispatcher


def build_provision_owner_handler() -> ProvisionOwnerHandler:
    """Assemble the bootstrap-owner use case with its adapters."""
    return ProvisionOwnerHandler(
        organizations=DjangoOrganizationRepository(),
        memberships=DjangoStaffMembershipRepository(),
        clock=SystemClock(),
        uuids=Uuid7Generator(),
        events=_build_event_dispatcher(),
    )


def build_invite_staff_handler() -> InviteStaffHandler:
    """Assemble the invitation-issuance use case with its adapters."""
    return InviteStaffHandler(
        organizations=DjangoOrganizationRepository(),
        memberships=DjangoStaffMembershipRepository(),
        invitations=DjangoStaffInvitationRepository(),
        clock=SystemClock(),
        uuids=Uuid7Generator(),
        hasher=Sha256InvitationTokenHasher(),
        token_service=_build_invitation_token_service(),
        events=_build_event_dispatcher(),
    )


def build_accept_staff_invitation_handler() -> AcceptStaffInvitationHandler:
    """Assemble the invitation-acceptance use case with its adapters."""
    return AcceptStaffInvitationHandler(
        organizations=DjangoOrganizationRepository(),
        memberships=DjangoStaffMembershipRepository(),
        invitations=DjangoStaffInvitationRepository(),
        clock=SystemClock(),
        uuids=Uuid7Generator(),
        hasher=Sha256InvitationTokenHasher(),
        events=_build_event_dispatcher(),
    )


class DjangoStaffInvitationEmailGateway:
    def __init__(self, *, from_email: str | None = None) -> None:
        self._from_email = from_email if from_email is not None else settings.DEFAULT_FROM_EMAIL

    def send_staff_invitation(
        self,
        *,
        recipient_email: StaffEmail,
        organization_name: OrganizationName,
        role: StaffRole,
        expires_at: datetime,
        token: str,
    ) -> None:
        subject = "Приглашение в команду Взлёт талантов"
        body = (
            f"Вас пригласили в команду {organization_name.value} c ролью {role.value}.\n\n"  # noqa: RUF001
            f"Ссылка для принятия приглашения: {token}\n\n"
            f"Ссылка действительна до {expires_at.isoformat()}."
        )
        EmailMessage(
            subject=subject,
            body=body,
            from_email=self._from_email,
            to=[recipient_email.value],
        ).send(fail_silently=False)


def _build_email_gateway() -> EmailGateway:
    return DjangoStaffInvitationEmailGateway()


def _build_invitation_token_service() -> InvitationTokenService:
    from apps.organization.infrastructure.messaging import (
        InvitationTokenService as ConcreteInvitationTokenService,
    )

    return ConcreteInvitationTokenService()


def build_get_staff_invitation_handler() -> GetStaffInvitationHandler:
    """Assemble the invitation-lookup use case with its adapters."""
    return GetStaffInvitationHandler(
        invitations=DjangoStaffInvitationRepository(),
        organizations=DjangoOrganizationRepository(),
        hasher=Sha256InvitationTokenHasher(),
        clock=SystemClock(),
    )


def build_get_organization_profile_handler() -> GetOrganizationProfileHandler:
    """Assemble the organization profile read use case."""
    return GetOrganizationProfileHandler(organizations=DjangoOrganizationRepository())


def build_staff_membership_read_service() -> StaffMembershipReader:
    """Assemble the published cross-context staff-membership read model."""
    return StaffMembershipReader(
        organizations=DjangoOrganizationRepository(),
        memberships=DjangoStaffMembershipRepository(),
    )


def build_organization_directory() -> DjangoOrganizationDirectory:
    """Assemble the published cross-context organizer directory read model."""
    return DjangoOrganizationDirectory()
