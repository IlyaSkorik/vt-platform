"""``GenerationRunModel`` — the append-only log behind the generation archive.

One row per **completed** generation run, of any document kind: the numbered
diploma print package and the synchronous thank-you runs alike. It answers the
questions the archive asks — when, which competition, what kind, how many
documents, by whom, and where the ZIP is to download again — and nothing else.

Why not read this off :class:`PrintJobModel`. That row is the *job*: a diploma
package's durable status while a worker renders it, polled by the client and
meaningless once settled. Thank-you runs have no job at all (they finish inside the
request), so a history built on jobs would show half the generations. This table
is the history; the job table stays the job.

Deliberately a **snapshot**, like every other record in this context: the actor's
name is frozen as it was, so the archive keeps saying who generated a package even
after that person is renamed or leaves. Cross-context references
(``competition_id``, ``actor_id``) are id-only plain ``UUIDField`` columns
(ARCH-001 §7.2) — never FKs.
"""

from __future__ import annotations

from django.db import models

from .base import BasePersistenceModel
from .document_type import DocumentTypeChoices

__all__ = ["GenerationRunModel"]


class GenerationRunModel(BasePersistenceModel):
    """Database row for one completed generation run (persistence only)."""

    document_type = models.CharField(max_length=32, choices=DocumentTypeChoices.choices)

    # Id-only cross-context reference; the title is resolved when the archive is read
    # rather than frozen, so a renamed competition reads correctly in its own history.
    competition_id = models.UUIDField()

    # Nominations the run targeted. Empty means "every nomination with a template",
    # which is how the diploma package expresses an unnarrowed run.
    category_ids = models.JSONField(default=list, blank=True)

    # How many documents the run put out — the size of the printable set, which on a
    # repeat run is larger than what it created. This is the number the archive shows.
    document_count = models.PositiveIntegerField(default=0)
    # Of those, how many did not exist before this run.
    created_count = models.PositiveIntegerField(default=0)
    # How many the run made visible to participants. Zero for a print-only run.
    published_count = models.PositiveIntegerField(default=0)

    # The archive's whole point: the ZIP to download again. Empty for a run that
    # produced no archive (a publish-only thank-you run has nothing to print).
    zip_path = models.CharField(max_length=1024, blank=True, default="")

    # Who ran it, frozen at the time of the run (see the module note).
    actor_id = models.UUIDField(null=True, blank=True, default=None)
    actor_label = models.CharField(max_length=320, blank=True, default="")

    class Meta(BasePersistenceModel.Meta):
        db_table = "diplomas_generation_run"
        verbose_name = "generation run"
        verbose_name_plural = "generation runs"
        indexes = [
            *BasePersistenceModel.Meta.indexes,
            models.Index(fields=["competition_id"]),
            models.Index(fields=["document_type"]),
            models.Index(fields=["-created_at"]),
        ]
        constraints = [
            *BasePersistenceModel.Meta.constraints,
            models.CheckConstraint(
                condition=models.Q(document_type__in=DocumentTypeChoices.values),
                name="diplomas_generation_run_type_valid",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.document_type} run for competition {self.competition_id}"
