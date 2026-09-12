"""``DjangoBallotRepository`` — ORM adapter for the ``Ballot`` aggregate.

Saves the root and its nominees as one unit: the aggregate owns the list, so the
list in the database is rewritten to match it rather than diffed against it. The
one thing deliberately *not* written back from the aggregate is a nominee's vote
count — see :meth:`save`.
"""

from __future__ import annotations

import uuid
from collections.abc import Sequence
from datetime import datetime

from django.db import DatabaseError, IntegrityError, transaction

from apps.voting.domain.entities import Ballot
from apps.voting.domain.value_objects import BallotStatus
from apps.voting.infrastructure.mappers import BallotMapper
from apps.voting.infrastructure.models import BallotModel, BallotNomineeModel

from .exceptions import ConcurrencyConflictError, IntegrityViolationError, PersistenceError

__all__ = ["DjangoBallotRepository"]


class DjangoBallotRepository:
    """Django ORM adapter implementing the ``BallotRepository`` port."""

    def get(self, ballot_id: uuid.UUID) -> Ballot | None:
        """Return the ballot with ``ballot_id``, or ``None``."""
        try:
            model = BallotModel.objects.filter(pk=ballot_id, deleted_at__isnull=True).first()
        except DatabaseError as exc:  # pragma: no cover - defensive
            raise PersistenceError(f"Failed to load ballot {ballot_id}.") from exc
        return self._hydrate(model)

    def find_by_slug(self, slug: str) -> Ballot | None:
        """Return the ballot behind a public link, or ``None``.

        The public read path. A soft-deleted ballot is not found, which is what
        makes revoking a link work.
        """
        try:
            model = BallotModel.objects.filter(slug=slug, deleted_at__isnull=True).first()
        except DatabaseError as exc:  # pragma: no cover - defensive
            raise PersistenceError("Failed to load ballot by slug.") from exc
        return self._hydrate(model)

    def slug_exists(self, slug: str) -> bool:
        """Whether the slug is already claimed — including by a deleted ballot.

        Deleted rows count: a link that was handed out and revoked must never be
        minted again for something else.
        """
        try:
            return BallotModel.objects.filter(slug=slug).exists()
        except DatabaseError as exc:  # pragma: no cover - defensive
            raise PersistenceError("Failed to check slug.") from exc

    def list_for_organization(self, organization_id: uuid.UUID, *, competition_id: uuid.UUID | None = None) -> Sequence[Ballot]:
        """Return the organization's ballots, newest first.

        ``competition_id`` narrows to one festival's ballots; omitted, it returns
        every ballot the organization has, standalone ones included — which is what
        the list screen shows, because a standalone ballot is not a lesser one.
        """
        try:
            query = BallotModel.objects.filter(organization_id=organization_id, deleted_at__isnull=True)
            if competition_id is not None:
                query = query.filter(competition_id=competition_id)
            models = list(query.order_by("-created_at").prefetch_related("nominees"))
        except DatabaseError as exc:  # pragma: no cover - defensive
            raise PersistenceError("Failed to list ballots.") from exc
        return [BallotMapper.to_domain(model, self._live_nominees(model)) for model in models]

    def save(self, ballot: Ballot) -> None:
        """Persist the ballot and its nominee list as one unit.

        Two things are worth spelling out.

        **The vote counts are not written from the aggregate.** They are advanced by
        the vote use case with a database-level increment, and an organizer's save
        that happened to start before a vote landed would otherwise write back the
        stale number it read and lose the vote. So the count column is left alone
        here for rows that already exist; only a brand-new nominee gets its (zero)
        count written.

        **The list is rewritten, not diffed.** The aggregate owns the order and the
        membership; positions are a projection of its list. Nominees missing from
        the aggregate are deleted outright, which is safe precisely because the
        aggregate turns a removal into a withdrawal once votes exist.
        """
        columns = BallotMapper.root_columns(ballot)
        # Guarded on the version the aggregate was *read* at, not on ``version - 1``:
        # one use case may mutate a ballot many times before saving it (an import adds
        # fifty nominees and bumps the version fifty times), and a guard assuming one
        # bump per save refuses every batch operation there is.
        expected = ballot.persisted_version
        try:
            with transaction.atomic():
                if expected is None:
                    BallotModel.objects.create(**columns)
                else:
                    updated = BallotModel.objects.filter(pk=ballot.id, version=expected).update(
                        **{name: value for name, value in columns.items() if name != "id"}
                    )
                    if not updated:
                        raise ConcurrencyConflictError(f"Ballot {ballot.id} was modified concurrently; expected version {expected}.")
                self._save_nominees(ballot)
                ballot.mark_persisted()
        except IntegrityError as exc:
            raise IntegrityViolationError(f"Failed to persist ballot {ballot.id}.") from exc
        except DatabaseError as exc:  # pragma: no cover - defensive
            raise PersistenceError(f"Failed to persist ballot {ballot.id}.") from exc

    def soft_delete(self, ballot: Ballot, *, now: datetime) -> None:
        """Retire a ballot without erasing what was voted.

        The slug stays claimed (see :meth:`slug_exists`) and the votes stay in their
        table: a vote that happened is not undone by the organizer tidying up.
        """
        try:
            BallotModel.objects.filter(pk=ballot.id).update(deleted_at=now, updated_at=now)
        except DatabaseError as exc:  # pragma: no cover - defensive
            raise PersistenceError(f"Failed to delete ballot {ballot.id}.") from exc

    def refresh_counts(self, ballot: Ballot) -> Ballot:
        """Re-read the nominees' counts, leaving the rest of the aggregate alone.

        Used by the reads that render a scoreboard: the caller has an aggregate in
        hand and wants the numbers as they are this instant, not as they were when
        it was loaded.
        """
        reloaded = self.get(ballot.id)
        return reloaded if reloaded is not None else ballot

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    @staticmethod
    def _live_nominees(model: BallotModel) -> list[BallotNomineeModel]:
        return [row for row in model.nominees.all() if row.deleted_at is None]

    def _hydrate(self, model: BallotModel | None) -> Ballot | None:
        if model is None:
            return None
        rows = list(BallotNomineeModel.objects.filter(ballot_id=model.id, deleted_at__isnull=True).order_by("position"))
        return BallotMapper.to_domain(model, rows)

    def _save_nominees(self, ballot: Ballot) -> None:
        existing = {row.id: row for row in BallotNomineeModel.objects.filter(ballot_id=ballot.id)}
        kept: set[uuid.UUID] = set()

        for nominee in ballot.nominees:
            kept.add(nominee.id)
            columns = BallotMapper.nominee_columns(nominee, ballot_id=ballot.id, now=ballot.updated_at)
            row = existing.get(nominee.id)
            if row is None:
                BallotNomineeModel.objects.create(**columns)
                continue
            # `votes` is owned by the vote path, not by this save. See the docstring.
            BallotNomineeModel.objects.filter(pk=nominee.id).update(
                **{name: value for name, value in columns.items() if name not in {"id", "ballot_id", "created_at", "votes", "version"}},
                version=row.version + 1,
            )

        gone = set(existing) - kept
        if gone:
            BallotNomineeModel.objects.filter(pk__in=gone).delete()

    @staticmethod
    def open_ballot_ids(organization_id: uuid.UUID) -> list[uuid.UUID]:
        """Ids of the organization's ballots that are currently open."""
        return list(
            BallotModel.objects.filter(
                organization_id=organization_id,
                status=BallotStatus.OPEN.value,
                deleted_at__isnull=True,
            ).values_list("id", flat=True)
        )
