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
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, datetime

from apps.identity.application.dto import TokenPairDto
from apps.identity.application.exceptions import (
    InvalidTokenError,
    InvalidVerificationTokenError,
)
from apps.identity.application.interfaces import VerificationToken
from apps.identity.domain.entities import User
from apps.identity.domain.events import DomainEvent
from apps.identity.domain.value_objects import (
    Email,
    FullName,
    Locale,
    PasswordHash,
    PhoneNumber,
    UserId,
)

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


class FakeTokenService:
    """Deterministic :class:`TokenService` fake — no cryptography, no persistence.

    Tracks which refresh tokens are still valid so ``rotate``/``revoke`` reject an
    unknown, already-rotated, or already-revoked token exactly as a real adapter
    would (raising :class:`InvalidTokenError`).
    """

    def __init__(self) -> None:
        self.issued: list[str] = []
        self.rotated: list[str] = []
        self.revoked: list[str] = []
        self._valid: set[str] = set()
        self._counter = 0

    def issue(self, *, subject: str) -> TokenPairDto:
        self._counter += 1
        refresh = f"refresh-{subject}-{self._counter}"
        access = f"access-{subject}-{self._counter}"
        self._valid.add(refresh)
        self.issued.append(subject)
        return TokenPairDto(access_token=access, refresh_token=refresh, token_type="Bearer", expires_in=900)

    def rotate(self, *, refresh_token: str) -> TokenPairDto:
        if refresh_token not in self._valid:
            raise InvalidTokenError("The refresh token is invalid or expired.")
        self._valid.discard(refresh_token)
        self.rotated.append(refresh_token)
        return self.issue(subject="rotated")

    def revoke(self, *, refresh_token: str) -> None:
        if refresh_token not in self._valid:
            raise InvalidTokenError("The refresh token is invalid or expired.")
        self._valid.discard(refresh_token)
        self.revoked.append(refresh_token)


@dataclass(frozen=True, slots=True)
class SentEmail:
    """A verification email a :class:`FakeEmailGateway` recorded."""

    email: Email
    full_name: FullName
    verification_url: str
    locale: Locale


class FakeEmailGateway:
    """Recording :class:`EmailGateway` fake — captures calls, sends nothing."""

    def __init__(self) -> None:
        self.verification_emails: list[SentEmail] = []
        self.password_resets: list[Email] = []

    def send_verification_email(self, *, email: Email, full_name: FullName, verification_url: str, locale: Locale) -> None:
        self.verification_emails.append(
            SentEmail(
                email=email,
                full_name=full_name,
                verification_url=verification_url,
                locale=locale,
            )
        )

    def send_password_reset(
        self,
        *,
        email: Email,
        full_name: FullName,
        reset_url: str,
        expires_at: datetime,
        locale: Locale,
    ) -> None:
        self.password_resets.append(email)


class FakeVerificationTokenService:
    """Reversible :class:`VerificationTokenService` fake — no cryptography.

    Mints a self-describing link whose token round-trips back to the exact
    ``(user_id, issued_at)`` it was issued for; an unknown token is rejected with
    :class:`InvalidVerificationTokenError`, mirroring a bad signature.
    """

    def __init__(self) -> None:
        self._issued: dict[str, VerificationToken] = {}
        self.links: list[str] = []

    def issue_link(self, *, user_id: UserId, issued_at: datetime) -> str:
        token = f"tok-{user_id.json()}-{issued_at.isoformat()}"
        self._issued[token] = VerificationToken(user_id=user_id, issued_at=issued_at)
        link = f"https://frontend.test/verify-email?token={token}"
        self.links.append(link)
        return link

    def verify(self, token: str) -> VerificationToken:
        decoded = self._issued.get(token)
        if decoded is None:
            raise InvalidVerificationTokenError("The verification token is invalid.")
        return decoded


class FakeEventPublisher:
    """Recording :class:`EventPublisher` fake — captures published events in order."""

    def __init__(self) -> None:
        self.published: list[DomainEvent] = []

    def publish(self, events: Sequence[DomainEvent]) -> None:
        self.published.extend(events)
