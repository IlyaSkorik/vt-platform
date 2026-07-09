"""Tests for the Organization application use cases (handlers & read model)."""

from __future__ import annotations

import pytest

from apps.organization.application.dto.commands import ProvisionOwnerCommand
from apps.organization.application.exceptions import (
    InvalidInputError,
    OrganizationNotFoundError,
    UserAlreadyStaffError,
)
from apps.organization.application.handlers import ProvisionOwnerHandler
from apps.organization.application.read_models import StaffMembershipReader
from apps.organization.domain.entities import Organization
from apps.organization.domain.value_objects import (
    OrganizationId,
    OrganizationName,
    OrganizationSlug,
    StaffRole,
)

from .fakes import (
    NOW,
    FakeClock,
    FakeOrganizationRepository,
    FakeStaffMembershipRepository,
    RecordingEventPublisher,
    SequenceUuidGenerator,
)


def _seeded_org(repo: FakeOrganizationRepository) -> Organization:
    org, _ = Organization.seed(
        organization_id=OrganizationId.generate(),
        name=OrganizationName("Взлёт талантов"),
        slug=OrganizationSlug("vzlyot-talantov"),
        now=NOW,
    )
    return repo.seed(org)


def _new_user_uuid() -> str:
    return OrganizationId.generate().json()


class TestProvisionOwnerHandler:
    def _handler(self, orgs, members, events):
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

        result = self._handler(orgs, members, events).handle(
            ProvisionOwnerCommand(user_id=user_id)
        )

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
            ).handle(ProvisionOwnerCommand(user_id=_new_user_uuid()))

    def test_rejects_malformed_user_id(self) -> None:
        orgs = FakeOrganizationRepository()
        _seeded_org(orgs)
        with pytest.raises(InvalidInputError):
            self._handler(
                orgs, FakeStaffMembershipRepository(), RecordingEventPublisher()
            ).handle(ProvisionOwnerCommand(user_id="not-a-uuid"))

    def test_rejects_duplicate_active_owner(self) -> None:
        orgs = FakeOrganizationRepository()
        members = FakeStaffMembershipRepository()
        events = RecordingEventPublisher()
        _seeded_org(orgs)
        user_id = _new_user_uuid()
        handler = self._handler(orgs, members, events)
        handler.handle(ProvisionOwnerCommand(user_id=user_id))
        with pytest.raises(UserAlreadyStaffError):
            handler.handle(ProvisionOwnerCommand(user_id=user_id))


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
        ).handle(ProvisionOwnerCommand(user_id=user_id))

        reader = StaffMembershipReader(organizations=orgs, memberships=members)
        import uuid

        view = reader.active_for_user(uuid.UUID(user_id))
        assert view is not None
        assert view.role == "OWNER"
        assert view.status == "ACTIVE"
