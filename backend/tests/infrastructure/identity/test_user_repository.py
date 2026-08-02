"""Integration tests for :class:`DjangoUserRepository`.

These exercise the repository as the real persistence adapter it is: **real
Django ORM against real PostgreSQL, no mocks** (ARCH-001 §28.2). The database is
repointed at PostgreSQL by ``tests/infrastructure/conftest.py``; every test that
touches it is marked ``django_db``.

Coverage:

* every port method (``get`` / ``get_by_email`` / ``get_by_phone`` /
  ``exists`` / ``exists_by_email`` / ``exists_by_phone`` / ``save`` / ``delete``);
* the domain⇄persistence round trip (a saved aggregate reloads field-for-field);
* insert-vs-update dispatch in ``save`` and full-field updates;
* optimistic locking — a stale write raises :class:`ConcurrencyConflictError`;
* soft delete — ``delete`` stamps ``deleted_at``, never removes the row, and frees
  the email/phone for reuse; it is idempotent and safe on an absent row;
* active-only semantics of the email/phone lookups;
* exception translation — a uniqueness clash surfaces as
  :class:`IntegrityViolationError`, never a raw Django ``IntegrityError``;
* structural conformance to the ``UserRepository`` port.
"""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from apps.identity.application.interfaces import UserRepository
from apps.identity.domain.entities import User
from apps.identity.domain.value_objects import (
    Email,
    FullName,
    Locale,
    PasswordHash,
    PhoneNumber,
    Timezone,
    UserId,
)
from apps.identity.infrastructure.models import UserModel
from apps.identity.infrastructure.repositories import (
    ConcurrencyConflictError,
    DjangoUserRepository,
    IntegrityViolationError,
)

_ARGON2_HASH = "$argon2id$v=19$m=65536,t=3,p=4$c29tZXNhbHQ$c29tZWhhc2h2YWx1ZQ"
_NOW = datetime(2026, 7, 7, 12, 0, tzinfo=UTC)


# ---------------------------------------------------------------------------
# Builders / fixtures
# ---------------------------------------------------------------------------


def make_user(
    *,
    email: str = "ivan.petrov@example.com",
    phone: str | None = "+375291234567",
) -> User:
    """A freshly-registered aggregate (version 1, active, unverified)."""
    user, _events = User.register(
        user_id=UserId.generate(),
        email=Email(email),
        full_name=FullName(first_name="Ivan", last_name="Petrov", middle_name="Sergeevich"),
        password_hash=PasswordHash(algorithm="argon2id", encoded_hash=_ARGON2_HASH),
        now=_NOW,
        phone=PhoneNumber(phone) if phone is not None else None,
    )
    return user


@pytest.fixture
def repository() -> DjangoUserRepository:
    return DjangoUserRepository()


# ---------------------------------------------------------------------------
# Port conformance
# ---------------------------------------------------------------------------


def test_repository_structurally_satisfies_the_port() -> None:
    assert isinstance(DjangoUserRepository(), UserRepository)


# ---------------------------------------------------------------------------
# save: insert
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_save_inserts_a_new_user(repository: DjangoUserRepository) -> None:
    user = make_user()

    repository.save(user)

    assert UserModel.objects.filter(pk=user.id.value).exists()


@pytest.mark.django_db
def test_save_then_get_round_trips_every_field(repository: DjangoUserRepository) -> None:
    user = make_user()

    repository.save(user)
    loaded = repository.get(user.id)

    assert loaded is not None
    assert loaded == user  # identity
    assert loaded.email == user.email
    assert loaded.phone == user.phone
    assert loaded.full_name == user.full_name
    assert loaded.locale == user.locale
    assert loaded.timezone == user.timezone
    assert loaded.password_hash == user.password_hash
    assert loaded.created_at == user.created_at
    assert loaded.updated_at == user.updated_at
    assert loaded.version == user.version
    assert loaded.is_deleted() is False


@pytest.mark.django_db
def test_save_returns_domain_user_not_orm_model(repository: DjangoUserRepository) -> None:
    user = make_user()
    repository.save(user)

    loaded = repository.get(user.id)

    assert isinstance(loaded, User)
    assert not isinstance(loaded, UserModel)


# ---------------------------------------------------------------------------
# save: update
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_save_updates_an_existing_user(repository: DjangoUserRepository) -> None:
    # One business operation per save is the unit of work: each domain method
    # advances ``version`` by exactly one, matching the stored row before the write.
    user = make_user()
    repository.save(user)

    reloaded = repository.get(user.id)
    assert reloaded is not None
    reloaded.change_locale(Locale("en-US"), now=_NOW)
    repository.save(reloaded)

    again = repository.get(user.id)
    assert again is not None
    again.change_timezone(Timezone("Europe/Moscow"), now=_NOW)
    repository.save(again)

    fresh = repository.get(user.id)
    assert fresh is not None
    assert fresh.locale == Locale("en-US")
    assert fresh.timezone == Timezone("Europe/Moscow")
    assert fresh.version == 3  # 1 (insert) -> 2 (locale) -> 3 (timezone)
    assert UserModel.objects.filter(pk=user.id.value).count() == 1  # update, not insert


# ---------------------------------------------------------------------------
# Optimistic locking
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_stale_write_raises_concurrency_conflict(repository: DjangoUserRepository) -> None:
    user = make_user()
    repository.save(user)

    # Two independent reads of the same version.
    first = repository.get(user.id)
    second = repository.get(user.id)
    assert first is not None and second is not None

    first.change_locale(Locale("en-US"), now=_NOW)
    repository.save(first)  # advances the stored version

    second.change_timezone(Timezone("Europe/Moscow"), now=_NOW)  # built from the stale read
    with pytest.raises(ConcurrencyConflictError):
        repository.save(second)


@pytest.mark.django_db
def test_stored_row_is_unchanged_after_a_conflict(repository: DjangoUserRepository) -> None:
    user = make_user()
    repository.save(user)
    winner = repository.get(user.id)
    loser = repository.get(user.id)
    assert winner is not None and loser is not None

    winner.change_locale(Locale("en-US"), now=_NOW)
    repository.save(winner)
    loser.change_locale(Locale("en-US"), now=_NOW)
    with pytest.raises(ConcurrencyConflictError):
        repository.save(loser)

    fresh = repository.get(user.id)
    assert fresh is not None
    assert fresh.version == 2  # only the winner's write landed


# ---------------------------------------------------------------------------
# get / exists
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_get_returns_none_when_absent(repository: DjangoUserRepository) -> None:
    assert repository.get(UserId.generate()) is None


@pytest.mark.django_db
def test_get_by_email_returns_the_user(repository: DjangoUserRepository) -> None:
    user = make_user()
    repository.save(user)

    found = repository.get_by_email(user.email)

    assert found is not None
    assert found.id == user.id


@pytest.mark.django_db
def test_get_by_email_returns_none_when_absent(repository: DjangoUserRepository) -> None:
    assert repository.get_by_email(Email("nobody@example.com")) is None


@pytest.mark.django_db
def test_get_by_phone_returns_the_user(repository: DjangoUserRepository) -> None:
    user = make_user()
    repository.save(user)

    found = repository.get_by_phone(PhoneNumber("+375291234567"))

    assert found is not None
    assert found.id == user.id


@pytest.mark.django_db
def test_get_by_phone_returns_none_when_absent(repository: DjangoUserRepository) -> None:
    assert repository.get_by_phone(PhoneNumber("+375291234567")) is None


@pytest.mark.django_db
def test_exists_reflects_presence(repository: DjangoUserRepository) -> None:
    user = make_user()
    assert repository.exists(user.id) is False

    repository.save(user)

    assert repository.exists(user.id) is True


@pytest.mark.django_db
def test_exists_by_email_and_phone(repository: DjangoUserRepository) -> None:
    user = make_user()
    repository.save(user)

    assert repository.exists_by_email(user.email) is True
    assert repository.exists_by_phone(PhoneNumber("+375291234567")) is True
    assert repository.exists_by_email(Email("nobody@example.com")) is False
    assert repository.exists_by_phone(PhoneNumber("+375447654321")) is False


# ---------------------------------------------------------------------------
# Soft delete
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_delete_soft_deletes_without_removing_the_row(repository: DjangoUserRepository) -> None:
    user = make_user()
    repository.save(user)

    repository.delete(user)

    # Row is retained...
    assert UserModel.objects.filter(pk=user.id.value).exists()
    row = UserModel.objects.get(pk=user.id.value)
    assert row.deleted_at is not None
    # ...and reachable by id, carrying the deleted state...
    reloaded = repository.get(user.id)
    assert reloaded is not None
    assert reloaded.is_deleted() is True
    # ...but no longer surfaced by the active-only lookups.
    assert repository.get_by_email(user.email) is None
    assert repository.exists_by_email(user.email) is False


@pytest.mark.django_db
def test_delete_uses_aggregate_timestamp_when_soft_deleted(
    repository: DjangoUserRepository,
) -> None:
    user = make_user()
    repository.save(user)
    reloaded = repository.get(user.id)
    assert reloaded is not None
    deleted_at = datetime(2026, 8, 1, 9, 0, tzinfo=UTC)
    reloaded.soft_delete(now=deleted_at)

    repository.delete(reloaded)

    row = UserModel.objects.get(pk=user.id.value)
    assert row.deleted_at == deleted_at


@pytest.mark.django_db
def test_delete_is_idempotent(repository: DjangoUserRepository) -> None:
    user = make_user()
    repository.save(user)

    repository.delete(user)
    repository.delete(user)  # must not raise

    assert UserModel.objects.filter(pk=user.id.value).count() == 1


@pytest.mark.django_db
def test_delete_on_absent_user_is_a_noop(repository: DjangoUserRepository) -> None:
    user = make_user()

    repository.delete(user)  # never saved; must not raise

    assert UserModel.objects.filter(pk=user.id.value).exists() is False


@pytest.mark.django_db
def test_email_is_reusable_after_soft_delete(repository: DjangoUserRepository) -> None:
    first = make_user(email="shared@example.com", phone="+375291234567")
    repository.save(first)
    repository.delete(first)

    second = make_user(email="shared@example.com", phone="+375291234567")
    repository.save(second)  # active uniqueness frees the address for reuse

    found = repository.get_by_email(Email("shared@example.com"))
    assert found is not None
    assert found.id == second.id


# ---------------------------------------------------------------------------
# Exception translation
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_duplicate_active_email_raises_integrity_violation(
    repository: DjangoUserRepository,
) -> None:
    repository.save(make_user(email="dup@example.com", phone="+375291234567"))
    clashing = make_user(email="dup@example.com", phone="+375291234567")

    with pytest.raises(IntegrityViolationError):
        repository.save(clashing)


@pytest.mark.django_db
def test_duplicate_active_phone_raises_integrity_violation(
    repository: DjangoUserRepository,
) -> None:
    repository.save(make_user(email="a@example.com", phone="+375291234567"))
    clashing = make_user(email="b@example.com", phone="+375291234567")

    with pytest.raises(IntegrityViolationError):
        repository.save(clashing)
