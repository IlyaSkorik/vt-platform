"""The ``Diploma`` aggregate root — a self-contained, issued document.

A diploma is deliberately independent of the submission and competition it was
created from: at creation it captures a :class:`DiplomaSnapshot` of the resolved
data, its own permanent :attr:`number`, and a :attr:`verification_token` for a
future authenticity page. Nothing that later changes in the submission or the
competition may alter an existing diploma.

Framework-free (no Django). Persistence lives in the infrastructure mapper.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, replace
from datetime import datetime

from apps.diplomas.domain.value_objects import AwardSnapshot, DiplomaSnapshot, DiplomaStatus

__all__ = ["Diploma"]


@dataclass(frozen=True, slots=True)
class Diploma:
    """A single diploma. Immutable value semantics; transitions return a new one."""

    id: uuid.UUID
    number: str
    verification_token: str
    competition_id: uuid.UUID
    submission_id: uuid.UUID
    template_id: uuid.UUID
    status: DiplomaStatus
    snapshot: DiplomaSnapshot
    created_at: datetime
    updated_at: datetime
    print_pdf_path: str | None = None
    official_pdf_path: str | None = None
    issued_at: datetime | None = None
    version: int = 1

    @classmethod
    def create(
        cls,
        *,
        diploma_id: uuid.UUID,
        number: str,
        verification_token: str,
        competition_id: uuid.UUID,
        submission_id: uuid.UUID,
        template_id: uuid.UUID,
        snapshot: DiplomaSnapshot,
        now: datetime,
    ) -> Diploma:
        """Create a fresh diploma in ``DRAFT``.

        A missing ``award.degree`` is expected and valid: the diploma is often
        created (and, offline, printed) before the jury has decided.
        """
        return cls(
            id=diploma_id,
            number=number,
            verification_token=verification_token,
            competition_id=competition_id,
            submission_id=submission_id,
            template_id=template_id,
            status=DiplomaStatus.DRAFT,
            snapshot=snapshot,
            created_at=now,
            updated_at=now,
            print_pdf_path=None,
            official_pdf_path=None,
            issued_at=None,
            version=1,
        )

    @classmethod
    def rehydrate(
        cls,
        *,
        diploma_id: uuid.UUID,
        number: str,
        verification_token: str,
        competition_id: uuid.UUID,
        submission_id: uuid.UUID,
        template_id: uuid.UUID,
        status: DiplomaStatus,
        snapshot: DiplomaSnapshot,
        created_at: datetime,
        updated_at: datetime,
        print_pdf_path: str | None,
        official_pdf_path: str | None,
        issued_at: datetime | None,
        version: int,
    ) -> Diploma:
        """Reconstruct from persistence (no validation, no state change)."""
        return cls(
            id=diploma_id,
            number=number,
            verification_token=verification_token,
            competition_id=competition_id,
            submission_id=submission_id,
            template_id=template_id,
            status=status,
            snapshot=snapshot,
            created_at=created_at,
            updated_at=updated_at,
            print_pdf_path=print_pdf_path,
            official_pdf_path=official_pdf_path,
            issued_at=issued_at,
            version=version,
        )

    @property
    def degree(self) -> str | None:
        """The awarded degree, or ``None`` while it is still unknown."""
        return self.snapshot.award.degree

    def with_print_pdf(self, path: str, *, now: datetime) -> Diploma:
        """Record the generated print PDF (pre-ceremony copy) and mark GENERATED."""
        return replace(
            self,
            print_pdf_path=path,
            status=DiplomaStatus.GENERATED,
            updated_at=now,
            version=self.version + 1,
        )

    def with_degree(self, degree: str | None, *, now: datetime) -> Diploma:
        """Return a copy whose award degree is set — the only snapshot field the
        organizer fills in after the fact (offline: printed later as "Степень").

        The number, token and every other snapshot value stay frozen."""
        snapshot = replace(self.snapshot, award=AwardSnapshot(degree=degree))
        return replace(self, snapshot=snapshot, updated_at=now, version=self.version + 1)
