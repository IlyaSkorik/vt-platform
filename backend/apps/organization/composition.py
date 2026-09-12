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
from typing import Final
from zoneinfo import ZoneInfo

from django.conf import settings
from django.core.mail import EmailMultiAlternatives

from apps.emailing import render_transactional_email_html
from apps.identity.composition import build_user_directory
from apps.notifications.infrastructure.email import send_priority
from apps.organization.application.handlers import (
    AcceptStaffInvitationHandler,
    ChangeOrganizationStatusHandler,
    ChangeStaffRoleHandler,
    ConnectOrganizationHandler,
    GetOrganizationProfileHandler,
    GetStaffInvitationHandler,
    InviteStaffHandler,
    ListOrganizationModulesHandler,
    ListOrganizationsHandler,
    ListStaffInvitationsHandler,
    ListStaffMembersHandler,
    ProvisionOwnerHandler,
    RevokeStaffInvitationHandler,
    RevokeStaffMembershipHandler,
    SendInvitationEmailHandler,
    SetCommissionRateHandler,
    SetOrganizationModulesHandler,
    SetPerformanceFeeScheduleHandler,
    UpdateOrganizationProfileHandler,
)
from apps.organization.application.interfaces import EmailGateway, InvitationTokenService
from apps.organization.application.read_models import EnabledModulesReader, StaffMembershipReader
from apps.organization.domain.events import StaffInvitationIssued
from apps.organization.domain.value_objects import OrganizationName, StaffEmail, StaffRole
from apps.organization.infrastructure.cache import DjangoModuleCache
from apps.organization.infrastructure.messaging import (
    EventDispatcher,
    Sha256InvitationTokenHasher,
)
from apps.organization.infrastructure.read_models import DjangoOrganizationDirectory
from apps.organization.infrastructure.repositories import (
    DjangoModuleEntitlementRepository,
    DjangoOrganizationRepository,
    DjangoStaffInvitationRepository,
    DjangoStaffMembershipRepository,
)
from apps.organization.infrastructure.system import SystemClock, Uuid7Generator

__all__ = [
    "build_accept_staff_invitation_handler",
    "build_change_organization_status_handler",
    "build_change_staff_role_handler",
    "build_connect_organization_handler",
    "build_enabled_modules_read_service",
    "build_get_organization_profile_handler",
    "build_get_staff_invitation_handler",
    "build_invite_staff_handler",
    "build_list_organization_modules_handler",
    "build_list_organizations_handler",
    "build_list_staff_invitations_handler",
    "build_list_staff_members_handler",
    "build_organization_directory",
    "build_provision_owner_handler",
    "build_revoke_staff_invitation_handler",
    "build_revoke_staff_membership_handler",
    "build_set_commission_rate_handler",
    "build_set_organization_modules_handler",
    "build_set_performance_fee_schedule_handler",
    "build_staff_membership_read_service",
    "build_update_organization_profile_handler",
]


def _build_event_dispatcher() -> EventDispatcher:
    dispatcher = EventDispatcher()
    dispatcher.subscribe(
        StaffInvitationIssued,
        SendInvitationEmailHandler(
            emails=_build_email_gateway(),
            organizations=DjangoOrganizationRepository(),
            token_service=_build_invitation_token_service(),
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


def build_connect_organization_handler() -> ConnectOrganizationHandler:
    """Assemble the platform's connect-an-organization use case with its adapters."""
    return ConnectOrganizationHandler(
        organizations=DjangoOrganizationRepository(),
        invitations=DjangoStaffInvitationRepository(),
        entitlements=DjangoModuleEntitlementRepository(),
        clock=SystemClock(),
        uuids=Uuid7Generator(),
        hasher=Sha256InvitationTokenHasher(),
        events=_build_event_dispatcher(),
    )


def build_set_commission_rate_handler() -> SetCommissionRateHandler:
    """Assemble the commission-rate use case (platform-gated) with its adapters."""
    return SetCommissionRateHandler(
        organizations=DjangoOrganizationRepository(),
        clock=SystemClock(),
        events=_build_event_dispatcher(),
    )


def build_set_performance_fee_schedule_handler() -> SetPerformanceFeeScheduleHandler:
    """Assemble the per-performance fee-schedule use case (platform-gated) with its adapters."""
    return SetPerformanceFeeScheduleHandler(
        organizations=DjangoOrganizationRepository(),
        clock=SystemClock(),
        events=_build_event_dispatcher(),
    )


def build_change_organization_status_handler() -> ChangeOrganizationStatusHandler:
    """Assemble the suspend/reactivate use case (platform-gated) with its adapters."""
    return ChangeOrganizationStatusHandler(
        organizations=DjangoOrganizationRepository(),
        clock=SystemClock(),
        events=_build_event_dispatcher(),
    )


def build_list_organizations_handler() -> ListOrganizationsHandler:
    """Assemble the platform's organization roster read use case."""
    return ListOrganizationsHandler(organizations=DjangoOrganizationRepository())


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


def build_list_staff_invitations_handler() -> ListStaffInvitationsHandler:
    """Assemble the invitation-roster read use case with its adapters."""
    return ListStaffInvitationsHandler(
        organizations=DjangoOrganizationRepository(),
        memberships=DjangoStaffMembershipRepository(),
        invitations=DjangoStaffInvitationRepository(),
        clock=SystemClock(),
    )


def build_revoke_staff_invitation_handler() -> RevokeStaffInvitationHandler:
    """Assemble the invitation-revocation use case with its adapters."""
    return RevokeStaffInvitationHandler(
        organizations=DjangoOrganizationRepository(),
        memberships=DjangoStaffMembershipRepository(),
        invitations=DjangoStaffInvitationRepository(),
        clock=SystemClock(),
        events=_build_event_dispatcher(),
    )


def build_list_staff_members_handler() -> ListStaffMembersHandler:
    """Assemble the staff-roster read use case (joins the Identity directory)."""
    return ListStaffMembersHandler(
        organizations=DjangoOrganizationRepository(),
        memberships=DjangoStaffMembershipRepository(),
        users=build_user_directory(),
    )


def build_change_staff_role_handler() -> ChangeStaffRoleHandler:
    """Assemble the staff-role-change use case with its adapters."""
    return ChangeStaffRoleHandler(
        organizations=DjangoOrganizationRepository(),
        memberships=DjangoStaffMembershipRepository(),
        clock=SystemClock(),
        events=_build_event_dispatcher(),
    )


def build_revoke_staff_membership_handler() -> RevokeStaffMembershipHandler:
    """Assemble the staff-membership-revocation use case with its adapters."""
    return RevokeStaffMembershipHandler(
        organizations=DjangoOrganizationRepository(),
        memberships=DjangoStaffMembershipRepository(),
        clock=SystemClock(),
        events=_build_event_dispatcher(),
    )


_MINSK_TZ = ZoneInfo("Europe/Minsk")
_RU_MONTHS = (
    "января",
    "февраля",
    "марта",
    "апреля",
    "мая",
    "июня",
    "июля",
    "августа",
    "сентября",
    "октября",
    "ноября",
    "декабря",
)


#: How each role is named to the person being invited.
#:
#: The enum's own values are authorization codes; an invitation letter has to say
#: «Менеджер фестивалей», not ``COMPETITION_MANAGER``. The wording matches the panel's
#: own labels (``features/staff-invitations`` → ``ROLE_LABELS``), so an invitee reads
#: the same word in the letter and then in the interface.
_RU_ROLES: Final[dict[StaffRole, str]] = {
    StaffRole.OWNER: "Владелец",
    StaffRole.DIRECTOR: "Директор",
    StaffRole.FINANCE: "Финансы",
    StaffRole.COMPETITION_MANAGER: "Менеджер фестивалей",
    StaffRole.CONTENT_MANAGER: "Контент-менеджер",
    StaffRole.MODERATOR: "Модератор",
    StaffRole.SUPPORT: "Поддержка",
}


def _role_name(role: StaffRole) -> str:
    """The role's Russian name, falling back to the code for a role added later."""
    return _RU_ROLES.get(role, role.value)


def _format_minsk(moment: datetime) -> str:
    """Render an instant as a human-readable Minsk-local date/time (Europe/Minsk)."""
    local = moment.astimezone(_MINSK_TZ)
    return f"{local.day} {_RU_MONTHS[local.month - 1]} {local.year} г. в {local:%H:%M} (Минск)"


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
        expires_text = _format_minsk(expires_at)
        body = (
            f"Вас пригласили в команду {organization_name.value} с ролью «{_role_name(role)}».\n\n"
            f"Ссылка для принятия приглашения: {token}\n\n"
            f"Ссылка действительна до {expires_text}."
        )
        html_body = render_transactional_email_html(
            title=subject,
            intro=f"Вас пригласили в команду {organization_name.value} с ролью «{_role_name(role)}».",
            details_label="Срок действия ссылки",
            details=f"До {expires_text}",
            button_label="Принять приглашение",
            button_url=token,
            status="info",
            status_label="Приглашение",
        )
        message = EmailMultiAlternatives(
            subject=subject,
            body=body,
            from_email=self._from_email,
            to=[recipient_email.value],
        )
        message.attach_alternative(html_body, "text/html")
        send_priority(message)


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
    return GetOrganizationProfileHandler(
        organizations=DjangoOrganizationRepository(),
        memberships=DjangoStaffMembershipRepository(),
    )


def build_update_organization_profile_handler() -> UpdateOrganizationProfileHandler:
    """Assemble the organization profile edit use case with its adapters."""
    return UpdateOrganizationProfileHandler(
        organizations=DjangoOrganizationRepository(),
        memberships=DjangoStaffMembershipRepository(),
        clock=SystemClock(),
        events=_build_event_dispatcher(),
    )


def build_staff_membership_read_service() -> StaffMembershipReader:
    """Assemble the published cross-context staff-membership read model."""
    return StaffMembershipReader(
        organizations=DjangoOrganizationRepository(),
        memberships=DjangoStaffMembershipRepository(),
    )


def build_organization_directory() -> DjangoOrganizationDirectory:
    """Assemble the published cross-context organizer directory read model."""
    return DjangoOrganizationDirectory()


def build_enabled_modules_read_service() -> EnabledModulesReader:
    """Assemble the published cross-context module-entitlement read model.

    Cached: this is consulted on essentially every staff request. The cache is
    invalidated by the use case that writes an entitlement, so the TTL inside the
    reader is a backstop and not the mechanism.
    """
    return EnabledModulesReader(
        entitlements=DjangoModuleEntitlementRepository(),
        cache=DjangoModuleCache(),
    )


def build_list_organization_modules_handler() -> ListOrganizationModulesHandler:
    """Assemble the platform's read of one organization's module switchboard."""
    return ListOrganizationModulesHandler(
        organizations=DjangoOrganizationRepository(),
        entitlements=DjangoModuleEntitlementRepository(),
    )


def build_set_organization_modules_handler() -> SetOrganizationModulesHandler:
    """Assemble the platform's module-switchboard use case with its adapters."""
    return SetOrganizationModulesHandler(
        organizations=DjangoOrganizationRepository(),
        entitlements=DjangoModuleEntitlementRepository(),
        clock=SystemClock(),
        uuids=Uuid7Generator(),
        events=_build_event_dispatcher(),
        cache=DjangoModuleCache(),
    )
