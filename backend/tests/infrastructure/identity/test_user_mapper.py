"""Unit tests for :class:`apps.identity.infrastructure.mappers.UserMapper`.

The mapper is the Anti-Corruption Layer between the framework-free ``User``
aggregate and the ``UserModel`` ORM row. These tests exercise it as a pure
translator: **no database is touched** — model instances are built in memory and
never saved — so no ``django_db`` marker is required. This is exactly the mapper's
contract: it converts, and only converts (ARCH-001 §7.2, §14).

Coverage spans both directions (Domain → ORM, ORM → Domain), the round-trip
identity, and every optional/nullable dimension: absent phone/consent/verification
timestamps, soft-deleted, locked, email-verified, phone-verified, consent,
version, UUID identity, timezone, locale, and password-hash mapping.
"""

from __future__ import annotations

from datetime import UTC, datetime

from apps.identity.domain.entities import User
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
from apps.identity.infrastructure.mappers import UserMapper
from apps.identity.infrastructure.models import UserModel

# ---------------------------------------------------------------------------
# Fixtures / builders
# ---------------------------------------------------------------------------

_ARGON2_HASH = "$argon2id$v=19$m=65536,t=3,p=4$c29tZXNhbHQ$c29tZWhhc2h2YWx1ZQ"
_PBKDF2_HASH = "pbkdf2_sha256$260000$c29tZXNhbHQ$aGFzaGVkcGFzc3dvcmR2YWx1ZQ=="


def make_full_user() -> User:
    """A maximally-populated aggregate: phone, consent, all timestamps, locked, deleted.

    The mapper never validates business rules, so an account that is simultaneously
    verified, locked, and deleted is a perfectly legal *persistence* projection to
    round-trip.
    """
    return User.rehydrate(
        user_id=UserId.generate(),
        email=Email("ivan.petrov@example.com"),
        full_name=FullName(first_name="Ivan", last_name="Petrov", middle_name="Sergeevich"),
        locale=Locale("ru-RU"),
        timezone=Timezone("Europe/Moscow"),
        password_hash=PasswordHash(algorithm="argon2id", encoded_hash=_ARGON2_HASH),
        created_at=datetime(2026, 1, 1, 12, 0, tzinfo=UTC),
        updated_at=datetime(2026, 2, 1, 9, 30, tzinfo=UTC),
        version=7,
        phone=PhoneNumber("+79991234567"),
        consent_version=ConsentVersion("2026-01"),
        email_verified_at=datetime(2026, 1, 2, 8, 0, tzinfo=UTC),
        phone_verified_at=datetime(2026, 1, 3, 8, 0, tzinfo=UTC),
        locked_until=datetime(2026, 3, 1, 0, 0, tzinfo=UTC),
        deleted_at=datetime(2026, 4, 1, 0, 0, tzinfo=UTC),
    )


def make_minimal_user() -> User:
    """A minimally-populated aggregate: no phone, no consent, nothing verified/locked/deleted."""
    return User.rehydrate(
        user_id=UserId.generate(),
        email=Email("anna@example.com"),
        full_name=FullName(first_name="Anna", last_name="Ivanova"),
        locale=Locale.default(),
        timezone=Timezone.utc(),
        password_hash=PasswordHash(algorithm="pbkdf2_sha256", encoded_hash=_PBKDF2_HASH),
        created_at=datetime(2026, 1, 1, 0, 0, tzinfo=UTC),
        updated_at=datetime(2026, 1, 1, 0, 0, tzinfo=UTC),
        version=1,
    )


def assert_users_equal(actual: User, expected: User) -> None:
    """Assert two aggregates are equal by identity *and* field-by-field."""
    assert actual == expected  # identity semantics (UserId)
    assert actual.id == expected.id
    assert actual.email == expected.email
    assert actual.phone == expected.phone
    assert actual.full_name == expected.full_name
    assert actual.locale == expected.locale
    assert actual.timezone == expected.timezone
    assert actual.password_hash == expected.password_hash
    assert actual.consent_version == expected.consent_version
    assert actual.created_at == expected.created_at
    assert actual.updated_at == expected.updated_at
    assert actual.email_verified_at == expected.email_verified_at
    assert actual.phone_verified_at == expected.phone_verified_at
    assert actual.locked_until == expected.locked_until
    assert actual.deleted_at == expected.deleted_at
    assert actual.version == expected.version


# ---------------------------------------------------------------------------
# Domain -> ORM (to_model)
# ---------------------------------------------------------------------------


def test_to_model_maps_every_column_from_a_full_aggregate() -> None:
    user = make_full_user()

    model = UserMapper.to_model(user)

    assert model.id == user.id.value
    assert model.email == "ivan.petrov@example.com"
    assert model.phone == "+79991234567"
    assert model.first_name == "Ivan"
    assert model.last_name == "Petrov"
    assert model.middle_name == "Sergeevich"
    assert model.locale == "ru-RU"
    assert model.timezone == "Europe/Moscow"
    assert model.password_algorithm == "argon2id"
    assert model.password_hash == _ARGON2_HASH
    assert model.consent_version == "2026-01"
    assert model.email_verified_at == datetime(2026, 1, 2, 8, 0, tzinfo=UTC)
    assert model.phone_verified_at == datetime(2026, 1, 3, 8, 0, tzinfo=UTC)
    assert model.locked_until == datetime(2026, 3, 1, 0, 0, tzinfo=UTC)
    assert model.deleted_at == datetime(2026, 4, 1, 0, 0, tzinfo=UTC)
    assert model.created_at == datetime(2026, 1, 1, 12, 0, tzinfo=UTC)
    assert model.updated_at == datetime(2026, 2, 1, 9, 30, tzinfo=UTC)
    assert model.version == 7


def test_to_model_collapses_absent_value_objects_to_null_columns() -> None:
    user = make_minimal_user()

    model = UserMapper.to_model(user)

    assert model.phone is None
    assert model.middle_name is None
    assert model.consent_version is None
    assert model.email_verified_at is None
    assert model.phone_verified_at is None
    assert model.locked_until is None
    assert model.deleted_at is None


def test_to_model_returns_an_unsaved_instance() -> None:
    # The mapper must never persist: a freshly built model is still "adding".
    model = UserMapper.to_model(make_minimal_user())

    assert model._state.adding is True


# ---------------------------------------------------------------------------
# ORM -> Domain (to_domain)
# ---------------------------------------------------------------------------


def test_to_domain_rehydrates_every_field_from_a_full_row() -> None:
    user_id = UserId.generate()
    model = UserModel(
        id=user_id.value,
        email="ivan.petrov@example.com",
        phone="+79991234567",
        first_name="Ivan",
        last_name="Petrov",
        middle_name="Sergeevich",
        locale="ru-RU",
        timezone="Europe/Moscow",
        password_algorithm="argon2id",
        password_hash=_ARGON2_HASH,
        consent_version="2026-01",
        email_verified_at=datetime(2026, 1, 2, 8, 0, tzinfo=UTC),
        phone_verified_at=datetime(2026, 1, 3, 8, 0, tzinfo=UTC),
        locked_until=datetime(2026, 3, 1, 0, 0, tzinfo=UTC),
        deleted_at=datetime(2026, 4, 1, 0, 0, tzinfo=UTC),
        created_at=datetime(2026, 1, 1, 12, 0, tzinfo=UTC),
        updated_at=datetime(2026, 2, 1, 9, 30, tzinfo=UTC),
        version=7,
    )

    user = UserMapper.to_domain(model)

    assert user.id == user_id
    assert user.email == Email("ivan.petrov@example.com")
    assert user.phone == PhoneNumber("+79991234567")
    assert user.full_name == FullName("Ivan", "Petrov", "Sergeevich")
    assert user.locale == Locale("ru-RU")
    assert user.timezone == Timezone("Europe/Moscow")
    assert user.password_hash == PasswordHash("argon2id", _ARGON2_HASH)
    assert user.consent_version == ConsentVersion("2026-01")
    assert user.email_verified_at == datetime(2026, 1, 2, 8, 0, tzinfo=UTC)
    assert user.phone_verified_at == datetime(2026, 1, 3, 8, 0, tzinfo=UTC)
    assert user.locked_until == datetime(2026, 3, 1, 0, 0, tzinfo=UTC)
    assert user.deleted_at == datetime(2026, 4, 1, 0, 0, tzinfo=UTC)
    assert user.created_at == datetime(2026, 1, 1, 12, 0, tzinfo=UTC)
    assert user.updated_at == datetime(2026, 2, 1, 9, 30, tzinfo=UTC)
    assert user.version == 7


def test_to_domain_maps_null_columns_to_none() -> None:
    model = UserModel(
        id=UserId.generate().value,
        email="anna@example.com",
        phone=None,
        first_name="Anna",
        last_name="Ivanova",
        middle_name=None,
        locale="ru-RU",
        timezone="UTC",
        password_algorithm="pbkdf2_sha256",
        password_hash=_PBKDF2_HASH,
        consent_version=None,
        email_verified_at=None,
        phone_verified_at=None,
        locked_until=None,
        deleted_at=None,
        created_at=datetime(2026, 1, 1, 0, 0, tzinfo=UTC),
        updated_at=datetime(2026, 1, 1, 0, 0, tzinfo=UTC),
        version=1,
    )

    user = UserMapper.to_domain(model)

    assert user.phone is None
    assert user.full_name.middle_name is None
    assert user.consent_version is None
    assert user.email_verified_at is None
    assert user.phone_verified_at is None
    assert user.locked_until is None
    assert user.deleted_at is None
    assert user.is_deleted() is False


# ---------------------------------------------------------------------------
# Round trip: Domain -> ORM -> Domain
# ---------------------------------------------------------------------------


def test_round_trip_preserves_a_full_aggregate() -> None:
    original = make_full_user()

    restored = UserMapper.to_domain(UserMapper.to_model(original))

    assert_users_equal(restored, original)


def test_round_trip_preserves_a_minimal_aggregate() -> None:
    original = make_minimal_user()

    restored = UserMapper.to_domain(UserMapper.to_model(original))

    assert_users_equal(restored, original)


# ---------------------------------------------------------------------------
# update_model
# ---------------------------------------------------------------------------


def test_update_model_overwrites_every_column_in_place() -> None:
    model = UserMapper.to_model(make_minimal_user())
    replacement = make_full_user()

    returned = UserMapper.update_model(model, replacement)

    assert returned is model  # mutated in place, not a new instance
    assert model.id == replacement.id.value
    assert model.email == replacement.email.value
    assert model.phone == "+79991234567"
    assert model.middle_name == "Sergeevich"
    assert model.consent_version == "2026-01"
    assert model.version == 7
    assert model.deleted_at == datetime(2026, 4, 1, 0, 0, tzinfo=UTC)


def test_update_model_clears_columns_when_value_objects_become_absent() -> None:
    model = UserMapper.to_model(make_full_user())
    minimal = make_minimal_user()

    UserMapper.update_model(model, minimal)

    assert model.phone is None
    assert model.middle_name is None
    assert model.consent_version is None
    assert model.email_verified_at is None
    assert model.locked_until is None
    assert model.deleted_at is None


def test_update_model_round_trips_back_to_the_source_aggregate() -> None:
    model = UserMapper.to_model(make_minimal_user())
    source = make_full_user()

    UserMapper.update_model(model, source)

    assert_users_equal(UserMapper.to_domain(model), source)


# ---------------------------------------------------------------------------
# Focused dimension tests
# ---------------------------------------------------------------------------


def test_uuid_identity_is_preserved_exactly() -> None:
    user = make_minimal_user()

    model = UserMapper.to_model(user)

    assert model.id == user.id.value
    assert UserMapper.to_domain(model).id.value == user.id.value


def test_version_is_preserved_verbatim_and_never_incremented() -> None:
    user = make_full_user()

    restored = UserMapper.to_domain(UserMapper.to_model(user))

    assert restored.version == 7


def test_soft_deleted_user_round_trips() -> None:
    user = User.rehydrate(
        user_id=UserId.generate(),
        email=Email("gone@example.com"),
        full_name=FullName("Gone", "User"),
        locale=Locale.default(),
        timezone=Timezone.utc(),
        password_hash=PasswordHash("argon2id", _ARGON2_HASH),
        created_at=datetime(2026, 1, 1, tzinfo=UTC),
        updated_at=datetime(2026, 5, 1, tzinfo=UTC),
        version=3,
        deleted_at=datetime(2026, 5, 1, tzinfo=UTC),
    )

    restored = UserMapper.to_domain(UserMapper.to_model(user))

    assert restored.is_deleted() is True
    assert restored.deleted_at == datetime(2026, 5, 1, tzinfo=UTC)


def test_locked_user_round_trips() -> None:
    locked_until = datetime(2026, 6, 1, tzinfo=UTC)
    user = User.rehydrate(
        user_id=UserId.generate(),
        email=Email("locked@example.com"),
        full_name=FullName("Locked", "User"),
        locale=Locale.default(),
        timezone=Timezone.utc(),
        password_hash=PasswordHash("argon2id", _ARGON2_HASH),
        created_at=datetime(2026, 1, 1, tzinfo=UTC),
        updated_at=datetime(2026, 1, 1, tzinfo=UTC),
        version=2,
        locked_until=locked_until,
    )

    restored = UserMapper.to_domain(UserMapper.to_model(user))

    assert restored.locked_until == locked_until
    assert restored.is_locked(now=datetime(2026, 5, 1, tzinfo=UTC)) is True


def test_email_verified_timestamp_round_trips() -> None:
    verified_at = datetime(2026, 1, 2, 8, 0, tzinfo=UTC)
    model = UserMapper.to_model(make_full_user())
    model.email_verified_at = verified_at

    user = UserMapper.to_domain(model)

    assert user.is_email_verified() is True
    assert user.email_verified_at == verified_at


def test_phone_verified_timestamp_round_trips() -> None:
    user = make_full_user()

    restored = UserMapper.to_domain(UserMapper.to_model(user))

    assert restored.is_phone_verified() is True
    assert restored.phone_verified_at == datetime(2026, 1, 3, 8, 0, tzinfo=UTC)


def test_consent_version_round_trips() -> None:
    user = make_full_user()

    restored = UserMapper.to_domain(UserMapper.to_model(user))

    assert restored.consent_version == ConsentVersion("2026-01")


def test_locale_round_trips() -> None:
    model = UserMapper.to_model(make_full_user())
    assert model.locale == "ru-RU"

    assert UserMapper.to_domain(model).locale == Locale("ru-RU")


def test_timezone_round_trips() -> None:
    model = UserMapper.to_model(make_full_user())
    assert model.timezone == "Europe/Moscow"

    assert UserMapper.to_domain(model).timezone == Timezone("Europe/Moscow")


def test_password_hash_maps_algorithm_and_digest_separately() -> None:
    user = make_full_user()

    model = UserMapper.to_model(user)
    assert model.password_algorithm == "argon2id"
    assert model.password_hash == _ARGON2_HASH

    restored = UserMapper.to_domain(model)
    assert restored.password_hash == PasswordHash("argon2id", _ARGON2_HASH)
    assert restored.password_hash.algorithm == "argon2id"
    assert restored.password_hash.encoded_hash == _ARGON2_HASH


def test_optional_phone_absent_round_trips_as_none() -> None:
    user = make_minimal_user()

    restored = UserMapper.to_domain(UserMapper.to_model(user))

    assert restored.phone is None
