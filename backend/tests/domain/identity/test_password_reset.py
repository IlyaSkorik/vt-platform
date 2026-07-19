"""Unit tests for the password-reset domain rules.

Framework-free, database-free: exercises
:class:`~apps.identity.domain.policies.PasswordResetPolicy` and the
:meth:`~apps.identity.domain.entities.User.reset_password` behaviour purely through
the public surface, with time supplied explicitly. Covers the happy path (new
digest stored, credential cut-off stamped, ``PasswordResetCompleted`` emitted), an
expired link (``VerificationExpiredError``), and refusal on a deleted account.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from apps.identity.domain.entities import User
from apps.identity.domain.events import PasswordResetCompleted
from apps.identity.domain.exceptions import PolicyConfigurationError, UserDeletedError, VerificationExpiredError
from apps.identity.domain.policies import PasswordResetPolicy
from apps.identity.domain.value_objects import Email, FullName, Locale, PasswordHash, Timezone, UserId

NOW = datetime(2026, 7, 7, 12, 0, tzinfo=UTC)
_OLD_HASH = "$argon2id$v=19$m=65536,t=3,p=4$c29tZXNhbHQ$T2xkSGFzaFZhbHVlUGFkZGluZ0FB"
_NEW_HASH = "$argon2id$v=19$m=65536,t=3,p=4$c29tZXNhbHQ$TmV3SGFzaFZhbHVlUGFkZGluZ0FB"


def _registered() -> User:
    user, _ = User.register(
        user_id=UserId.generate(),
        email=Email("recover@example.com"),
        full_name=FullName.of("Reset", "Test"),
        password_hash=PasswordHash.from_hash(_OLD_HASH),
        now=NOW,
    )
    return user


class TestPasswordResetPolicy:
    def test_default_timeout_is_one_hour(self) -> None:
        assert PasswordResetPolicy().reset_timeout == timedelta(hours=1)

    def test_link_within_the_window_is_not_expired(self) -> None:
        policy = PasswordResetPolicy(reset_timeout=timedelta(hours=1))
        assert policy.is_reset_expired(NOW, NOW + timedelta(minutes=59)) is False

    def test_link_at_or_past_the_window_is_expired(self) -> None:
        policy = PasswordResetPolicy(reset_timeout=timedelta(hours=1))
        assert policy.is_reset_expired(NOW, NOW + timedelta(hours=1)) is True

    def test_non_positive_timeout_is_rejected(self) -> None:
        with pytest.raises(PolicyConfigurationError):
            PasswordResetPolicy(reset_timeout=timedelta(0))


class TestResetPassword:
    def test_sets_new_digest_stamps_cutoff_and_emits_completed(self) -> None:
        user = _registered()
        later = NOW + timedelta(minutes=10)
        new_hash = PasswordHash.from_hash(_NEW_HASH)

        events = user.reset_password(
            new_hash,
            policy=PasswordResetPolicy(),
            issued_at=NOW,
            now=later,
        )

        assert user.password_hash == new_hash
        assert user.credentials_invalidated_at == later
        assert [type(e) for e in events] == [PasswordResetCompleted]
        completed = events[0]
        assert isinstance(completed, PasswordResetCompleted)
        assert completed.email == user.email
        assert completed.occurred_at == later

    def test_expired_link_is_refused(self) -> None:
        user = _registered()

        with pytest.raises(VerificationExpiredError):
            user.reset_password(
                PasswordHash.from_hash(_NEW_HASH),
                policy=PasswordResetPolicy(reset_timeout=timedelta(hours=1)),
                issued_at=NOW,
                now=NOW + timedelta(hours=2),
            )
        # An expired link changes nothing.
        assert user.credentials_invalidated_at is None

    def test_deleted_account_is_refused(self) -> None:
        user = _registered()
        user.soft_delete(now=NOW)

        with pytest.raises(UserDeletedError):
            user.reset_password(
                PasswordHash.from_hash(_NEW_HASH),
                policy=PasswordResetPolicy(),
                issued_at=NOW,
                now=NOW + timedelta(minutes=1),
            )

    def test_rehydrate_round_trips_credentials_invalidated_at(self) -> None:
        cutoff = NOW + timedelta(minutes=5)
        user = User.rehydrate(
            user_id=UserId.generate(),
            email=Email("recover@example.com"),
            full_name=FullName.of("Reset", "Test"),
            locale=Locale.default(),
            timezone=Timezone.utc(),
            password_hash=PasswordHash.from_hash(_OLD_HASH),
            created_at=NOW,
            updated_at=NOW,
            version=3,
            credentials_invalidated_at=cutoff,
        )
        assert user.credentials_invalidated_at == cutoff
