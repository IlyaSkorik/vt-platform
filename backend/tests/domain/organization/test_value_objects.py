"""Unit tests for the Organization domain value objects."""

from __future__ import annotations

import uuid

import pytest

from apps.organization.domain.exceptions import (
    InvalidInvitationTokenHashError,
    InvalidOrganizationNameError,
    InvalidOrganizationProfileError,
    InvalidOrganizationSlugError,
    InvalidStaffEmailError,
    InvalidStaffUserIdError,
)
from apps.organization.domain.value_objects import (
    InvitationTokenHash,
    MembershipStatus,
    OrganizationId,
    OrganizationName,
    OrganizationProfile,
    OrganizationSlug,
    OrganizationStatus,
    StaffEmail,
    StaffRole,
    StaffUserId,
    _generate_uuid7,
)


class TestIds:
    def test_generate_is_uuid_v7(self) -> None:
        assert OrganizationId.generate().value.version == 7

    def test_from_string_roundtrip(self) -> None:
        oid = OrganizationId.generate()
        assert OrganizationId.from_string(oid.json()) == oid

    def test_rejects_non_v7(self) -> None:
        with pytest.raises(InvalidStaffUserIdError):
            StaffUserId.from_uuid(uuid.uuid4())

    def test_rejects_garbage_string(self) -> None:
        with pytest.raises(InvalidStaffUserIdError):
            StaffUserId.from_string("not-a-uuid")


class TestOrganizationName:
    def test_strips_whitespace(self) -> None:
        assert OrganizationName("  Взлёт талантов  ").value == "Взлёт талантов"

    def test_rejects_empty(self) -> None:
        with pytest.raises(InvalidOrganizationNameError):
            OrganizationName("   ")

    def test_rejects_too_long(self) -> None:
        with pytest.raises(InvalidOrganizationNameError):
            OrganizationName("x" * 201)


class TestOrganizationSlug:
    def test_accepts_kebab(self) -> None:
        assert OrganizationSlug("vzlyot-talantov").value == "vzlyot-talantov"

    @pytest.mark.parametrize("bad", ["Vzlyot", "with_underscore", "-lead", "trail-", "sp ace", ""])
    def test_rejects_invalid(self, bad: str) -> None:
        with pytest.raises(InvalidOrganizationSlugError):
            OrganizationSlug(bad)


class TestStaffEmail:
    def test_normalizes_lowercase(self) -> None:
        assert StaffEmail("New.Staff@Example.COM").value == "new.staff@example.com"

    @pytest.mark.parametrize("bad", ["", "no-at", "a@b", "two@@at.com"])
    def test_rejects_invalid(self, bad: str) -> None:
        with pytest.raises(InvalidStaffEmailError):
            StaffEmail(bad)


class TestInvitationTokenHash:
    def test_accepts_sha256_hex(self) -> None:
        digest = "a" * 64
        assert InvitationTokenHash(digest).value == digest

    def test_repr_is_masked(self) -> None:
        assert "aaaa" in repr(InvitationTokenHash("a" * 64))
        assert ("a" * 64) not in repr(InvitationTokenHash("a" * 64))

    @pytest.mark.parametrize("bad", ["", "abc", "A" * 64, "g" * 64, "a" * 63])
    def test_rejects_non_digest(self, bad: str) -> None:
        with pytest.raises(InvalidInvitationTokenHashError):
            InvitationTokenHash(bad)


class TestEnums:
    def test_role_values(self) -> None:
        assert StaffRole.OWNER.value == "OWNER"
        assert {r.value for r in StaffRole} == {
            "OWNER",
            "DIRECTOR",
            "FINANCE",
            "COMPETITION_MANAGER",
            "CONTENT_MANAGER",
            "MODERATOR",
            "SUPPORT",
        }

    def test_status_values(self) -> None:
        assert {s.value for s in MembershipStatus} == {"PENDING", "ACTIVE", "REVOKED"}
        assert {s.value for s in OrganizationStatus} == {"ACTIVE", "SUSPENDED"}


class TestOrganizationProfile:
    def test_empty_has_all_none_fields(self) -> None:
        profile = OrganizationProfile.empty()
        assert profile.phone is None
        assert profile.email is None
        assert profile.legal_information is None

    def test_strips_whitespace_and_collapses_blanks_to_none(self) -> None:
        profile = OrganizationProfile(phone="  +375 29  ", email="   ")
        assert profile.phone == "+375 29"
        assert profile.email is None

    def test_compares_by_value(self) -> None:
        assert OrganizationProfile(phone="1") == OrganizationProfile(phone="1")
        assert OrganizationProfile(phone="1") != OrganizationProfile(phone="2")

    def test_rejects_overlong_short_field(self) -> None:
        with pytest.raises(InvalidOrganizationProfileError):
            OrganizationProfile(phone="x" * 201)

    def test_rejects_overlong_legal_information(self) -> None:
        with pytest.raises(InvalidOrganizationProfileError):
            OrganizationProfile(legal_information="x" * 5001)

    def test_allows_long_address_and_legal(self) -> None:
        profile = OrganizationProfile(address="x" * 500, legal_information="y" * 5000)
        assert profile.address is not None
        assert len(profile.address) == 500


def test_generate_uuid7_version() -> None:
    assert _generate_uuid7().version == 7
