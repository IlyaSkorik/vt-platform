"""Diploma registry use cases.

The application service orchestrates the ports: it snapshots a submission into a
new, self-contained diploma, and reads the registry back. No PDF, no bulk
generation, no verification — that is later work.
"""

from __future__ import annotations

import secrets
import uuid
from datetime import datetime

from apps.diplomas.application.interfaces import DiplomaRepository, DiplomaSnapshotSource
from apps.diplomas.domain.entities import Diploma
from apps.diplomas.domain.exceptions import (
    DiplomaNotFoundError,
    SubmissionNotFoundError,
    TemplateNotFoundError,
)

__all__ = ["DiplomaService"]

#: Bytes of entropy behind a verification token (~43 url-safe chars). Unguessable.
_TOKEN_BYTES = 32


class DiplomaService:
    """Create diplomas from submissions and read the registry."""

    def __init__(self, *, repository: DiplomaRepository, snapshots: DiplomaSnapshotSource) -> None:
        self._repository = repository
        self._snapshots = snapshots

    def create_diploma(self, *, submission_id: uuid.UUID, template_id: uuid.UUID, now: datetime) -> Diploma:
        """Snapshot a submission into a new ``DRAFT`` diploma with a permanent
        number and verification token.

        A missing award degree is normal and does not block creation. Raises
        :class:`TemplateNotFoundError` / :class:`SubmissionNotFoundError`.
        """
        if not self._snapshots.template_exists(template_id):
            raise TemplateNotFoundError("Template was not found.")
        built = self._snapshots.build(submission_id)
        if built is None:
            raise SubmissionNotFoundError("Submission was not found.")

        diploma = Diploma.create(
            diploma_id=self._repository.new_id(),
            number=self._repository.next_number(),
            verification_token=secrets.token_urlsafe(_TOKEN_BYTES),
            competition_id=built.competition_id,
            submission_id=submission_id,
            template_id=template_id,
            snapshot=built.snapshot,
            now=now,
        )
        self._repository.add(diploma)
        return diploma

    def get_diploma(self, diploma_id: uuid.UUID) -> Diploma:
        """Load one diploma. Raises :class:`DiplomaNotFoundError` if unknown."""
        diploma = self._repository.get(diploma_id)
        if diploma is None:
            raise DiplomaNotFoundError("Diploma was not found.")
        return diploma

    def list_for_competition(self, competition_id: uuid.UUID) -> list[Diploma]:
        """The competition's diploma registry, newest first."""
        return self._repository.list_by_competition(competition_id)
