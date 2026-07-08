"""Unit tests for the :class:`User` aggregate root.

Framework-free, database-free (ARCH-001 §28.2). Every test drives the aggregate
purely through its public surface — the :meth:`~apps.identity.domain.entities.User.register`
/ :meth:`~apps.identity.domain.entities.User.rehydrate` factories, the read-only
properties, and the ``change_*``/``verify_*``/lifecycle behaviour — and asserts
on the domain events each method returns. Time is always supplied explicitly, so
the suite is deterministic.

Coverage spans: registration & rehydration, the full behaviour set (email/phone
change & verification, password change, consent grant/withdraw, lock/unlock,
soft-delete/restore, rename, locale/timezone change), the status helpers,
optimistic-concurrency version bumps, invalid state transitions, identity-based
equality/hashing, the redacted repr, and the immutability of the value objects
held inside the aggregate.
"""

from __future__ import annotations

from dataclasses import FrozenInstanceError
from datetime import UTC, datetime, timedelta

import pytest

from apps.identity.domain.entities import User
from apps.identity.domain.events import (
    ConsentGranted,
    ConsentType,
    ConsentWithdrawn,
    DomainEvent,
    EmailChanged,
    EmailVerified,
    LocaleChanged,
    PasswordChanged,
    PhoneChanged,
    PhoneVerified,
    TimezoneChanged,
    UserDeleted,
    UserLocked,
    UserRegistered,
    UserRenamed,
    UserRestored,
    UserUnlocked,
)
from apps.identity.domain.exceptions import (
    ConsentNotGrantedError,
    DirectConstructionError,
    EmailAlreadyVerifiedError,
    EmailNotChangedError,
    PhoneAlreadyVerifiedError,
    PhoneNotChangedError,
    PhoneNotSetError,
    StaleConsentError,
    UserDeletedError,
    UserNotDeletedError,
    UserNotLockedError,
    VerificationExpiredError,
)
from apps.identity.domain.policies import (
    ConsentPolicy,
    EmailVerificationPolicy,
    PhoneVerificationPolicy,
)
from apps.identity.domain.value_objects import (
    ConsentVersion,
    Email,
    FullName,
    Locale,
    PasswordHash,
    PhoneNumber,
    Timezone,
    UserId,
)

# ---------------------------------------------------------------------------
# Fixtures / helpers
# ---------------------------------------------------------------------------

NOW = datetime(2026, 7, 7, 12, 0, tzinfo=UTC)
#: A realistic Argon2id PHC-encoded digest; the value object only checks shape.
ENCODED_HASH = "$argon2id$v=19$m=65536,t=3,p=4$c29tZXNhbHQ$RGVlcE1hbGxIYXNoVmFsdWU"


@pytest.fixture
def user_id() -> UserId:
    return UserId.generate()


@pytest.fixture
def email() -> Email:
    return Email("ivan@example.com")


@pytest.fixture
def full_name() -> FullName:
    return FullName("Ivan", "Petrov", "Sergeevich")


@pytest.fixture
def password_hash() -> PasswordHash:
    return PasswordHash.from_hash(ENCODED_HASH)


@pytest.fixture
def consent_policy() -> ConsentPolicy:
    return ConsentPolicy(current_version=ConsentVersion("1.0"))


@pytest.fixture
def email_policy() -> EmailVerificationPolicy:
    return EmailVerificationPolicy()


@pytest.fixture
def phone_policy() -> PhoneVerificationPolicy:
    return PhoneVerificationPolicy()


@pytest.fixture
def registered(
    user_id: UserId, email: Email, full_name: FullName, password_hash: PasswordHash
) -> User:
    """A freshly registered aggregate (events discarded)."""
    user, _ = User.register(
        user_id=user_id,
        email=email,
        full_name=full_name,
        password_hash=password_hash,
        now=NOW,
    )
    return user


def _verified(user: User, email_policy: EmailVerificationPolicy, at: datetime = NOW) -> User:
    """Return the same aggregate with its email verified."""
    user.verify_email(policy=email_policy, sent_at=at, now=at)
    return user


# ---------------------------------------------------------------------------
# Construction & factories
# ---------------------------------------------------------------------------


class TestConstruction:
    def test_direct_construction_is_forbidden(
        self, user_id: UserId, email: Email, full_name: FullName, password_hash: PasswordHash
    ) -> None:
        with pytest.raises(DirectConstructionError):
            User(
                _token=object(),
                _id=user_id,
                _email=email,
                _full_name=full_name,
                _locale=Locale.default(),
                _timezone=Timezone.utc(),
                _password_hash=password_hash,
                _created_at=NOW,
                _updated_at=NOW,
            )


class TestRegistration:
    def test_register_returns_user_and_event(
        self, user_id: UserId, email: Email, full_name: FullName, password_hash: PasswordHash
    ) -> None:
        user, events = User.register(
            user_id=user_id,
            email=email,
            full_name=full_name,
            password_hash=password_hash,
            now=NOW,
        )
        assert isinstance(user, User)
        assert len(events) == 1
        assert isinstance(events[0], UserRegistered)

    def test_register_produces_user_registered_payload(
        self, user_id: UserId, email: Email, full_name: FullName, password_hash: PasswordHash
    ) -> None:
        _, events = User.register(
            user_id=user_id,
            email=email,
            full_name=full_name,
            password_hash=password_hash,
            now=NOW,
        )
        event = events[0]
        assert isinstance(event, UserRegistered)
        assert event.aggregate_id == user_id
        assert event.email == email
        assert event.full_name == full_name
        assert event.locale == Locale.default()
        assert event.occurred_at == NOW

    def test_register_initial_state(self, registered: User, user_id: UserId, email: Email) -> None:
        assert registered.id == user_id
        assert registered.email == email
        assert registered.phone is None
        assert registered.consent_version is None
        assert registered.locale == Locale.default()
        assert registered.timezone == Timezone.utc()
        assert registered.created_at == NOW
        assert registered.updated_at == NOW
        assert registered.email_verified_at is None
        assert registered.phone_verified_at is None
        assert registered.locked_until is None
        assert registered.deleted_at is None
        assert registered.version == 1

    def test_register_accepts_optional_preferences(
        self, user_id: UserId, email: Email, full_name: FullName, password_hash: PasswordHash
    ) -> None:
        phone = PhoneNumber("+79991234567")
        user, _ = User.register(
            user_id=user_id,
            email=email,
            full_name=full_name,
            password_hash=password_hash,
            now=NOW,
            phone=phone,
            locale=Locale("en-US"),
            timezone=Timezone("Europe/Moscow"),
        )
        assert user.phone == phone
        assert user.locale == Locale("en-US")
        assert user.timezone == Timezone("Europe/Moscow")


class TestRehydration:
    def test_rehydrate_restores_state_verbatim(
        self, user_id: UserId, email: Email, full_name: FullName, password_hash: PasswordHash
    ) -> None:
        created = datetime(2026, 1, 1, 8, 0, tzinfo=UTC)
        updated = datetime(2026, 6, 1, 9, 0, tzinfo=UTC)
        user = User.rehydrate(
            user_id=user_id,
            email=email,
            full_name=full_name,
            locale=Locale("en-US"),
            timezone=Timezone("Europe/Moscow"),
            password_hash=password_hash,
            created_at=created,
            updated_at=updated,
            version=7,
            phone=PhoneNumber("+79991234567"),
            consent_version=ConsentVersion("1.0"),
            email_verified_at=updated,
            phone_verified_at=updated,
            locked_until=None,
            deleted_at=None,
        )
        assert user.id == user_id
        assert user.locale == Locale("en-US")
        assert user.timezone == Timezone("Europe/Moscow")
        assert user.created_at == created
        assert user.updated_at == updated
        assert user.version == 7
        assert user.phone == PhoneNumber("+79991234567")
        assert user.consent_version == ConsentVersion("1.0")
        assert user.is_email_verified()
        assert user.is_phone_verified()

    def test_rehydrate_emits_no_events(
        self, user_id: UserId, email: Email, full_name: FullName, password_hash: PasswordHash
    ) -> None:
        # rehydrate returns the aggregate only — never a (User, events) tuple.
        user = User.rehydrate(
            user_id=user_id,
            email=email,
            full_name=full_name,
            locale=Locale.default(),
            timezone=Timezone.utc(),
            password_hash=password_hash,
            created_at=NOW,
            updated_at=NOW,
            version=3,
        )
        assert isinstance(user, User)

    def test_rehydrate_never_increments_version(
        self, user_id: UserId, email: Email, full_name: FullName, password_hash: PasswordHash
    ) -> None:
        user = User.rehydrate(
            user_id=user_id,
            email=email,
            full_name=full_name,
            locale=Locale.default(),
            timezone=Timezone.utc(),
            password_hash=password_hash,
            created_at=NOW,
            updated_at=NOW,
            version=42,
        )
        assert user.version == 42


# ---------------------------------------------------------------------------
# Read-only properties
# ---------------------------------------------------------------------------


class TestProperties:
    def test_password_hash_is_exposed(self, registered: User, password_hash: PasswordHash) -> None:
        assert registered.password_hash == password_hash

    def test_full_name_is_exposed(self, registered: User, full_name: FullName) -> None:
        assert registered.full_name == full_name


# ---------------------------------------------------------------------------
# Email
# ---------------------------------------------------------------------------


class TestChangeEmail:
    def test_change_email_updates_and_resets_verification(
        self, registered: User, email_policy: EmailVerificationPolicy
    ) -> None:
        _verified(registered, email_policy)
        assert registered.is_email_verified()
        new_email = Email("new@example.com")
        events = registered.change_email(new_email, now=NOW)
        assert [type(e) for e in events] == [EmailChanged]
        assert registered.email == new_email
        assert not registered.is_email_verified()

    def test_change_email_no_op_is_rejected(self, registered: User, email: Email) -> None:
        with pytest.raises(EmailNotChangedError):
            registered.change_email(email, now=NOW)

    def test_change_email_on_deleted_is_rejected(self, registered: User) -> None:
        registered.soft_delete(now=NOW)
        with pytest.raises(UserDeletedError):
            registered.change_email(Email("new@example.com"), now=NOW)


class TestVerifyEmail:
    def test_verify_email_marks_verified(
        self, registered: User, email_policy: EmailVerificationPolicy
    ) -> None:
        events = registered.verify_email(policy=email_policy, sent_at=NOW, now=NOW)
        assert [type(e) for e in events] == [EmailVerified]
        assert registered.is_email_verified()
        assert registered.email_verified_at == NOW

    def test_verify_email_twice_is_rejected(
        self, registered: User, email_policy: EmailVerificationPolicy
    ) -> None:
        _verified(registered, email_policy)
        with pytest.raises(EmailAlreadyVerifiedError):
            registered.verify_email(policy=email_policy, sent_at=NOW, now=NOW)

    def test_verify_email_after_link_expired_is_rejected(
        self, registered: User, email_policy: EmailVerificationPolicy
    ) -> None:
        sent_at = NOW - timedelta(hours=25)
        with pytest.raises(VerificationExpiredError):
            registered.verify_email(policy=email_policy, sent_at=sent_at, now=NOW)

    def test_ensure_email_unverified_passes_when_unverified(self, registered: User) -> None:
        # A read-only guard: no exception, no state change, no events.
        registered.ensure_email_unverified()
        assert not registered.is_email_verified()

    def test_ensure_email_unverified_rejects_a_verified_email(
        self, registered: User, email_policy: EmailVerificationPolicy
    ) -> None:
        _verified(registered, email_policy)
        with pytest.raises(EmailAlreadyVerifiedError):
            registered.ensure_email_unverified()


# ---------------------------------------------------------------------------
# Phone
# ---------------------------------------------------------------------------


class TestChangePhone:
    def test_change_phone_sets_number(self, registered: User) -> None:
        phone = PhoneNumber("+79991234567")
        events = registered.change_phone(phone, now=NOW)
        assert [type(e) for e in events] == [PhoneChanged]
        assert registered.phone == phone
        assert not registered.is_phone_verified()

    def test_change_phone_replaces_and_resets_verification(
        self, registered: User, phone_policy: PhoneVerificationPolicy
    ) -> None:
        registered.change_phone(PhoneNumber("+79991234567"), now=NOW)
        registered.verify_phone(policy=phone_policy, issued_at=NOW, now=NOW)
        assert registered.is_phone_verified()
        registered.change_phone(PhoneNumber("+79997654321"), now=NOW)
        assert registered.phone == PhoneNumber("+79997654321")
        assert not registered.is_phone_verified()

    def test_change_phone_no_op_is_rejected(self, registered: User) -> None:
        phone = PhoneNumber("+79991234567")
        registered.change_phone(phone, now=NOW)
        with pytest.raises(PhoneNotChangedError):
            registered.change_phone(phone, now=NOW)


class TestVerifyPhone:
    def test_verify_phone_marks_verified(
        self, registered: User, phone_policy: PhoneVerificationPolicy
    ) -> None:
        registered.change_phone(PhoneNumber("+79991234567"), now=NOW)
        events = registered.verify_phone(policy=phone_policy, issued_at=NOW, now=NOW)
        assert [type(e) for e in events] == [PhoneVerified]
        assert registered.is_phone_verified()
        assert registered.phone_verified_at == NOW

    def test_verify_phone_without_number_is_rejected(
        self, registered: User, phone_policy: PhoneVerificationPolicy
    ) -> None:
        with pytest.raises(PhoneNotSetError):
            registered.verify_phone(policy=phone_policy, issued_at=NOW, now=NOW)

    def test_verify_phone_twice_is_rejected(
        self, registered: User, phone_policy: PhoneVerificationPolicy
    ) -> None:
        registered.change_phone(PhoneNumber("+79991234567"), now=NOW)
        registered.verify_phone(policy=phone_policy, issued_at=NOW, now=NOW)
        with pytest.raises(PhoneAlreadyVerifiedError):
            registered.verify_phone(policy=phone_policy, issued_at=NOW, now=NOW)

    def test_verify_phone_after_code_expired_is_rejected(
        self, registered: User, phone_policy: PhoneVerificationPolicy
    ) -> None:
        registered.change_phone(PhoneNumber("+79991234567"), now=NOW)
        issued_at = NOW - timedelta(minutes=11)
        with pytest.raises(VerificationExpiredError):
            registered.verify_phone(policy=phone_policy, issued_at=issued_at, now=NOW)


# ---------------------------------------------------------------------------
# Password
# ---------------------------------------------------------------------------


class TestChangePassword:
    def test_change_password_replaces_digest(self, registered: User) -> None:
        new_hash = PasswordHash.from_hash(
            "$argon2id$v=19$m=65536,t=3,p=4$bmV3c2FsdA$TmV3RGlnZXN0VmFsdWU"
        )
        events = registered.change_password(new_hash, now=NOW)
        assert [type(e) for e in events] == [PasswordChanged]
        assert registered.password_hash == new_hash

    def test_change_password_on_deleted_is_rejected(self, registered: User) -> None:
        registered.soft_delete(now=NOW)
        with pytest.raises(UserDeletedError):
            registered.change_password(
                PasswordHash.from_hash("$argon2id$x$y$c29tZXNhbHQ$RGlnZXN0"), now=NOW
            )


# ---------------------------------------------------------------------------
# Consent
# ---------------------------------------------------------------------------


class TestConsent:
    def test_grant_consent_records_version(
        self, registered: User, consent_policy: ConsentPolicy
    ) -> None:
        version = ConsentVersion("1.0")
        events = registered.grant_consent(version, policy=consent_policy, now=NOW)
        assert [type(e) for e in events] == [ConsentGranted]
        assert registered.consent_version == version

    def test_grant_consent_uses_given_type(
        self, registered: User, consent_policy: ConsentPolicy
    ) -> None:
        events = registered.grant_consent(
            ConsentVersion("1.0"),
            policy=consent_policy,
            now=NOW,
            consent_type=ConsentType.PRIVACY_POLICY,
        )
        granted = events[0]
        assert isinstance(granted, ConsentGranted)
        assert granted.consent_type is ConsentType.PRIVACY_POLICY

    def test_grant_stale_consent_is_rejected(self, registered: User) -> None:
        policy = ConsentPolicy(current_version=ConsentVersion("2.0"))
        with pytest.raises(StaleConsentError):
            registered.grant_consent(ConsentVersion("1.0"), policy=policy, now=NOW)

    def test_withdraw_consent_clears_version(
        self, registered: User, consent_policy: ConsentPolicy
    ) -> None:
        registered.grant_consent(ConsentVersion("1.0"), policy=consent_policy, now=NOW)
        events = registered.withdraw_consent(now=NOW)
        assert [type(e) for e in events] == [ConsentWithdrawn]
        assert registered.consent_version is None

    def test_withdraw_without_consent_is_rejected(self, registered: User) -> None:
        with pytest.raises(ConsentNotGrantedError):
            registered.withdraw_consent(now=NOW)


# ---------------------------------------------------------------------------
# Lock / unlock
# ---------------------------------------------------------------------------


class TestLocking:
    def test_temporary_lock_sets_deadline(self, registered: User) -> None:
        until = NOW + timedelta(minutes=15)
        events = registered.lock(reason="too many attempts", until=until, now=NOW)
        assert [type(e) for e in events] == [UserLocked]
        assert registered.locked_until == until
        assert registered.is_locked(NOW)

    def test_permanent_lock_uses_far_future_sentinel(self, registered: User) -> None:
        registered.lock(reason="fraud", until=None, now=NOW)
        assert registered.locked_until == datetime.max.replace(tzinfo=UTC)
        assert registered.is_locked(NOW)

    def test_unlock_releases_lock(self, registered: User) -> None:
        registered.lock(reason="x", until=NOW + timedelta(hours=1), now=NOW)
        events = registered.unlock(reason="appeal upheld", now=NOW)
        assert [type(e) for e in events] == [UserUnlocked]
        assert registered.locked_until is None
        assert not registered.is_locked(NOW)

    def test_unlock_when_not_locked_is_rejected(self, registered: User) -> None:
        with pytest.raises(UserNotLockedError):
            registered.unlock(reason="noop", now=NOW)


# ---------------------------------------------------------------------------
# Lifecycle: delete / restore
# ---------------------------------------------------------------------------


class TestLifecycle:
    def test_soft_delete_marks_deleted(self, registered: User) -> None:
        events = registered.soft_delete(now=NOW, reason="user requested")
        assert [type(e) for e in events] == [UserDeleted]
        assert registered.is_deleted()
        assert registered.deleted_at == NOW

    def test_soft_delete_twice_is_rejected(self, registered: User) -> None:
        registered.soft_delete(now=NOW)
        with pytest.raises(UserDeletedError):
            registered.soft_delete(now=NOW)

    def test_restore_reactivates(self, registered: User) -> None:
        registered.soft_delete(now=NOW)
        events = registered.restore(now=NOW)
        assert [type(e) for e in events] == [UserRestored]
        assert not registered.is_deleted()

    def test_restore_when_active_is_rejected(self, registered: User) -> None:
        with pytest.raises(UserNotDeletedError):
            registered.restore(now=NOW)


# ---------------------------------------------------------------------------
# Profile
# ---------------------------------------------------------------------------


class TestProfile:
    def test_rename_changes_name(self, registered: User) -> None:
        new_name = FullName("Anna", "Ivanova")
        events = registered.rename(new_name, now=NOW)
        assert [type(e) for e in events] == [UserRenamed]
        assert registered.full_name == new_name

    def test_change_locale(self, registered: User) -> None:
        events = registered.change_locale(Locale("en-US"), now=NOW)
        assert [type(e) for e in events] == [LocaleChanged]
        assert registered.locale == Locale("en-US")

    def test_change_timezone(self, registered: User) -> None:
        events = registered.change_timezone(Timezone("Europe/Moscow"), now=NOW)
        assert [type(e) for e in events] == [TimezoneChanged]
        assert registered.timezone == Timezone("Europe/Moscow")


# ---------------------------------------------------------------------------
# Status helpers
# ---------------------------------------------------------------------------


class TestStatusHelpers:
    def test_is_deleted_reflects_state(self, registered: User) -> None:
        assert not registered.is_deleted()
        registered.soft_delete(now=NOW)
        assert registered.is_deleted()

    def test_is_locked_is_false_when_never_locked(self, registered: User) -> None:
        assert not registered.is_locked(NOW)

    def test_temporary_lock_auto_expires(self, registered: User) -> None:
        until = NOW + timedelta(minutes=15)
        registered.lock(reason="cool-off", until=until, now=NOW)
        assert registered.is_locked(NOW)
        assert not registered.is_locked(until + timedelta(seconds=1))

    def test_requires_consent_when_never_granted(
        self, registered: User, consent_policy: ConsentPolicy
    ) -> None:
        assert registered.requires_consent(consent_policy)

    def test_requires_consent_false_when_current(
        self, registered: User, consent_policy: ConsentPolicy
    ) -> None:
        registered.grant_consent(ConsentVersion("1.0"), policy=consent_policy, now=NOW)
        assert not registered.requires_consent(consent_policy)

    def test_requires_consent_when_version_superseded(
        self, registered: User, consent_policy: ConsentPolicy
    ) -> None:
        registered.grant_consent(ConsentVersion("1.0"), policy=consent_policy, now=NOW)
        newer = ConsentPolicy(current_version=ConsentVersion("2.0"))
        assert registered.requires_consent(newer)

    def test_can_login_requires_verified_email(self, registered: User) -> None:
        assert not registered.can_login(now=NOW)

    def test_can_login_when_active_verified_unlocked(
        self, registered: User, email_policy: EmailVerificationPolicy
    ) -> None:
        _verified(registered, email_policy)
        assert registered.can_login(now=NOW)

    def test_can_login_false_when_locked(
        self, registered: User, email_policy: EmailVerificationPolicy
    ) -> None:
        _verified(registered, email_policy)
        registered.lock(reason="x", until=NOW + timedelta(hours=1), now=NOW)
        assert not registered.can_login(now=NOW)

    def test_can_login_false_when_deleted(
        self, registered: User, email_policy: EmailVerificationPolicy
    ) -> None:
        _verified(registered, email_policy)
        registered.soft_delete(now=NOW)
        assert not registered.can_login(now=NOW)


# ---------------------------------------------------------------------------
# Optimistic concurrency
# ---------------------------------------------------------------------------


class TestOptimisticConcurrency:
    def test_version_increments_once_per_mutation(self, registered: User) -> None:
        assert registered.version == 1
        registered.change_locale(Locale("en-US"), now=NOW)
        assert registered.version == 2
        registered.change_timezone(Timezone("Europe/Moscow"), now=NOW)
        assert registered.version == 3

    def test_updated_at_advances_on_mutation(self, registered: User) -> None:
        later = NOW + timedelta(hours=1)
        registered.rename(FullName("Anna", "Ivanova"), now=later)
        assert registered.updated_at == later

    def test_failed_transition_does_not_bump_version(self, registered: User) -> None:
        with pytest.raises(ConsentNotGrantedError):
            registered.withdraw_consent(now=NOW)
        assert registered.version == 1


# ---------------------------------------------------------------------------
# Identity semantics
# ---------------------------------------------------------------------------


class TestIdentity:
    def test_equality_is_by_id(
        self, user_id: UserId, email: Email, full_name: FullName, password_hash: PasswordHash
    ) -> None:
        one, _ = User.register(
            user_id=user_id,
            email=email,
            full_name=full_name,
            password_hash=password_hash,
            now=NOW,
        )
        # Same identity, divergent state — still equal.
        two = User.rehydrate(
            user_id=user_id,
            email=Email("other@example.com"),
            full_name=FullName("Other", "Person"),
            locale=Locale.default(),
            timezone=Timezone.utc(),
            password_hash=password_hash,
            created_at=NOW,
            updated_at=NOW,
            version=99,
        )
        assert one == two

    def test_distinct_ids_are_not_equal(
        self, email: Email, full_name: FullName, password_hash: PasswordHash
    ) -> None:
        one, _ = User.register(
            user_id=UserId.generate(),
            email=email,
            full_name=full_name,
            password_hash=password_hash,
            now=NOW,
        )
        two, _ = User.register(
            user_id=UserId.generate(),
            email=email,
            full_name=full_name,
            password_hash=password_hash,
            now=NOW,
        )
        assert one != two

    def test_equality_with_non_user_is_false(self, registered: User) -> None:
        assert (registered == "not a user") is False
        assert registered != 42

    def test_hash_is_by_id_and_usable_in_set(self, registered: User) -> None:
        same_id = User.rehydrate(
            user_id=registered.id,
            email=Email("other@example.com"),
            full_name=FullName("Other", "Person"),
            locale=Locale.default(),
            timezone=Timezone.utc(),
            password_hash=registered.password_hash,
            created_at=NOW,
            updated_at=NOW,
            version=5,
        )
        assert hash(registered) == hash(same_id)
        assert len({registered, same_id}) == 1


class TestRepr:
    def test_repr_is_readable_and_redacts_password(self, registered: User) -> None:
        text = repr(registered)
        assert "User(" in text
        assert registered.id.json() in text
        assert "version=1" in text
        assert ENCODED_HASH not in text
        assert "argon2" not in text


# ---------------------------------------------------------------------------
# Immutability of the value objects held inside the aggregate
# ---------------------------------------------------------------------------


class TestValueObjectImmutability:
    def test_email_value_object_is_frozen(self, registered: User) -> None:
        with pytest.raises(FrozenInstanceError):
            registered.email.value = "hacked@example.com"  # type: ignore[misc]

    def test_full_name_value_object_is_frozen(self, registered: User) -> None:
        with pytest.raises(FrozenInstanceError):
            registered.full_name.first_name = "Mallory"  # type: ignore[misc]

    def test_password_hash_value_object_is_frozen(self, registered: User) -> None:
        with pytest.raises(FrozenInstanceError):
            registered.password_hash.encoded_hash = "tampered"  # type: ignore[misc]


# ---------------------------------------------------------------------------
# Domain event generation — every mutating method returns DomainEvents
# ---------------------------------------------------------------------------


class TestEventGeneration:
    def test_every_returned_event_is_a_domain_event(
        self,
        registered: User,
        consent_policy: ConsentPolicy,
        email_policy: EmailVerificationPolicy,
    ) -> None:
        produced: list[DomainEvent] = []
        produced += registered.verify_email(policy=email_policy, sent_at=NOW, now=NOW)
        produced += registered.change_phone(PhoneNumber("+79991234567"), now=NOW)
        produced += registered.grant_consent(ConsentVersion("1.0"), policy=consent_policy, now=NOW)
        produced += registered.change_password(
            PasswordHash.from_hash("$argon2id$v=19$m=1$c2FsdHNhbHQ$RGlnZXN0VmFs"), now=NOW
        )
        produced += registered.lock(reason="x", until=NOW + timedelta(hours=1), now=NOW)
        assert produced
        assert all(isinstance(event, DomainEvent) for event in produced)
        assert all(event.aggregate_id == registered.id for event in produced)
