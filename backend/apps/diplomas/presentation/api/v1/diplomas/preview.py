"""Diploma preview data — the BindingResolver.

Given an application (a submission), resolve the values that fill a template's
data-bound fields, keyed by binding (e.g. ``participant.display_name``). Reads the
Applications context by id (cross-context read, as the organizer views do); the
diplomas context owns none of these rows.

`participant.display_name` is the performer's single display name — the
individual's full name for a solo entry or the ensemble's name for a collective
— exactly the unified field the editor binds to.
"""

from __future__ import annotations

from typing import Any

from apps.applications.infrastructure.models.submission import SubmissionModel

__all__ = [
    "PARTICIPANT_DISPLAY_NAME",
    "list_preview_applications",
    "resolve_preview_bindings",
]

PARTICIPANT_DISPLAY_NAME = "participant.display_name"


def _performer_name(submission: SubmissionModel) -> str:
    for participant in submission.participants or []:
        name = str(participant.get("display_name") or "").strip()
        if name:
            return name
    return ""


def list_preview_applications(competition_id: str) -> list[dict[str, Any]]:
    """Applications (submissions) of a competition, labelled by performer name."""
    rows = SubmissionModel.objects.filter(
        competition_id=competition_id, deleted_at__isnull=True
    ).order_by("-created_at")
    applications: list[dict[str, Any]] = []
    for row in rows:
        performance = row.performance or {}
        label = _performer_name(row) or str(performance.get("title") or "").strip()
        applications.append({"id": str(row.id), "label": label or str(row.id)[:8].upper()})
    return applications


def resolve_preview_bindings(application_id: str) -> dict[str, str] | None:
    """The binding→value map for one application, or None if it does not exist."""
    submission = SubmissionModel.objects.filter(
        id=application_id, deleted_at__isnull=True
    ).first()
    if submission is None:
        return None
    return {PARTICIPANT_DISPLAY_NAME: _performer_name(submission)}
