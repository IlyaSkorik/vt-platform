"""``UserMapper`` — the Anti-Corruption Layer between the ``User`` aggregate and its ORM row.

This mapper is the **single** component permitted to know both the framework-free
domain (:class:`apps.identity.domain.entities.User` and its value objects) and the
Django persistence model (:class:`apps.identity.infrastructure.models.UserModel`).
Keeping that knowledge in one place is what lets the domain stay ignorant of the
ORM and the ORM stay ignorant of business rules (ARCH-001 §4.1, §7.2, §14).

Its whole job is translation:

* :meth:`UserMapper.to_domain` — ORM row → aggregate, via :meth:`User.rehydrate`
  (no re-validation, no events, ``version`` preserved verbatim).
* :meth:`UserMapper.to_model` — aggregate → a **new, unsaved** ``UserModel``.
* :meth:`UserMapper.update_model` — project an aggregate onto an **existing**
  ``UserModel``, preserving its primary key for an in-place update.

What it deliberately does **not** do: it never validates business rules, never
runs a domain workflow, never publishes or reconstructs domain events, never
touches a repository, never issues a query, and never calls ``save()``,
``full_clean()``, or any manager/queryset. Persistence timing and event dispatch
belong to the repository and application layers. Timestamps are copied verbatim —
the aggregate owns those instants (see ``BasePersistenceModel``).
"""

from __future__ import annotations

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
from apps.identity.infrastructure.models import UserModel

__all__ = ["UserMapper"]


class UserMapper:
    """Bidirectional translator between the ``User`` aggregate and ``UserModel``.

    Stateless: every method is a pure, side-effect-free projection, so the mapper
    holds no state and can be used as a namespace of static methods.
    """

    @staticmethod
    def to_domain(model: UserModel) -> User:
        """Reconstruct the ``User`` aggregate from a persisted row.

        Delegates to :meth:`User.rehydrate`, which re-runs no invariant and emits
        no events: the stored state was already valid when written. Each column is
        wrapped back into its value object; ``NULL`` columns (phone, consent, the
        verification and lock/delete timestamps) map to ``None``.
        """
        return User.rehydrate(
            user_id=UserId.from_uuid(model.id),
            email=Email(model.email),
            full_name=FullName(
                first_name=model.first_name,
                last_name=model.last_name,
                middle_name=model.middle_name,
            ),
            locale=Locale(model.locale),
            timezone=Timezone(model.timezone),
            password_hash=PasswordHash(
                algorithm=model.password_algorithm,
                encoded_hash=model.password_hash,
            ),
            created_at=model.created_at,
            updated_at=model.updated_at,
            version=model.version,
            phone=PhoneNumber(model.phone) if model.phone is not None else None,
            consent_version=(
                ConsentVersion(model.consent_version) if model.consent_version is not None else None
            ),
            email_verified_at=model.email_verified_at,
            phone_verified_at=model.phone_verified_at,
            locked_until=model.locked_until,
            deleted_at=model.deleted_at,
        )

    @staticmethod
    def to_model(entity: User) -> UserModel:
        """Build a brand-new, **unsaved** ``UserModel`` from an aggregate.

        Constructs the instance only; persisting it is the repository's concern.
        The primary key is carried over from the aggregate's identity so the row is
        insertable with a stable, domain-assigned UUID.
        """
        return UserModel(**UserMapper._to_columns(entity))

    @staticmethod
    def update_model(model: UserModel, entity: User) -> UserModel:
        """Project ``entity`` onto an existing ``model`` in place, returning it.

        Overwrites every mapped column (identity included, so the row stays keyed to
        the aggregate) without saving. Used by the repository to apply an update to
        a row it has already fetched, preserving its ORM state for the write.
        """
        for field, value in UserMapper._to_columns(entity).items():
            setattr(model, field, value)
        return model

    @staticmethod
    def _to_columns(entity: User) -> dict[str, object]:
        """Flatten an aggregate into the ``UserModel`` column values.

        The shared Domain → ORM projection behind :meth:`to_model` and
        :meth:`update_model`. Value objects are unwrapped to their primitives and
        optional value objects collapse to ``None`` columns.
        """
        phone = entity.phone
        consent = entity.consent_version
        return {
            "id": entity.id.value,
            "email": entity.email.value,
            "phone": phone.value if phone is not None else None,
            "first_name": entity.full_name.first_name,
            "last_name": entity.full_name.last_name,
            "middle_name": entity.full_name.middle_name,
            "locale": entity.locale.value,
            "timezone": entity.timezone.value,
            "password_algorithm": entity.password_hash.algorithm,
            "password_hash": entity.password_hash.encoded_hash,
            "consent_version": consent.value if consent is not None else None,
            "email_verified_at": entity.email_verified_at,
            "phone_verified_at": entity.phone_verified_at,
            "locked_until": entity.locked_until,
            "deleted_at": entity.deleted_at,
            "created_at": entity.created_at,
            "updated_at": entity.updated_at,
            "version": entity.version,
        }
