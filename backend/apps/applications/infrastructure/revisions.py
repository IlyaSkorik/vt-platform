"""Recording, and later replaying, the edits an applicant makes to a placed order.

The ``note_*`` functions are called from the API edge right after a mutation the
applicant asked for succeeded. They decide whether the change is even worth recording
(only an order the organizer has already seen qualifies) and write one row. **They
never raise**: journalling is a courtesy to the organizer, and an applicant's edit
must not fail because a courtesy did.

Why the edge and not a handler: an edit to a submitted order violates nothing, so
no aggregate owns the fact, and threading a journal port through fifteen unrelated
use cases would put a notification concern inside every one of them. The same
reasoning already puts the organizer's review letters in
``presentation/api/v1/mail.py``.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Final

from apps.applications.infrastructure.models import ApplicationModel, ApplicationRevisionModel, SubmissionModel

__all__ = ["note_application_revision", "note_submission_revision"]

_logger: Final = logging.getLogger(__name__)

#: Order statuses in which an edit is news to the organizer. A DRAFT has never been
#: seen by anybody, and a settled order cannot be edited at all - in both cases there
#: is nothing to report.
_REPORTABLE_STATUSES: Final = ("SUBMITTED", "WAITING_PAYMENT")

#: The recorded description is display text in a letter; a runaway value (a pasted
#: performance title, say) is truncated rather than rejected, because losing the tail
#: of one line is better than losing the notice.
_MAX_CHANGE_LENGTH: Final = 500


@dataclass(frozen=True, slots=True)
class _Target:
    """The placed order an edit is being journalled against."""

    application_id: str
    competition_id: str
    applicant_id: str


def note_application_revision(*, application_id: str, change: str) -> None:
    """Record one edit to an order, if that order has already been placed."""
    try:
        row = (
            ApplicationModel.objects.filter(pk=application_id, deleted_at__isnull=True, status__in=_REPORTABLE_STATUSES)
            .values_list("id", "competition_id", "applicant_id")
            .first()
        )
        if row is None:
            return
        _write(_Target(application_id=str(row[0]), competition_id=str(row[1]), applicant_id=str(row[2])), change)
    except Exception:
        _logger.warning("Could not journal a revision of application %s", application_id, exc_info=True)


def note_submission_revision(*, submission_id: str, change: str) -> None:
    """Record one edit to a performance, against whichever placed order carries it."""
    try:
        target = _application_for_submission(submission_id)
        if target is None:
            return
        _write(target, change)
    except Exception:
        _logger.warning("Could not journal a revision of submission %s", submission_id, exc_info=True)


def _application_for_submission(submission_id: str) -> _Target | None:
    """Find the placed order whose submission refs include ``submission_id``.

    The refs live in a JSON column, so the match is made in Python over the
    applicant's own orders for that competition rather than with a JSON containment
    lookup - the candidate set is a handful of rows, and the query stays portable
    across the Postgres the platform runs on and the SQLite the tests use.
    """
    submission = SubmissionModel.objects.filter(pk=submission_id, deleted_at__isnull=True).values_list("applicant_id", "competition_id").first()
    if submission is None:
        return None
    applicant_id, competition_id = submission
    candidates = ApplicationModel.objects.filter(
        applicant_id=applicant_id,
        competition_id=competition_id,
        status__in=_REPORTABLE_STATUSES,
        deleted_at__isnull=True,
    ).values_list("id", "submission_refs")
    wanted = str(submission_id)
    for candidate_id, refs in candidates:
        if any(isinstance(ref, dict) and str(ref.get("submission_id") or "") == wanted for ref in refs or []):
            return _Target(application_id=str(candidate_id), competition_id=str(competition_id), applicant_id=str(applicant_id))
    return None


def _write(target: _Target, change: str) -> None:
    """Append one journal row for ``target``."""
    text = change.strip()
    if not text:
        return
    ApplicationRevisionModel.objects.create(
        application_id=target.application_id,
        competition_id=target.competition_id,
        applicant_id=target.applicant_id,
        change=text[:_MAX_CHANGE_LENGTH],
    )
