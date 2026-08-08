"""``ApplicationRevisionModel`` - the journal of edits made to an order after it was placed.

Deliberately **not** part of either aggregate. An edit to an already-submitted order
breaks no invariant the ``Application`` or the ``Submission`` has to defend - both
stay editable by design while registration is open - so nothing about it belongs in
the domain. What it *is* is correspondence: the organizer accepted a list of
performances and that list has since changed, and they have to be told.

So this is a plain append-only log written at the API edge (the same place the
organizer's review letters are composed, see ``presentation/api/v1/mail.py``) and
read by the digest sweep in ``tasks.py``. ``notified_at`` is stamped once a row has
gone out in a digest, which is the only thing keeping the next sweep from reporting
the same edit again.
"""

from __future__ import annotations

from django.db import models

from .base import BasePersistenceModel

__all__ = ["ApplicationRevisionModel"]


class ApplicationRevisionModel(BasePersistenceModel):
    """One recorded edit to a submitted order (persistence only - no business logic)."""

    application_id = models.UUIDField()
    competition_id = models.UUIDField()
    applicant_id = models.UUIDField()

    #: A short human-readable Russian description of what the applicant changed,
    #: composed at the edge ("Добавлен педагог: Иванова И. И."). The digest lists
    #: these verbatim, so it is display text rather than a machine-readable diff.
    change = models.CharField(max_length=500)

    #: When this row was included in a digest to the organizer; ``None`` while it is
    #: still pending. Not a boolean, because "when did we tell them" is the question
    #: support actually asks.
    notified_at = models.DateTimeField(null=True, blank=True, default=None)

    class Meta(BasePersistenceModel.Meta):
        db_table = "applications_application_revision"
        verbose_name = "application revision"
        verbose_name_plural = "application revisions"
        indexes = [
            *BasePersistenceModel.Meta.indexes,
            # The sweep's only query: everything still unsent, newest-per-order first.
            models.Index(fields=["notified_at", "application_id"]),
        ]

    def __str__(self) -> str:
        return f"Revision of application {self.application_id} ({self.change[:40]})"
