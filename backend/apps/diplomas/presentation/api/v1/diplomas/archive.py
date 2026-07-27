"""The generation archive: record a finished run, list the history.

Every way of generating documents ends here — the asynchronous diploma print
package from its Celery task, the synchronous thank-you runs from their endpoint —
so the organizer has one history to look at rather than one per mechanism, and one
place to fetch a ZIP from again when the browser lost the download.

Only *completed* runs are recorded. A failed diploma job has nothing to download and
nothing to count; its error stays on the job row, where the client that started it
is already watching.

Kept thin like its siblings: the model holds the row, this holds the shaping.
"""

from __future__ import annotations

import uuid
from typing import Any

from apps.competitions.infrastructure.models.competition import CompetitionModel
from apps.diplomas.infrastructure.models import GenerationRunModel

__all__ = ["list_runs", "record_run"]

#: How many runs the archive returns. A history is read newest-first and skimmed,
#: not paged through; the cap keeps one competition's noisy re-runs from making the
#: response unbounded.
_LIMIT = 200


def record_run(
    *,
    competition_id: uuid.UUID,
    document_type: str,
    category_ids: list[str],
    document_count: int,
    created_count: int = 0,
    published_count: int = 0,
    zip_path: str = "",
    actor_id: uuid.UUID | None = None,
    actor_label: str = "",
) -> None:
    """Append one completed run to the archive.

    Never raises into its caller's face: the archive is a record of work already
    done, so failing to write the history must not undo a successful generation or
    turn it into an error the organizer sees. A lost row costs a line of history.
    """
    try:
        GenerationRunModel.objects.create(
            competition_id=competition_id,
            document_type=document_type,
            category_ids=[str(category_id) for category_id in category_ids],
            document_count=max(0, document_count),
            created_count=max(0, created_count),
            published_count=max(0, published_count),
            zip_path=zip_path or "",
            actor_id=actor_id,
            actor_label=actor_label or "",
        )
    except Exception:  # pragma: no cover - defensive; the run itself already succeeded
        return


def list_runs(competition_id: uuid.UUID | None = None) -> list[dict[str, Any]]:
    """The generation history, newest first, optionally for one competition.

    The competition's title is resolved on read rather than frozen in the row, so a
    renamed competition reads correctly throughout its own history. A competition
    that has since been deleted resolves to ``None`` and the client shows the run
    without it — losing the name must not lose the run.
    """
    rows = GenerationRunModel.objects.filter(deleted_at__isnull=True)
    if competition_id is not None:
        rows = rows.filter(competition_id=competition_id)
    runs = list(rows.order_by("-created_at")[:_LIMIT])

    titles = {
        str(row["id"]): str(row["title"])
        for row in CompetitionModel.objects.filter(
            id__in={run.competition_id for run in runs}, deleted_at__isnull=True
        ).values("id", "title")
    }

    return [
        {
            "id": str(run.id),
            "documentType": run.document_type,
            "competitionId": str(run.competition_id),
            "competition": titles.get(str(run.competition_id)),
            "nominations": len(run.category_ids or []),
            "documents": run.document_count,
            "created": run.created_count,
            "published": run.published_count,
            "zipUrl": run.zip_path or None,
            "user": run.actor_label or None,
            "createdAt": run.created_at,
        }
        for run in runs
    ]
