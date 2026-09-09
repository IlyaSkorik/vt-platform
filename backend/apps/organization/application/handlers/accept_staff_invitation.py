from __future__ import annotations

from apps.organization.application.dto import (
    MembershipOperationResultDto,
    StaffMembershipView,
)
from apps.organization.application.dto.commands import AcceptStaffInvitationCommand
from apps.organization.application.exceptions import (
    InvalidInvitationTokenError,
    OrganizationNotFoundError,
    PermissionDeniedError,
    UserAlreadyStaffError,
    translate_domain_errors,
)
from apps.organization.application.interfaces import (
    Clock,
    EventPublisher,
    OrganizationRepository,
    StaffInvitationRepository,
    StaffMembershipRepository,
    TokenHasher,
    UuidGenerator,
)
from apps.organization.domain.entities import StaffMembership
from apps.organization.domain.policies import InvitationExpiryPolicy
from apps.organization.domain.value_objects import (
    StaffEmail,
    StaffMembershipId,
    StaffUserId,
)

__all__ = ["AcceptStaffInvitationHandler"]


class AcceptStaffInvitationHandler:
    """Use case: accept a staff invitation and create the staff membership."""

    def __init__(
        self,
        *,
        organizations: OrganizationRepository,
        memberships: StaffMembershipRepository,
        invitations: StaffInvitationRepository,
        clock: Clock,
        uuids: UuidGenerator,
        hasher: TokenHasher,
        events: EventPublisher,
    ) -> None:
        self._organizations = organizations
        self._memberships = memberships
        self._invitations = invitations
        self._clock = clock
        self._uuids = uuids
        self._hasher = hasher
        self._events = events

    def handle(self, command: AcceptStaffInvitationCommand) -> MembershipOperationResultDto:
        now = self._clock.utcnow()

        with translate_domain_errors():
            accepted_by = StaffUserId.from_string(command.accepted_by)
            email = StaffEmail(command.email)

        token_hash = self._hasher.hash(command.raw_token)
        invitation = self._invitations.get_by_token_hash(token_hash)
        if invitation is None:
            raise InvalidInvitationTokenError("Ссылка приглашения недействительна или устарела.")

        # The seat is in the organization that issued the invitation. Reading the
        # default organization here instead put everyone who ever accepted one into
        # the platform's first organization — whatever the letter said, and whatever
        # the invitation preview showed them.
        organization = self._organizations.get(invitation.organization_id)
        if organization is None:
            raise OrganizationNotFoundError("Организация, приславшая приглашение, больше не существует.")

        if invitation.email != email:
            raise PermissionDeniedError("Это приглашение выписано на другую почту.")

        # A person is staff of one organization at a time — that is the assumption the
        # whole scoping layer rests on (`find_active_for_user` answers "which one" with
        # a single row). A second seat elsewhere would not be refused by the database,
        # it would just make the earlier one win silently, so it is refused here.
        existing = self._memberships.find_active_for_user(accepted_by)
        if existing is not None:
            if existing.organization_id == organization.id:
                raise UserAlreadyStaffError("Этот пользователь уже состоит в организации.")
            raise UserAlreadyStaffError(
                "Этот аккаунт уже состоит в другой организации. Выйдите из неё (владелец может отозвать доступ) "
                "или примите приглашение другим аккаунтом."
            )

        with translate_domain_errors():
            invitation_events = invitation.accept(
                accepted_by=accepted_by,
                policy=InvitationExpiryPolicy(),
                now=now,
            )

        membership_id = StaffMembershipId.from_uuid(self._uuids.new())
        membership = StaffMembership.pending_from_invitation(
            membership_id=membership_id,
            organization_id=organization.id,
            user_id=accepted_by,
            role=invitation.role,
            invited_by=invitation.invited_by,
            invited_at=now,
            now=now,
        )
        membership_events = membership.activate(accepted_by=accepted_by, now=now)

        self._invitations.save(invitation)
        self._memberships.save(membership)
        self._events.publish(tuple(invitation_events + membership_events))
        return MembershipOperationResultDto(
            membership=StaffMembershipView.from_membership(membership),
            events=tuple(invitation_events + membership_events),
        )
