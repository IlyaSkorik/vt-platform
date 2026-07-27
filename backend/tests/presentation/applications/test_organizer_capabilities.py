"""Unit tests for the organizer workspace's per-status action list.

``_capabilities`` is what the processing page renders as buttons, so it is the
answer to "what can I do with this entry right now". Pure function over a status
string — no ORM, no auth.
"""

from __future__ import annotations

import pytest

from apps.applications.domain.value_objects import SubmissionStatus
from apps.applications.presentation.api.v1.organizer.views import _capabilities


def _keys(status: str) -> list[str]:
    return [item["key"] for item in _capabilities(status)]


@pytest.mark.parametrize(
    "status",
    [SubmissionStatus.ACCEPTED.value, SubmissionStatus.SCHEDULED.value],
)
def test_an_entry_in_the_running_order_can_still_be_cancelled(status: str) -> None:
    """The applicant can no longer withdraw here, so the organizer must be able to.

    Such a withdrawal is decided case by case — a disqualification, a no-show, or a
    request granted as an exception — which is why it is offered here and nowhere
    else.
    """
    assert "cancel" in _keys(status)


def test_an_accepted_entry_can_also_be_moved_into_the_running_order() -> None:
    # Cancelling must not have crowded out the ordinary next step.
    assert _keys(SubmissionStatus.ACCEPTED.value) == ["move_to_running", "cancel"]


def test_a_performed_entry_offers_nothing() -> None:
    """COMPLETED is terminal: the performance happened, and its diploma may already
    be in the register."""
    assert _keys(SubmissionStatus.COMPLETED.value) == []


@pytest.mark.parametrize(
    "status",
    [SubmissionStatus.CANCELLED.value, SubmissionStatus.REQUIRES_CORRECTION.value],
)
def test_statuses_awaiting_someone_else_offer_nothing(status: str) -> None:
    # Cancelled is terminal; a correction is the applicant's turn.
    assert _keys(status) == []


def test_an_unknown_status_offers_nothing_rather_than_raising() -> None:
    assert _keys("SOMETHING_NEW") == []
