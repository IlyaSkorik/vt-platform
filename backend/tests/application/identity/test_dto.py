"""Unit tests for the Identity application result DTOs.

Exercises both branches of every optional projection in :meth:`UserDto.from_user`
(phone, middle name, consent, lock status) and the :class:`OperationResultDto`
container's immutability.
"""

from __future__ import annotations

import dataclasses
from datetime import timedelta

import pytest

from apps.identity.application.dto import OperationResultDto, UserDto
from apps.identity.domain.entities import User
from apps.identity.domain.policies import ConsentPolicy
from apps.identity.domain.value_objects import (
    ConsentVersion,
    Email,
    FullName,
    PasswordHash,
    PhoneNumber,
    UserId,
)
from tests.application.identity.fakes import NOW

VALID_HASH = PasswordHash.from_hash("$argon2id$v=19$m=65536,t=3,p=4$c2FsdA$aGFzaA")
CONSENT_POLICY = ConsentPolicy(current_version=ConsentVersion("1.0"))


def _register(*, phone: str | None, middle: str | None) -> User:
    user, _ = User.register(
        user_id=UserId.generate(),
        email=Email("member@example.com"),
        full_name=FullName.of("Ivan", "Petrov", middle),
        password_hash=VALID_HASH,
        now=NOW,
        phone=PhoneNumber(phone) if phone is not None else None,
    )
    return user


class TestUserDto:
    def test_projects_populated_user(self) -> None:
        user = _register(phone="+79991234567", middle="Ivanovich")
        user.grant_consent(ConsentVersion("1.0"), policy=CONSENT_POLICY, now=NOW)
        user.lock(reason="fraud", until=NOW + timedelta(hours=1), now=NOW)

        dto = UserDto.from_user(user, now=NOW)

        assert dto.id == user.id.json()
        assert dto.phone == "+79991234567"
        assert dto.middle_name == "Ivanovich"
        assert dto.full_name == "Ivan Ivanovich Petrov"
        assert dto.consent_version == "1.0"
        assert dto.is_locked is True
        assert dto.locked_until is not None

    def test_projects_minimal_user(self) -> None:
        user = _register(phone=None, middle=None)

        dto = UserDto.from_user(user, now=NOW)

        assert dto.phone is None
        assert dto.middle_name is None
        assert dto.consent_version is None
        assert dto.is_locked is False
        assert dto.locked_until is None
        assert dto.is_email_verified is False
        assert dto.version == 1


class TestOperationResultDto:
    def test_holds_user_and_events(self) -> None:
        user = _register(phone=None, middle=None)
        dto = UserDto.from_user(user, now=NOW)
        result = OperationResultDto(user=dto, events=())

        assert result.user is dto
        assert result.events == ()

    def test_is_immutable(self) -> None:
        user = _register(phone=None, middle=None)
        result = OperationResultDto(user=UserDto.from_user(user, now=NOW), events=())
        with pytest.raises(dataclasses.FrozenInstanceError):
            result.events = ()  # type: ignore[misc]
