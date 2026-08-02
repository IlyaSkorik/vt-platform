"""Tests for the Organization application use cases (handlers & read model)."""

from __future__ import annotations

import pytest

from apps.organization.application.dto.commands import (
    AcceptStaffInvitationCommand,
    InviteStaffCommand,
    ProvisionOwnerCommand,
    UpdateOrganizationProfileCommand,
)
from apps.organization.application.dto.queries import (
    GetOrganizationProfileQuery,
    GetStaffInvitationQuery,
)
from apps.organization.application.exceptions import (
    InvalidInputError,
    InvalidInvitationTokenError,
    InvitationConflictError,
    InvitationStateConflictError,
    OrganizationNotFoundError,
    OrganizationStateConflictError,
    PermissionDeniedError,
    StaffInvitationNotFoundError,
    UserAlreadyStaffError,
)
from apps.organization.application.handlers import (
    AcceptStaffInvitationHandler,
    GetOrganizationProfileHandler,
    GetStaffInvitationHandler,
    InviteStaffHandler,
    ProvisionOwnerHandler,
    SendInvitationEmailHandler,
    UpdateOrganizationProfileHandler,
)
from apps.organization.application.read_models import StaffMembershipReader
from apps.organization.domain.entities import Organization, StaffMembership
from apps.organization.domain.events import OrganizationProfileUpdated, StaffInvitationIssued
from apps.organization.domain.policies import InvitationExpiryPolicy
from apps.organization.domain.value_objects import (
    OrganizationId,
    OrganizationName,
    OrganizationSlug,
    StaffEmail,
    StaffInvitationId,
    StaffMembershipId,
    StaffRole,
    StaffUserId,
)

from .fakes import (
    NOW,
    FakeClock,
    FakeOrganizationRepository,
    FakeStaffInvitationRepository,
    FakeStaffMembershipRepository,
    FakeTokenHasher,
    RecordingEmailGateway,
    RecordingEventPublisher,
    SequenceUuidGenerator,
    a_staff_invitation,
)


class TestGetStaffInvitationHandler:
    def _handler(
        self,
        orgs: FakeOrganizationRepository,
        invitations: FakeStaffInvitationRepository,
        clock: FakeClock,
        hasher: FakeTokenHasher,
    ) -> GetStaffInvitationHandler:
        return GetStaffInvitationHandler(
            invitations=invitations,
            organizations=orgs,
            hasher=hasher,
            clock=clock,
        )

    def test_lookup_valid_invitation(self) -> None:
        orgs = FakeOrganizationRepository()
        invitations = FakeStaffInvitationRepository()
        clock = FakeClock()
        hasher = FakeTokenHasher()
        organization = _seeded_org(orgs)

        # Create an invitation
        invited_email = StaffEmail("test@example.com")
        raw_token = hasher.generate().raw_token
        invitation = a_staff_invitation(
            organization_id=organization.id,
            email=invited_email,
            raw_token=raw_token,
            expires_at=clock.utcnow().replace(year=clock.utcnow().year + 1),
        )
        invitations.save(invitation)

        # Perform lookup
        query = GetStaffInvitationQuery(raw_token=raw_token)
        result = self._handler(orgs, invitations, clock, hasher).handle(query)

        assert result.organization_name == organization.name.value
        assert result.role == invitation.role.value
        assert result.expires_at == invitation.expires_at
        assert result.invited_email == invited_email.value

    def test_lookup_unknown_invitation_raises_404(self) -> None:
        orgs = FakeOrganizationRepository()
        invitations = FakeStaffInvitationRepository()
        clock = FakeClock()
        hasher = FakeTokenHasher()
        _seeded_org(orgs)

        query = GetStaffInvitationQuery(raw_token="unknown-token")
        with pytest.raises(StaffInvitationNotFoundError):
            self._handler(orgs, invitations, clock, hasher).handle(query)

    def test_lookup_accepted_invitation_raises_409(self) -> None:
        orgs = FakeOrganizationRepository()
        invitations = FakeStaffInvitationRepository()
        clock = FakeClock()
        hasher = FakeTokenHasher()
        _seeded_org(orgs)

        # Create and accept an invitation
        invited_email = StaffEmail("test@example.com")
        raw_token = hasher.generate().raw_token
        invitation = a_staff_invitation(
            email=invited_email,
            raw_token=raw_token,
            expires_at=clock.utcnow().replace(year=clock.utcnow().year + 1),
        )
        invitations.save(invitation)

        # Simulate acceptance
        invitation.accept(
            accepted_by=_new_user_uuid(),
            policy=InvitationExpiryPolicy(),
            now=clock.utcnow(),
        )
        invitations.save(invitation)

        query = GetStaffInvitationQuery(raw_token=raw_token)
        with pytest.raises(InvitationConflictError):
            self._handler(orgs, invitations, clock, hasher).handle(query)

    def test_lookup_expired_invitation_raises_410(self) -> None:
        orgs = FakeOrganizationRepository()
        invitations = FakeStaffInvitationRepository()
        clock = FakeClock()
        hasher = FakeTokenHasher()
        _seeded_org(orgs)

        # Create an invitation that is already expired
        invited_email = StaffEmail("test@example.com")
        raw_token = hasher.generate().raw_token
        invitation = a_staff_invitation(
            email=invited_email,
            raw_token=raw_token,
            expires_at=clock.utcnow().replace(year=clock.utcnow().year - 1),
        )
        invitations.save(invitation)

        query = GetStaffInvitationQuery(raw_token=raw_token)
        with pytest.raises(InvalidInvitationTokenError):  # This maps to 410
            self._handler(orgs, invitations, clock, hasher).handle(query)


def _seeded_org(repo: FakeOrganizationRepository) -> Organization:
    org, _ = Organization.seed(
        organization_id=OrganizationId.generate(),
        name=OrganizationName("Взлёт талантов"),
        slug=OrganizationSlug("vzlyot-talantov"),
        now=NOW,
    )
    return repo.seed(org)


def _owner_of(
    orgs: FakeOrganizationRepository,
    members: FakeStaffMembershipRepository,
    organization: Organization,
) -> StaffUserId:
    """Make a fresh account the organization's owner and return its id."""
    user_id = _new_user_uuid()
    membership, _ = StaffMembership.activate_for_owner(
        membership_id=StaffMembershipId.generate(),
        organization_id=organization.id,
        user_id=user_id,
        now=NOW,
    )
    members.save(membership)
    return user_id


def _new_user_uuid() -> StaffUserId:
    return StaffUserId.from_uuid(SequenceUuidGenerator().new())


class RecordingTokenService:
    def build_accept_url(self, *, raw_token: str) -> str:
        return f"https://example.test/invite?token={raw_token}"


class TestProvisionOwnerHandler:
    def _handler(
        self,
        orgs: FakeOrganizationRepository,
        members: FakeStaffMembershipRepository,
        events: RecordingEventPublisher,
    ) -> ProvisionOwnerHandler:
        return ProvisionOwnerHandler(
            organizations=orgs,
            memberships=members,
            clock=FakeClock(),
            uuids=SequenceUuidGenerator(),
            events=events,
        )

    def test_provisions_active_owner(self) -> None:
        orgs = FakeOrganizationRepository()
        members = FakeStaffMembershipRepository()
        events = RecordingEventPublisher()
        _seeded_org(orgs)
        user_id = _new_user_uuid()

        result = self._handler(orgs, members, events).handle(ProvisionOwnerCommand(user_id=user_id.json()))

        assert result.membership.role == StaffRole.OWNER.value
        assert result.membership.status == "ACTIVE"
        assert len(members.saved) == 1
        assert members.saved[0].has_role(StaffRole.OWNER)
        assert len(events.published) == 1

    def test_rejects_when_org_not_seeded(self) -> None:
        with pytest.raises(OrganizationNotFoundError):
            self._handler(
                FakeOrganizationRepository(),
                FakeStaffMembershipRepository(),
                RecordingEventPublisher(),
            ).handle(ProvisionOwnerCommand(user_id=_new_user_uuid().json()))

    def test_rejects_malformed_user_id(self) -> None:
        orgs = FakeOrganizationRepository()
        _seeded_org(orgs)
        with pytest.raises(InvalidInputError):
            self._handler(orgs, FakeStaffMembershipRepository(), RecordingEventPublisher()).handle(ProvisionOwnerCommand(user_id="not-a-uuid"))

    def test_rejects_duplicate_active_owner(self) -> None:
        orgs = FakeOrganizationRepository()
        members = FakeStaffMembershipRepository()
        events = RecordingEventPublisher()
        _seeded_org(orgs)
        user_id = _new_user_uuid()
        handler = self._handler(orgs, members, events)
        handler.handle(ProvisionOwnerCommand(user_id=user_id.json()))
        with pytest.raises(UserAlreadyStaffError):
            handler.handle(ProvisionOwnerCommand(user_id=user_id.json()))


class TestInviteStaffHandler:
    def _handler(
        self,
        orgs: FakeOrganizationRepository,
        members: FakeStaffMembershipRepository,
        invitations: FakeStaffInvitationRepository,
        events: RecordingEventPublisher,
    ) -> InviteStaffHandler:
        return InviteStaffHandler(
            organizations=orgs,
            memberships=members,
            invitations=invitations,
            clock=FakeClock(),
            uuids=SequenceUuidGenerator(),
            hasher=FakeTokenHasher(),
            token_service=RecordingTokenService(),
            events=events,
        )

    def test_creates_invitation_for_owner(self) -> None:
        orgs = FakeOrganizationRepository()
        members = FakeStaffMembershipRepository()
        invitations = FakeStaffInvitationRepository()
        events = RecordingEventPublisher()
        _seeded_org(orgs)
        owner_id = _new_user_uuid()
        ProvisionOwnerHandler(
            organizations=orgs,
            memberships=members,
            clock=FakeClock(),
            uuids=SequenceUuidGenerator(),
            events=events,
        ).handle(ProvisionOwnerCommand(user_id=owner_id.json()))

        result = self._handler(orgs, members, invitations, events).handle(
            InviteStaffCommand(
                email="new.staff@example.com",
                role=StaffRole.DIRECTOR.value,
                invited_by=owner_id.json(),
            )
        )

        assert result.invitation.email == "new.staff@example.com"
        assert result.invitation.role == StaffRole.DIRECTOR.value
        assert len(invitations.saved) == 1
        assert len(events.published) == 2  # owner provisioned, invitation issued

    def test_rejects_non_owner_inviter(self) -> None:
        orgs = FakeOrganizationRepository()
        members = FakeStaffMembershipRepository()
        invitations = FakeStaffInvitationRepository()
        events = RecordingEventPublisher()
        _seeded_org(orgs)

        with pytest.raises(PermissionDeniedError):
            self._handler(orgs, members, invitations, events).handle(
                InviteStaffCommand(
                    email="new.staff@example.com",
                    role=StaffRole.DIRECTOR.value,
                    invited_by=_new_user_uuid().json(),
                )
            )


class TestAcceptStaffInvitationHandler:
    def _handler(
        self,
        orgs: FakeOrganizationRepository,
        members: FakeStaffMembershipRepository,
        invitations: FakeStaffInvitationRepository,
        events: RecordingEventPublisher,
    ) -> AcceptStaffInvitationHandler:
        return AcceptStaffInvitationHandler(
            organizations=orgs,
            memberships=members,
            invitations=invitations,
            clock=FakeClock(),
            uuids=SequenceUuidGenerator(),
            hasher=FakeTokenHasher(),
            events=events,
        )

    def test_accepts_valid_invitation_and_creates_membership(self) -> None:
        orgs = FakeOrganizationRepository()
        members = FakeStaffMembershipRepository()
        invitations = FakeStaffInvitationRepository()
        events = RecordingEventPublisher()
        _seeded_org(orgs)
        owner_id = _new_user_uuid()
        ProvisionOwnerHandler(
            organizations=orgs,
            memberships=members,
            clock=FakeClock(),
            uuids=SequenceUuidGenerator(),
            events=events,
        ).handle(ProvisionOwnerCommand(user_id=owner_id.json()))

        invite_handler = InviteStaffHandler(
            organizations=orgs,
            memberships=members,
            invitations=invitations,
            clock=FakeClock(),
            uuids=SequenceUuidGenerator(),
            hasher=FakeTokenHasher(),
            token_service=RecordingTokenService(),
            events=events,
        )
        invite_result = invite_handler.handle(
            InviteStaffCommand(
                email="new.staff@example.com",
                role=StaffRole.DIRECTOR.value,
                invited_by=owner_id.json(),
            )
        )

        accept_result = self._handler(orgs, members, invitations, events).handle(
            AcceptStaffInvitationCommand(
                raw_token=invite_result.raw_token,
                accepted_by=_new_user_uuid().json(),
                email="new.staff@example.com",
            )
        )

        assert accept_result.membership.role == StaffRole.DIRECTOR.value
        assert accept_result.membership.status == "ACTIVE"
        assert len(members.saved) == 2

        # Add assertion for invitation closed
        saved_invitation = invitations.get(StaffInvitationId.from_string(invite_result.invitation.id))
        assert saved_invitation is not None
        assert saved_invitation.is_pending() is False

    def test_rejects_accept_twice(self) -> None:
        orgs = FakeOrganizationRepository()
        members = FakeStaffMembershipRepository()
        invitations = FakeStaffInvitationRepository()
        events = RecordingEventPublisher()
        _seeded_org(orgs)
        owner_id = _new_user_uuid()
        ProvisionOwnerHandler(
            organizations=orgs,
            memberships=members,
            clock=FakeClock(),
            uuids=SequenceUuidGenerator(),
            events=events,
        ).handle(ProvisionOwnerCommand(user_id=owner_id.json()))

        invite_handler = InviteStaffHandler(
            organizations=orgs,
            memberships=members,
            invitations=invitations,
            clock=FakeClock(),
            uuids=SequenceUuidGenerator(),
            hasher=FakeTokenHasher(),
            token_service=RecordingTokenService(),
            events=events,
        )
        invite_result = invite_handler.handle(
            InviteStaffCommand(
                email="new.staff@example.com",
                role=StaffRole.DIRECTOR.value,
                invited_by=owner_id.json(),
            )
        )

        accept_command = AcceptStaffInvitationCommand(
            raw_token=invite_result.raw_token,
            accepted_by=_new_user_uuid().json(),
            email="new.staff@example.com",
        )
        self._handler(orgs, members, invitations, events).handle(accept_command)

        with pytest.raises(UserAlreadyStaffError):
            self._handler(orgs, members, invitations, events).handle(accept_command)

    def test_rejects_accept_expired(self) -> None:
        orgs = FakeOrganizationRepository()
        members = FakeStaffMembershipRepository()
        invitations = FakeStaffInvitationRepository()
        events = RecordingEventPublisher()
        clock = FakeClock()
        hasher = FakeTokenHasher()
        _seeded_org(orgs)
        owner_id = _new_user_uuid()
        ProvisionOwnerHandler(
            organizations=orgs,
            memberships=members,
            clock=clock,
            uuids=SequenceUuidGenerator(),
            events=events,
        ).handle(ProvisionOwnerCommand(user_id=owner_id.json()))

        # Create an invitation that is already expired
        invited_email = StaffEmail("expired@example.com")
        raw_token = hasher.generate().raw_token
        expired_invitation = a_staff_invitation(
            email=invited_email,
            raw_token=raw_token,
            expires_at=clock.utcnow().replace(year=clock.utcnow().year - 1),
            now=clock.utcnow(),
        )
        invitations.save(expired_invitation)

        with pytest.raises(InvitationStateConflictError):  # This maps to 409 conflict
            self._handler(orgs, members, invitations, events).handle(
                AcceptStaffInvitationCommand(
                    raw_token=raw_token,
                    accepted_by=_new_user_uuid().json(),
                    email=invited_email.value,
                )
            )

    def test_rejects_mismatched_invitee_email(self) -> None:
        orgs = FakeOrganizationRepository()
        members = FakeStaffMembershipRepository()
        invitations = FakeStaffInvitationRepository()
        events = RecordingEventPublisher()
        _seeded_org(orgs)
        owner_id = _new_user_uuid()
        ProvisionOwnerHandler(
            organizations=orgs,
            memberships=members,
            clock=FakeClock(),
            uuids=SequenceUuidGenerator(),
            events=events,
        ).handle(ProvisionOwnerCommand(user_id=owner_id.json()))

        invite_handler = InviteStaffHandler(
            organizations=orgs,
            memberships=members,
            invitations=invitations,
            clock=FakeClock(),
            uuids=SequenceUuidGenerator(),
            hasher=FakeTokenHasher(),
            token_service=RecordingTokenService(),
            events=events,
        )
        invite_result = invite_handler.handle(
            InviteStaffCommand(
                email="new.staff@example.com",
                role=StaffRole.DIRECTOR.value,
                invited_by=owner_id.json(),
            )
        )

        with pytest.raises(PermissionDeniedError):
            self._handler(orgs, members, invitations, events).handle(
                AcceptStaffInvitationCommand(
                    raw_token=invite_result.raw_token,
                    accepted_by=_new_user_uuid().json(),
                    email="other@example.com",
                )
            )

    def test_rejects_unknown_token(self) -> None:
        with pytest.raises(InvalidInvitationTokenError):
            self._handler(
                FakeOrganizationRepository(),
                FakeStaffMembershipRepository(),
                FakeStaffInvitationRepository(),
                RecordingEventPublisher(),
            ).handle(
                AcceptStaffInvitationCommand(
                    raw_token="missing-token",
                    accepted_by=_new_user_uuid().json(),
                    email="someone@example.com",
                )
            )


class TestStaffMembershipReader:
    def test_returns_none_when_not_staff(self) -> None:
        orgs = FakeOrganizationRepository()
        members = FakeStaffMembershipRepository()
        _seeded_org(orgs)
        reader = StaffMembershipReader(organizations=orgs, memberships=members)
        assert reader.active_for_user(OrganizationId.generate().value) is None

    def test_returns_none_when_org_unseeded(self) -> None:
        reader = StaffMembershipReader(
            organizations=FakeOrganizationRepository(),
            memberships=FakeStaffMembershipRepository(),
        )
        assert reader.active_for_user(OrganizationId.generate().value) is None

    def test_returns_view_for_active_staff(self) -> None:
        orgs = FakeOrganizationRepository()
        members = FakeStaffMembershipRepository()
        events = RecordingEventPublisher()
        _seeded_org(orgs)
        user_id = _new_user_uuid()
        ProvisionOwnerHandler(
            organizations=orgs,
            memberships=members,
            clock=FakeClock(),
            uuids=SequenceUuidGenerator(),
            events=events,
        ).handle(ProvisionOwnerCommand(user_id=user_id.json()))

        reader = StaffMembershipReader(organizations=orgs, memberships=members)

        view = reader.active_for_user(user_id.value)
        assert view is not None
        assert view.role == "OWNER"
        assert view.status == "ACTIVE"


class TestSendInvitationEmailHandler:
    def test_sends_email_on_staff_invitation_issued_event(self) -> None:
        orgs = FakeOrganizationRepository()
        email_gateway = RecordingEmailGateway()
        _seeded_org(orgs)
        organization = orgs.get_default()
        assert organization is not None

        handler = SendInvitationEmailHandler(
            emails=email_gateway,
            organizations=orgs,
            token_service=RecordingTokenService(),
        )

        event = StaffInvitationIssued(
            aggregate_id=OrganizationId.generate().value,
            organization_id=organization.id,
            email=StaffEmail("test@example.com"),
            role=StaffRole.SUPPORT,
            invited_by=_new_user_uuid(),
            expires_at=NOW,
            raw_token="some-raw-token",
        )
        handler(event)

        assert len(email_gateway.sent) == 1
        sent_email, sent_org_name, sent_role, sent_expires_at, sent_token = email_gateway.sent[0]
        assert sent_email == StaffEmail("test@example.com")
        assert sent_org_name == organization.name
        assert sent_role == StaffRole.SUPPORT
        assert sent_expires_at == NOW
        # The email carries the full acceptance link, not the bare token secret.
        assert sent_token == "https://example.test/invite?token=some-raw-token"

    def test_raises_error_if_organization_not_found(self) -> None:
        orgs = FakeOrganizationRepository()
        email_gateway = RecordingEmailGateway()

        handler = SendInvitationEmailHandler(
            emails=email_gateway,
            organizations=orgs,
            token_service=RecordingTokenService(),
        )

        event = StaffInvitationIssued(
            aggregate_id=OrganizationId.generate().value,
            organization_id=OrganizationId.generate(),  # A non-existent organization
            email=StaffEmail("test@example.com"),
            role=StaffRole.SUPPORT,
            invited_by=_new_user_uuid(),
            expires_at=NOW,
            raw_token="some-raw-token",
        )
        with pytest.raises(OrganizationNotFoundError):
            handler(event)


class TestGetOrganizationProfileHandler:
    def test_returns_the_callers_own_organization(self) -> None:
        orgs = FakeOrganizationRepository()
        members = FakeStaffMembershipRepository()
        org = _seeded_org(orgs)
        owner = _owner_of(orgs, members, org)

        view = GetOrganizationProfileHandler(organizations=orgs, memberships=members).handle(GetOrganizationProfileQuery(requested_by=owner.json()))

        assert view.id == org.id.json()
        assert view.name == "Взлёт талантов"
        assert view.slug == "vzlyot-talantov"
        assert view.phone is None
        assert view.legal_information is None

    def test_rejects_a_caller_who_is_staff_of_no_organization(self) -> None:
        # Never "the first organization on the platform": with several connected,
        # a caller who is staff nowhere must read nothing.
        with pytest.raises(PermissionDeniedError):
            GetOrganizationProfileHandler(organizations=FakeOrganizationRepository(), memberships=FakeStaffMembershipRepository()).handle(
                GetOrganizationProfileQuery(requested_by=_new_user_uuid().json())
            )


class TestUpdateOrganizationProfileHandler:
    def _handler(
        self,
        orgs: FakeOrganizationRepository,
        events: RecordingEventPublisher,
        members: FakeStaffMembershipRepository | None = None,
    ) -> UpdateOrganizationProfileHandler:
        return UpdateOrganizationProfileHandler(
            organizations=orgs,
            memberships=members if members is not None else FakeStaffMembershipRepository(),
            clock=FakeClock(),
            events=events,
        )

    def test_persists_and_returns_updated_profile(self) -> None:
        orgs = FakeOrganizationRepository()
        events = RecordingEventPublisher()
        members = FakeStaffMembershipRepository()
        owner = _owner_of(orgs, members, _seeded_org(orgs))

        view = self._handler(orgs, events, members).handle(
            UpdateOrganizationProfileCommand(
                updated_by=owner.json(),
                phone="+375 29 000-00-00",
                email="hello@vzlet.ru",
                website="https://vzlet.ru",
                legal_information="ООО «Взлёт», ИНН 000",
            )
        )

        assert view.phone == "+375 29 000-00-00"
        assert view.email == "hello@vzlet.ru"
        assert view.website == "https://vzlet.ru"
        assert view.legal_information == "ООО «Взлёт», ИНН 000"
        assert len(orgs.saved) == 1
        assert orgs.saved[0].profile.phone == "+375 29 000-00-00"
        assert any(isinstance(event, OrganizationProfileUpdated) for event in events.published)

    def test_renames_organization(self) -> None:
        orgs = FakeOrganizationRepository()
        events = RecordingEventPublisher()
        members = FakeStaffMembershipRepository()
        owner = _owner_of(orgs, members, _seeded_org(orgs))

        view = self._handler(orgs, events, members).handle(UpdateOrganizationProfileCommand(updated_by=owner.json(), name="Новое имя"))

        assert view.name == "Новое имя"
        assert view.slug == "vzlyot-talantov"  # slug stays fixed
        assert orgs.saved[0].name.value == "Новое имя"

    def test_rejects_blank_name(self) -> None:
        orgs = FakeOrganizationRepository()
        members = FakeStaffMembershipRepository()
        owner = _owner_of(orgs, members, _seeded_org(orgs))

        with pytest.raises(InvalidInputError):
            self._handler(orgs, RecordingEventPublisher(), members).handle(UpdateOrganizationProfileCommand(updated_by=owner.json(), name="   "))

    def test_blank_fields_are_normalized_to_none(self) -> None:
        orgs = FakeOrganizationRepository()
        events = RecordingEventPublisher()
        members = FakeStaffMembershipRepository()
        owner = _owner_of(orgs, members, _seeded_org(orgs))

        view = self._handler(orgs, events, members).handle(UpdateOrganizationProfileCommand(updated_by=owner.json(), phone="   ", email=None))

        assert view.phone is None
        assert view.email is None

    def test_unchanged_profile_is_a_noop_without_event(self) -> None:
        orgs = FakeOrganizationRepository()
        events = RecordingEventPublisher()
        members = FakeStaffMembershipRepository()
        owner = _owner_of(orgs, members, _seeded_org(orgs))

        # Seeded organization already has an empty profile; submitting an empty one changes nothing.
        self._handler(orgs, events, members).handle(UpdateOrganizationProfileCommand(updated_by=owner.json()))

        assert events.published == []

    def test_rejects_a_caller_who_is_staff_of_no_organization(self) -> None:
        with pytest.raises(PermissionDeniedError):
            self._handler(FakeOrganizationRepository(), RecordingEventPublisher()).handle(
                UpdateOrganizationProfileCommand(updated_by=_new_user_uuid().json(), phone="123")
            )

    def test_rejects_overlong_field(self) -> None:
        orgs = FakeOrganizationRepository()
        members = FakeStaffMembershipRepository()
        owner = _owner_of(orgs, members, _seeded_org(orgs))

        with pytest.raises(InvalidInputError):
            self._handler(orgs, RecordingEventPublisher(), members).handle(UpdateOrganizationProfileCommand(updated_by=owner.json(), phone="x" * 201))

    def test_rejects_update_on_suspended_organization(self) -> None:
        orgs = FakeOrganizationRepository()
        members = FakeStaffMembershipRepository()
        org = _seeded_org(orgs)
        owner = _owner_of(orgs, members, org)
        org.suspend(now=NOW)

        with pytest.raises(OrganizationStateConflictError):
            self._handler(orgs, RecordingEventPublisher(), members).handle(UpdateOrganizationProfileCommand(updated_by=owner.json(), phone="123"))
