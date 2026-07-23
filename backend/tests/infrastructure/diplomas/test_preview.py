"""Integration tests for the diploma preview BindingResolver.

Exercises the cross-context read of the Applications context against real
PostgreSQL, as for every ``tests/infrastructure`` suite.
"""

from __future__ import annotations

import uuid

import pytest

from apps.applications.infrastructure.models.submission import SubmissionModel
from apps.diplomas.presentation.api.v1.diplomas import preview

pytestmark = pytest.mark.django_db


def _submission(competition_id: uuid.UUID, display_name: str) -> SubmissionModel:
    return SubmissionModel.objects.create(
        competition_id=competition_id,
        applicant_id=uuid.uuid4(),
        status="SUBMITTED",
        participants=[{"display_name": display_name, "member_count": 1}],
        performance={"title": "Этюд"},
    )


def test_lists_applications_labelled_by_performer() -> None:
    competition_id = uuid.uuid4()
    submission = _submission(competition_id, "Иванов Иван Иванович")

    applications = preview.list_preview_applications(str(competition_id))

    assert {"id": str(submission.id), "label": "Иванов Иван Иванович"} in applications


def test_resolves_participant_display_name() -> None:
    submission = _submission(uuid.uuid4(), "Ансамбль «Созвездие»")

    bindings = preview.resolve_preview_bindings(str(submission.id))

    assert bindings == {"participant.display_name": "Ансамбль «Созвездие»"}


def test_resolve_unknown_application_returns_none() -> None:
    assert preview.resolve_preview_bindings(str(uuid.uuid4())) is None
