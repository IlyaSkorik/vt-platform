"""``DjangoUserRepository`` — the ORM-backed adapter for the ``User`` aggregate.

This is the concrete implementation of the
:class:`~apps.identity.application.interfaces.UserRepository` port (ARCH-001
§7.2, §7.3): the **single** component permitted to touch the Django ORM on behalf
of the ``User`` aggregate. It is the gate between the framework-free application
core and the database — use cases speak only ``User`` and value objects, and this
adapter turns those into ``UserModel`` queries and back via :class:`UserMapper`.

What lives here, and nowhere else (ARCH-001 §14):

* querying the ORM (``UserModel.objects`` …);
* opening a :func:`~django.db.transaction.atomic` block when a read-then-write
  must be consistent;
* invoking :class:`UserMapper` to cross the domain⇄persistence boundary;
* translating every Django exception into a
  :mod:`~apps.identity.infrastructure.repositories.exceptions` type so no
  framework error leaks outward.

What deliberately does **not** live here (those belong to the domain/application
layers): validating input, applying business policies, publishing domain events,
or invoking handlers. The repository only loads and stores; it never decides.

**Return contract.** Every method returns a domain :class:`User` (or ``None`` /
``bool``); a ``UserModel`` never escapes this class. Lookups report absence as
``None`` rather than raising, matching the port so the *use case* decides whether
a missing user is an error.

**Optimistic concurrency.** The aggregate owns its ``version`` and bumps it once
per mutation (``User._touch``). :meth:`save` writes conditionally on the
*previous* version, so a write built from a stale read updates zero rows and is
surfaced as :class:`ConcurrencyConflictError` instead of silently clobbering a
concurrent change.

**Soft delete.** :meth:`delete` never issues ``DELETE``; it stamps ``deleted_at``
so the row is retained for audit and the email/phone become reusable (the partial
unique constraints cover active rows only). Hard erasure is out of scope for this
adapter.

**No N+1.** The ``User`` aggregate maps to a single flat table with no related
rows to walk, so neither ``select_related`` nor ``prefetch_related`` is justified
here — adding either would fetch columns nothing reads. Every method issues at
most a single round trip (two only where a write must first classify insert vs.
conflict, inside one transaction).
"""

from __future__ import annotations

from django.db import DatabaseError, IntegrityError, transaction
from django.db.models import F
from django.utils import timezone

from apps.identity.domain.entities import User
from apps.identity.domain.value_objects import Email, PhoneNumber, UserId
from apps.identity.infrastructure.mappers import UserMapper
from apps.identity.infrastructure.models import UserModel

from .exceptions import ConcurrencyConflictError, IntegrityViolationError, PersistenceError

__all__ = ["DjangoUserRepository"]


class DjangoUserRepository:
    """Django ORM adapter implementing the ``UserRepository`` port.

    Stateless and cheap to construct: it holds no per-request state and may be
    instantiated per use case or shared. Structurally satisfies
    :class:`~apps.identity.application.interfaces.UserRepository` (it does not
    inherit the ``Protocol`` — the port is structural by design, keeping the
    application core free of a dependency edge pointing at this module).
    """

    # ------------------------------------------------------------------
    # Reads
    # ------------------------------------------------------------------

    def get(self, user_id: UserId) -> User | None:
        """Return the user with ``user_id`` (deleted or not), or ``None``.

        Looks up by primary key, which is globally unique regardless of
        soft-delete state; the returned aggregate carries its own ``deleted_at``
        so the caller can decide what an inactive account means.
        """
        try:
            model = UserModel.objects.get(pk=user_id.value)
        except UserModel.DoesNotExist:
            return None
        except DatabaseError as exc:  # pragma: no cover - defensive
            raise PersistenceError(f"Failed to load user {user_id}.") from exc
        return UserMapper.to_domain(model)

    def get_by_email(self, email: Email) -> User | None:
        """Return the **active** user whose current email is ``email``, or ``None``.

        Restricted to non-deleted rows: the ``identity_user_unique_active_email``
        partial constraint guarantees at most one match among active accounts,
        while a soft-deleted account may share the address with a later signup.
        """
        try:
            model = UserModel.objects.get(email=email.value, deleted_at__isnull=True)
        except UserModel.DoesNotExist:
            return None
        except DatabaseError as exc:  # pragma: no cover - defensive
            raise PersistenceError(f"Failed to load user by email {email.masked()}.") from exc
        return UserMapper.to_domain(model)

    def get_by_phone(self, phone: PhoneNumber) -> User | None:
        """Return the **active** user whose current phone is ``phone``, or ``None``.

        Restricted to non-deleted rows for the same reason as
        :meth:`get_by_email`: uniqueness is enforced only among active accounts.
        """
        try:
            model = UserModel.objects.get(phone=phone.value, deleted_at__isnull=True)
        except UserModel.DoesNotExist:
            return None
        except DatabaseError as exc:  # pragma: no cover - defensive
            raise PersistenceError("Failed to load user by phone.") from exc
        return UserMapper.to_domain(model)

    def exists(self, user_id: UserId) -> bool:
        """Whether a user row with ``user_id`` is stored (deleted or not)."""
        try:
            return UserModel.objects.filter(pk=user_id.value).exists()
        except DatabaseError as exc:  # pragma: no cover - defensive
            raise PersistenceError(f"Failed to check existence of user {user_id}.") from exc

    def exists_by_email(self, email: Email) -> bool:
        """Whether an **active** user currently uses ``email`` (uniqueness pre-check)."""
        try:
            return UserModel.objects.filter(email=email.value, deleted_at__isnull=True).exists()
        except DatabaseError as exc:  # pragma: no cover - defensive
            raise PersistenceError(f"Failed to check email {email.masked()}.") from exc

    def exists_by_phone(self, phone: PhoneNumber) -> bool:
        """Whether an **active** user currently uses ``phone`` (uniqueness pre-check)."""
        try:
            return UserModel.objects.filter(phone=phone.value, deleted_at__isnull=True).exists()
        except DatabaseError as exc:  # pragma: no cover - defensive
            raise PersistenceError("Failed to check phone.") from exc

    # ------------------------------------------------------------------
    # Writes
    # ------------------------------------------------------------------

    def save(self, user: User) -> None:
        """Persist ``user`` (insert or update), honouring its optimistic ``version``.

        The aggregate has already advanced its ``version`` for the mutation being
        saved. The unit of work is **one business operation per save**: every
        domain method bumps ``version`` exactly once (``User._touch``), so a loaded
        aggregate is at most one version ahead of its row when persisted. The write
        is therefore conditional on the *previous* version:

        * **Update** — ``UPDATE … WHERE id = ? AND version = current - 1`` maps a
          stale read to zero affected rows. Zero rows with the row present means a
          concurrent writer moved the version on: raise
          :class:`ConcurrencyConflictError`. This is a true lock-free optimistic
          check (no ``SELECT … FOR UPDATE``).
        * **Insert** — a freshly ``register``-ed aggregate (its predecessor version
          matches no row) is inserted, keyed by its domain-assigned UUID.

        Both branches run in one :func:`~django.db.transaction.atomic` block so the
        classify-then-write is consistent under concurrency.
        """
        model = UserMapper.to_model(user)
        values = self._column_values(model)
        update_values = {name: value for name, value in values.items() if name != "id"}
        previous_version = user.version - 1
        try:
            with transaction.atomic():
                updated = UserModel.objects.filter(pk=user.id.value, version=previous_version).update(**update_values)
                if updated:
                    return
                if UserModel.objects.filter(pk=user.id.value).exists():
                    raise ConcurrencyConflictError(f"User {user.id} was modified concurrently; expected version {previous_version}.")
                UserModel.objects.create(**values)
        except IntegrityError as exc:
            raise IntegrityViolationError(f"Failed to persist user {user.id}.") from exc
        except DatabaseError as exc:  # pragma: no cover - defensive
            raise PersistenceError(f"Failed to persist user {user.id}.") from exc

    def delete(self, user: User) -> None:
        """Soft-delete ``user``: stamp ``deleted_at`` on the row; never remove it.

        Rows are retained for audit and to free the email/phone for reuse (the
        unique constraints cover active rows only). The stamp is taken from the
        aggregate when the caller already transitioned it via ``User.soft_delete``
        (the normal flow); otherwise the current instant is used so a bare
        ``delete(user)`` is still honoured. ``version`` is advanced so the marker
        participates in optimistic concurrency.

        Only an **active** row is affected. Zero rows affected with the row present
        means it is already deleted — an idempotent no-op; with no row present it
        never existed — also a no-op (there is nothing to erase).
        """
        deleted_at = user.deleted_at or timezone.now()
        try:
            with transaction.atomic():
                UserModel.objects.filter(pk=user.id.value, deleted_at__isnull=True).update(deleted_at=deleted_at, version=F("version") + 1)
        except IntegrityError as exc:  # pragma: no cover - defensive
            raise IntegrityViolationError(f"Failed to delete user {user.id}.") from exc
        except DatabaseError as exc:  # pragma: no cover - defensive
            raise PersistenceError(f"Failed to delete user {user.id}.") from exc

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    @staticmethod
    def _column_values(model: UserModel) -> dict[str, object]:
        """Flatten a mapped ``UserModel`` into its concrete column values.

        Reads the values the mapper already projected onto ``model`` so the
        insert/update paths write exactly the columns the aggregate owns, without
        the repository re-deriving them from the domain object.
        """
        return {field.attname: getattr(model, field.attname) for field in UserModel._meta.concrete_fields}
