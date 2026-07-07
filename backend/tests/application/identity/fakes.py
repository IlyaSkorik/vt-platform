"""In-memory fakes for the Identity application ports.

Framework-free, database-free test doubles that structurally satisfy the ports
in :mod:`apps.identity.application.interfaces`. They record their interactions so
tests can assert on them. Domain **policies** are pure, deterministic value
objects and are used for real (not faked) by the tests.

This module is not a test module (no ``test_`` prefix), so pytest does not
collect it; it is imported by the handler tests.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from apps.identity.domain.entities import User
from apps.identity.domain.value_objects import Email, PasswordHash, PhoneNumber, UserId

#: Fixed reference instant shared by the fake clock and the tests.
NOW = datetime(2026, 7, 7, 12, 0, tzinfo=UTC)


class FakeUserRepository:
    """In-memory :class:`UserRepository` keyed by :class:`UserId`."""

    def __init__(self) -> None:
        self._by_id: dict[UserId, User] = {}
        self.saved: list[User] = []
        self.deleted: list[User] = []

    def get(self, user_id: UserId) -> User | None:
        return self._by_id.get(user_id)

    def get_by_email(self, email: Email) -> User | None:
        return next((u for u in self._by_id.values() if u.email == email), None)

    def get_by_phone(self, phone: PhoneNumber) -> User | None:
        return next((u for u in self._by_id.values() if u.phone == phone), None)

    def exists(self, user_id: UserId) -> bool:
        return user_id in self._by_id

    def exists_by_email(self, email: Email) -> bool:
        return any(u.email == email for u in self._by_id.values())

    def exists_by_phone(self, phone: PhoneNumber) -> bool:
        return any(u.phone == phone for u in self._by_id.values())

    def save(self, user: User) -> None:
        self._by_id[user.id] = user
        self.saved.append(user)

    def delete(self, user: User) -> None:
        self._by_id.pop(user.id, None)
        self.deleted.append(user)

    # Test convenience: seed a user without going through ``save`` bookkeeping.
    def seed(self, user: User) -> User:
        self._by_id[user.id] = user
        return user


class FakePasswordHasher:
    """Deterministic :class:`PasswordHasher` fake — no real cryptography."""

    def __init__(self) -> None:
        self.hashed: list[str] = []

    def hash(self, password: str) -> PasswordHash:
        self.hashed.append(password)
        return PasswordHash.from_hash(f"$argon2id$v=19$m=1,t=1,p=1$c2FsdA${password}")

    def verify(self, password: str, hash: PasswordHash) -> bool:
        return hash.encoded_hash.endswith(f"${password}")

    def needs_rehash(self, hash: PasswordHash) -> bool:
        return hash.needs_migration()


class FakeClock:
    """:class:`Clock` fake frozen at a fixed instant."""

    def __init__(self, moment: datetime = NOW) -> None:
        self._moment = moment

    def now(self) -> datetime:
        return self._moment

    def utcnow(self) -> datetime:
        return self._moment.astimezone(UTC)


class FakeUuidGenerator:
    """:class:`UuidGenerator` fake producing fresh UUID v7 values, recording them."""

    def __init__(self) -> None:
        self.issued: list[uuid.UUID] = []

    def new(self) -> uuid.UUID:
        value = UserId.generate().value
        self.issued.append(value)
        return value
