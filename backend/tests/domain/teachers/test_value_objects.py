"""Unit tests for the Teacher Directory value objects."""

from __future__ import annotations

import uuid

import pytest

from apps.teachers.domain.exceptions import (
    InvalidEmailAddressError,
    InvalidOwnerIdError,
    InvalidPersonNameError,
    InvalidPhoneNumberError,
    InvalidTeacherIdError,
    InvalidTeacherRoleError,
)
from apps.teachers.domain.value_objects import (
    EmailAddress,
    OwnerId,
    PersonName,
    PhoneNumber,
    TeacherId,
    TeacherRole,
    TeacherStatus,
)


class TestIdentifiers:
    def test_teacher_id_roundtrips(self) -> None:
        tid = TeacherId.generate()
        assert TeacherId.from_string(tid.json()) == tid

    def test_teacher_id_rejects_non_v7(self) -> None:
        with pytest.raises(InvalidTeacherIdError):
            TeacherId.from_uuid(uuid.uuid4())

    def test_owner_id_rejects_non_v7(self) -> None:
        with pytest.raises(InvalidOwnerIdError):
            OwnerId.from_uuid(uuid.uuid4())

    def test_owner_id_rejects_garbage(self) -> None:
        with pytest.raises(InvalidOwnerIdError):
            OwnerId.from_string("nope")


class TestPersonName:
    def test_full_name_orders_last_first_middle(self) -> None:
        name = PersonName(first_name="Anna", last_name="Ivanova", middle_name="Petrovna")
        assert name.full_name == "Ivanova Anna Petrovna"

    def test_blank_middle_becomes_none(self) -> None:
        assert PersonName(first_name="Anna", last_name="Ivanova", middle_name="  ").middle_name is None

    def test_rejects_empty_first(self) -> None:
        with pytest.raises(InvalidPersonNameError):
            PersonName(first_name="  ", last_name="Ivanova")


class TestTeacherRole:
    def test_trims(self) -> None:
        assert TeacherRole("  Choreographer ").value == "Choreographer"

    def test_rejects_empty(self) -> None:
        with pytest.raises(InvalidTeacherRoleError):
            TeacherRole("   ")


class TestEmailAddress:
    def test_lowercases(self) -> None:
        assert EmailAddress("Teacher@School.RU").value == "teacher@school.ru"

    @pytest.mark.parametrize("bad", ["nope", "a@b", "@b.ru", "a b@c.ru"])
    def test_rejects_malformed(self, bad: str) -> None:
        with pytest.raises(InvalidEmailAddressError):
            EmailAddress(bad)


class TestPhoneNumber:
    def test_accepts_plausible(self) -> None:
        assert PhoneNumber("+7 (999) 123-45-67").value == "+7 (999) 123-45-67"

    @pytest.mark.parametrize("bad", ["abc", "12", ""])
    def test_rejects_malformed(self, bad: str) -> None:
        with pytest.raises(InvalidPhoneNumberError):
            PhoneNumber(bad)


class TestTeacherStatus:
    def test_members(self) -> None:
        assert {s.value for s in TeacherStatus} == {"ACTIVE", "ARCHIVED"}
