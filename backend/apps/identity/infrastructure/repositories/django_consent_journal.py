"""``DjangoConsentJournal`` — the ORM-backed adapter for the consent journal.

The concrete implementation of the
:class:`~apps.identity.application.interfaces.ConsentJournal` port: the only
component permitted to touch ``UserConsentModel`` on behalf of the application layer.

Two rules shape everything here, and both come from the published policy rather than
from persistence taste:

* **Nothing is overwritten.** A new acceptance of a consent already held does not
  update the old row — it closes it as ``superseded`` and inserts a fresh ``active``
  one. So the answer to "what wording did they agree to in March, and when did it
  change?" stays in the table (LEGAL-001 §13.3).
* **A withdrawal is a stamp, not a delete.** ``withdrawn_at`` is set and the status
  moves to ``withdrawn``; the record stays. Processing performed while the consent was
  active was lawful, and the record is the evidence of that.

Grants are ordered by ``granted_at`` and, for equal instants, by ``id`` — the ids are
UUID v7, so that tiebreak is chronological rather than arbitrary.
"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from django.db import DatabaseError, transaction
from django.db.models import QuerySet

from apps.identity.application.dto import ConsentRecordDto
from apps.identity.infrastructure.models import UserConsentModel
from apps.identity.infrastructure.models.consent import ConsentStatus

from .exceptions import PersistenceError

__all__ = ["DjangoConsentJournal"]

#: Statuses that count as "the consent currently in force".
_ACTIVE_STATUSES = (ConsentStatus.GRANTED, ConsentStatus.ACTIVE)


def _to_dto(row: UserConsentModel) -> ConsentRecordDto:
    """Project one row into the application-layer DTO."""
    return ConsentRecordDto(
        id=str(row.id),
        consent_type=row.consent_type,
        version=row.consent_version,
        status=row.status,
        purpose=row.purpose,
        subject_participant_id=(str(row.subject_participant_id) if row.subject_participant_id is not None else None),
        granted_at=row.granted_at,
        expires_at=row.expires_at,
        withdrawn_at=row.withdrawn_at,
    )


class DjangoConsentJournal:
    """Django ORM adapter implementing the ``ConsentJournal`` port.

    Stateless and cheap to construct. Structurally satisfies the port without
    inheriting it, keeping the application core free of an edge pointing here.
    """

    def grant(
        self,
        *,
        user_id: str,
        consent_type: str,
        version: str,
        granted_at: datetime,
        purpose: str | None = None,
        subject_participant_id: str | None = None,
    ) -> ConsentRecordDto:
        """Supersede the previous active record of this type and insert a new one."""
        try:
            with transaction.atomic():
                self._active_rows(
                    user_id=user_id,
                    consent_type=consent_type,
                    subject_participant_id=subject_participant_id,
                ).update(status=ConsentStatus.SUPERSEDED, updated_at=granted_at)
                row = UserConsentModel.objects.create(
                    user_id=UUID(user_id),
                    consent_type=consent_type,
                    consent_version=version,
                    status=ConsentStatus.ACTIVE,
                    purpose=purpose,
                    subject_participant_id=subject_participant_id,
                    granted_at=granted_at,
                )
        except DatabaseError as exc:  # pragma: no cover - surfaced, never swallowed
            raise PersistenceError("Failed to record the consent.") from exc
        return _to_dto(row)

    def withdraw(
        self,
        *,
        user_id: str,
        consent_type: str,
        withdrawn_at: datetime,
        subject_participant_id: str | None = None,
    ) -> ConsentRecordDto | None:
        """Stamp the active record withdrawn. ``None`` when nothing was active."""
        try:
            with transaction.atomic():
                rows = self._active_rows(
                    user_id=user_id,
                    consent_type=consent_type,
                    subject_participant_id=subject_participant_id,
                )
                row = rows.order_by("-granted_at", "-id").first()
                if row is None:
                    return None
                row.status = ConsentStatus.WITHDRAWN
                row.withdrawn_at = withdrawn_at
                row.updated_at = withdrawn_at
                row.save(update_fields=["status", "withdrawn_at", "updated_at"])
        except DatabaseError as exc:  # pragma: no cover - surfaced, never swallowed
            raise PersistenceError("Failed to withdraw the consent.") from exc
        return _to_dto(row)

    def list_for_user(self, *, user_id: str, include_history: bool = False) -> tuple[ConsentRecordDto, ...]:
        """The account's active consents, or its whole journal newest-first."""
        try:
            query = UserConsentModel.objects.filter(user_id=UUID(user_id), deleted_at__isnull=True)
            if not include_history:
                query = query.filter(status__in=_ACTIVE_STATUSES)
            rows = list(query.order_by("-granted_at", "-id"))
        except DatabaseError as exc:  # pragma: no cover - surfaced, never swallowed
            raise PersistenceError("Failed to read the consent journal.") from exc
        return tuple(_to_dto(row) for row in rows)

    def _active_rows(
        self,
        *,
        user_id: str,
        consent_type: str,
        subject_participant_id: str | None,
    ) -> QuerySet[UserConsentModel]:
        """The rows currently in force for one (account, consent, participant) triple.

        A consent about a child is scoped to that child: accepting for a second
        participant must not supersede the first one's record, so the participant is
        part of the key rather than an attribute of it.
        """
        return UserConsentModel.objects.filter(
            user_id=UUID(user_id),
            consent_type=consent_type,
            subject_participant_id=subject_participant_id,
            status__in=_ACTIVE_STATUSES,
            deleted_at__isnull=True,
        )
