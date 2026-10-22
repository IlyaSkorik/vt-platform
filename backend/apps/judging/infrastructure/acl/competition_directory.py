"""``DjangoCompetitionDirectory`` — the Judging context's window onto Competitions.

Reads only: the genres and nominations an organizer writes criteria against, the
festival's title for an invitation letter, who owns it, and whether it judges online at
all (ARCH-001 §13.3, Anti-Corruption Layer).

That last one is the important method. The judging mode is a *Competitions* setting —
it sits in the same bag as "нужен ли педагог" because it is a property of how the
festival runs, not of the panel. This context asks rather than keeping its own copy, so
an organizer who turns online judging off has turned it off everywhere at once, with no
second switch to remember.
"""

from __future__ import annotations

import uuid
from collections.abc import Sequence
from typing import Any

from apps.competitions.infrastructure.models.competition import CompetitionModel
from apps.competitions.infrastructure.models.taxonomy import CategoryModel, DisciplineModel
from apps.judging.application.interfaces import DirectoryCompetition, DirectoryNomination

__all__ = ["DjangoCompetitionDirectory"]

#: The wire value of :class:`~apps.competitions.domain.value_objects.JudgingMode.ONLINE`.
#: Compared as a string rather than imported as an enum: this adapter reads another
#: context's stored JSON, and the string is what is actually in the column.
_ONLINE = "ONLINE"


def _clean(value: Any) -> str:
    return str(value or "").strip()


class DjangoCompetitionDirectory:
    """Concrete :class:`~apps.judging.application.interfaces.CompetitionDirectory`."""

    def nominations(self, competition_id: uuid.UUID) -> tuple[DirectoryNomination, ...]:
        """Every genre of the festival with its nominations, in the organizer's order."""
        categories = list(
            CategoryModel.objects.filter(competition_id=competition_id, deleted_at__isnull=True)
            .order_by("sort_order", "name")
            .values("id", "name", "sort_order")
        )
        if not categories:
            return ()
        disciplines = list(
            DisciplineModel.objects.filter(competition_id=competition_id, deleted_at__isnull=True)
            .order_by("sort_order", "name")
            .values("id", "name", "category_id")
        )
        by_category: dict[str, list[tuple[uuid.UUID, str]]] = {}
        for item in disciplines:
            by_category.setdefault(str(item["category_id"]), []).append((item["id"], str(item["name"])))
        return tuple(
            DirectoryNomination(
                category_id=item["id"],
                name=str(item["name"]),
                sort_order=int(item["sort_order"] or 0),
                disciplines=tuple(by_category.get(str(item["id"]), ())),
            )
            for item in categories
        )

    def competition_title(self, competition_id: uuid.UUID) -> str:
        title = CompetitionModel.objects.filter(id=competition_id, deleted_at__isnull=True).values_list("title", flat=True).first()
        return _clean(title) or "Фестиваль"

    def competitions(self, competition_ids: Sequence[uuid.UUID]) -> dict[uuid.UUID, DirectoryCompetition]:
        """Resolve several festivals at once — one query, whatever the panel's size."""
        if not competition_ids:
            return {}
        rows = CompetitionModel.objects.filter(id__in=list(competition_ids), deleted_at__isnull=True).values(
            "id",
            "title",
            "settings",
            "competition_start",
            "competition_end",
            "venue_name",
        )
        resolved: dict[uuid.UUID, DirectoryCompetition] = {}
        for row in rows:
            settings = row["settings"] if isinstance(row["settings"], dict) else {}
            resolved[row["id"]] = DirectoryCompetition(
                competition_id=row["id"],
                title=_clean(row["title"]) or "Фестиваль",
                online_judging=_clean(settings.get("judging_mode")) == _ONLINE,
                starts_on=row["competition_start"],
                ends_on=row["competition_end"],
                venue=_clean(row["venue_name"]) or None,
            )
        return resolved

    def online_judging_enabled(self, competition_id: uuid.UUID) -> bool:
        """Whether this festival's jury scores on the platform.

        A festival whose settings have never been saved reads as ``False``, which is the
        right answer twice over: it is the stored default, and a panel must not be able
        to start marking a festival nobody configured for it.
        """
        settings = CompetitionModel.objects.filter(id=competition_id, deleted_at__isnull=True).values_list("settings", flat=True).first()
        if not isinstance(settings, dict):
            return False
        return _clean(settings.get("judging_mode")) == _ONLINE

    def organizer_id(self, competition_id: uuid.UUID) -> uuid.UUID | None:
        return CompetitionModel.objects.filter(id=competition_id, deleted_at__isnull=True).values_list("organizer_id", flat=True).first()
