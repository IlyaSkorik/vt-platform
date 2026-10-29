"""``DjangoPerformanceSchedule`` — the one place Programs writes into Applications.

Everywhere else this context only reads its neighbours (see
:mod:`~apps.programs.infrastructure.acl.performance_catalog`). This adapter is the
exception, and it exists because ``SCHEDULED`` is a fact about the running order:
an act holds a slot or it does not, and the running order lives here.

It goes through the :class:`~apps.applications.domain.entities.Submission`
aggregate rather than writing the column, even though an ``UPDATE`` would be one
line. The aggregate owns which transitions are legal and appends the status history
every other screen reads off; a direct write would be a second, quieter copy of
those rules, and the first thing it would lose is the history — which is exactly
what makes "когда номер попал в программу" answerable at all.

Failures are swallowed per act, deliberately. The caller has already saved the
programme; the slot is real whether or not the status caught up. Refusing the whole
request here would leave the organizer looking at a programme that did save, told
it did not — and the next edit of that programme re-drives the same diff, so a
status that fell behind corrects itself rather than staying wrong forever.
"""

from __future__ import annotations

import logging
import uuid
from collections.abc import Sequence
from datetime import UTC, datetime

from apps.applications.domain.value_objects import SubmissionId
from apps.applications.infrastructure.repositories.django_submission_repository import DjangoSubmissionRepository

__all__ = ["DjangoPerformanceSchedule"]

_logger = logging.getLogger(__name__)


class DjangoPerformanceSchedule:
    """Applications ACL implementing the ``PerformanceSchedule`` port."""

    def __init__(self) -> None:
        self._submissions = DjangoSubmissionRepository()

    def mark_scheduled(self, submission_ids: Sequence[uuid.UUID]) -> None:
        """These acts now hold a slot in a running order."""
        self._apply(submission_ids, scheduled=True)

    def mark_unscheduled(self, submission_ids: Sequence[uuid.UUID]) -> None:
        """These acts hold no slot in any programme any more."""
        self._apply(submission_ids, scheduled=False)

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    def _apply(self, submission_ids: Sequence[uuid.UUID], *, scheduled: bool) -> None:
        if not submission_ids:
            return
        now = datetime.now(UTC)
        for submission_id in submission_ids:
            try:
                submission = self._submissions.get(SubmissionId(submission_id))
                if submission is None:
                    continue
                # Both aggregate methods are no-ops when the status is already what
                # is being asked for, so a diff that overlaps a previous one costs a
                # read and nothing else — no spurious history entry, no version bump.
                events = submission.schedule(now=now) if scheduled else submission.unschedule(now=now)
                if not events:
                    continue
                self._submissions.save(submission)
            except Exception:  # see the module docstring: a lagging status self-corrects
                _logger.warning(
                    "Could not mark submission %s as %s",
                    submission_id,
                    "scheduled" if scheduled else "unscheduled",
                    exc_info=True,
                )
