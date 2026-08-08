"""Use cases of the Results bounded context.

One service over one aggregate: every operation loads the protocol, asks the domain to
change it, saves it, and renders the result. The rules live in the aggregate - this
layer orchestrates, and reaches other contexts exclusively through the ports in
:mod:`apps.results.application.interfaces`.

The write methods all return the freshly rendered
:class:`~apps.results.application.dto.ProtocolDetailView`. A jury's table needs its
whole state back after every edit anyway (a saved award changes whether the protocol can
be published, and whether what is published is stale), so returning it removes a
follow-up request and with it any chance of a screen rendering a result it did not save.

:meth:`ProtocolService.publish` is the one method here that does more than move data
around. It is written as one ordered sequence on purpose:

1. the domain publishes - status, revision, slug, timestamp, and the refusal to publish
   nothing at all;
2. the protocol is **saved**, so a failure in anything below cannot leave results that
   the page says are public but the database calls a draft;
3. the degrees are written onto the diplomas, which is what makes them appear in the
   participant's cabinet;
4. the letters are queued, last, because a letter is the one effect that cannot be
   undone by trying again.
"""

from __future__ import annotations

import uuid
from collections import defaultdict
from collections.abc import Sequence
from datetime import datetime

from apps.results.application.commands import (
    AddRowCommand,
    AwardRowsCommand,
    CreateProtocolCommand,
    PublishProtocolCommand,
    ReorderRowsCommand,
    UpdateProtocolCommand,
)
from apps.results.application.dto import (
    AwardOptionView,
    ColumnView,
    ProtocolDetailView,
    ProtocolRowView,
    ProtocolSummaryView,
    ProtocolTableView,
    PublicationResultView,
    PublicProtocolRowView,
    PublicProtocolView,
    PublishedProtocolLinkView,
)
from apps.results.application.interfaces import (
    AwardedDiploma,
    AwardRegister,
    CatalogPerformance,
    Clock,
    PerformanceCatalog,
    ProtocolRepository,
    ResultsNotifier,
    RunningOrderSource,
    SlugFactory,
)
from apps.results.domain.entities import Protocol, ProtocolRow
from apps.results.domain.exceptions import (
    InvalidProtocolDataError,
    PerformanceNotAvailableError,
    ProtocolAlreadyExistsError,
    ProtocolNotFoundError,
    SlugUnavailableError,
)
from apps.results.domain.value_objects import (
    AWARD_LABELS,
    COLUMN_LABELS,
    AwardKind,
    ProtocolColumn,
    ProtocolName,
    PublicSlug,
    PublishedResult,
    parse_award,
    parse_columns,
)

__all__ = ["PUBLIC_PROTOCOL_PATH", "ProtocolService"]

#: The client-side route a published slug resolves to. Rendered into API responses so
#: the organizer can copy the link, and the landing page can link it, without either
#: re-deriving the URL shape.
PUBLIC_PROTOCOL_PATH = "/protocol/{slug}"

#: How many times to re-roll a slug before giving up. A collision needs two of ~57
#: random bits to coincide, so a single retry is already generous; the loop exists so the
#: failure is an explicit error instead of an integrity error from the database.
_SLUG_ATTEMPTS = 8


def _uuid(value: str, *, what: str) -> uuid.UUID:
    try:
        return uuid.UUID(str(value))
    except (ValueError, TypeError, AttributeError) as exc:
        raise InvalidProtocolDataError(f"{what} must be a UUID, got {value!r}.") from exc


class ProtocolService:
    """Everything a jury and an organizer do to a protocol, and the one public read."""

    def __init__(
        self,
        *,
        protocols: ProtocolRepository,
        catalog: PerformanceCatalog,
        running_order: RunningOrderSource,
        clock: Clock,
        slugs: SlugFactory,
        awards: AwardRegister | None = None,
        notifier: ResultsNotifier | None = None,
    ) -> None:
        self._protocols = protocols
        self._catalog = catalog
        self._running_order = running_order
        self._clock = clock
        self._slugs = slugs
        # Both optional: every use case except publication works without them, and a test
        # that only fills in a table should not have to supply a diploma register.
        self._awards = awards
        self._notifier = notifier

    # ------------------------------------------------------------------
    # Protocols
    # ------------------------------------------------------------------

    def create_protocol(self, command: CreateProtocolCommand) -> ProtocolDetailView:
        """Open a protocol for one nomination, seeded from how the day actually ran.

        Seeding is the whole convenience of this action: the programme's running order
        and its numbers are copied in, so the jury's first screen is the list they were
        looking at from the hall rather than an empty table. A nomination with no
        programme falls back to its competing acts in catalog order.
        """
        now = self._clock.utcnow()
        competition_id = _uuid(command.competition_id, what="competitionId")
        nomination_id = _uuid(command.nomination_id, what="nominationId")
        if self._protocols.get_for_nomination(competition_id=competition_id, nomination_id=nomination_id) is not None:
            raise ProtocolAlreadyExistsError("This nomination already has a protocol.")
        name = command.name or self._default_name(nomination_id)
        protocol = Protocol.create(
            protocol_id=uuid.uuid4(),
            competition_id=competition_id,
            nomination_id=nomination_id,
            name=ProtocolName(name),
            now=now,
            public_columns=parse_columns(command.columns),
        )
        if command.seed:
            self._seed(protocol, now=now)
        self._protocols.save(protocol)
        return self._detail(protocol)

    def list_protocols(self, *, competition_id: str) -> tuple[ProtocolSummaryView, ...]:
        """Every protocol of a competition - one per nomination that has one."""
        protocols = self._protocols.list_for_competition(_uuid(competition_id, what="competitionId"))
        return tuple(self._summary(protocol) for protocol in protocols)

    def get_protocol(self, protocol_id: str) -> ProtocolDetailView:
        """One protocol, with every row resolved against the live entries."""
        return self._detail(self._load(protocol_id))

    def update_protocol(self, command: UpdateProtocolCommand) -> ProtocolDetailView:
        """Rename a protocol, and/or choose which columns its public page shows."""
        now = self._clock.utcnow()
        protocol = self._load(command.protocol_id)
        if command.name is not None:
            protocol.rename(ProtocolName(command.name), now=now)
        if command.columns is not None:
            protocol.show_columns(parse_columns(command.columns), now=now)
        self._protocols.save(protocol)
        return self._detail(protocol)

    def delete_protocol(self, protocol_id: str) -> None:
        """Soft-delete a protocol; its public link stops resolving at once."""
        protocol = self._load(protocol_id)
        protocol.delete(now=self._clock.utcnow())
        self._protocols.save(protocol)

    # ------------------------------------------------------------------
    # Rows
    # ------------------------------------------------------------------

    def candidates(self, protocol_id: str) -> tuple[CatalogPerformance, ...]:
        """The competing acts of this nomination that have no row yet."""
        protocol = self._load(protocol_id)
        taken = set(protocol.submission_ids)
        available = self._catalog.competing_performances(
            competition_id=protocol.competition_id,
            nomination_id=protocol.nomination_id,
        )
        return tuple(performance for performance in available if performance.submission_id not in taken)

    def add_row(self, command: AddRowCommand) -> ProtocolDetailView:
        """Add one act's line to the protocol."""
        now = self._clock.utcnow()
        protocol = self._load(command.protocol_id)
        submission_id = _uuid(command.submission_id, what="submissionId")
        self._require_competed(protocol, submission_id)
        protocol.add_row(
            row_id=uuid.uuid4(),
            submission_id=submission_id,
            now=now,
            award=parse_award(command.award),
            position=command.position,
        )
        self._protocols.save(protocol)
        return self._detail(protocol)

    def sync_from_running_order(self, protocol_id: str) -> ProtocolDetailView:
        """Pull in every act of this nomination that has no row yet.

        The catch-up action for a protocol opened before registration finished, or before
        an act was added to the programme. Existing rows keep their place **and their
        award** - this only ever appends, because a jury's entered result must survive an
        organizer pressing "обновить состав".
        """
        now = self._clock.utcnow()
        protocol = self._load(protocol_id)
        self._seed(protocol, now=now)
        self._protocols.save(protocol)
        return self._detail(protocol)

    def remove_row(self, *, protocol_id: str, row_id: str) -> ProtocolDetailView:
        """Remove one line - an act that never appeared, or a row added by mistake."""
        now = self._clock.utcnow()
        protocol = self._load(protocol_id)
        protocol.remove_row(_uuid(row_id, what="rowId"), now=now)
        self._protocols.save(protocol)
        return self._detail(protocol)

    def reorder_rows(self, command: ReorderRowsCommand) -> ProtocolDetailView:
        """Apply a new order, leaving every number with the act it belongs to."""
        now = self._clock.utcnow()
        protocol = self._load(command.protocol_id)
        protocol.reorder([_uuid(row_id, what="rowId") for row_id in command.row_ids], now=now)
        self._protocols.save(protocol)
        return self._detail(protocol)

    def renumber_rows(self, protocol_id: str) -> ProtocolDetailView:
        """Re-issue numbers 1..N along the current order (the explicit, opt-in reset)."""
        now = self._clock.utcnow()
        protocol = self._load(protocol_id)
        protocol.renumber_sequentially(now=now)
        self._protocols.save(protocol)
        return self._detail(protocol)

    # ------------------------------------------------------------------
    # Results
    # ------------------------------------------------------------------

    def award_rows(self, command: AwardRowsCommand) -> ProtocolDetailView:
        """Write results - one, or a whole nomination's worth in a single save.

        The action the jury tab exists for, and it is deliberately unremarkable: no
        status check, no one-way transition, no confirmation. A result is a value on a
        row, and changing it is changing a value.
        """
        now = self._clock.utcnow()
        protocol = self._load(command.protocol_id)
        protocol.award_rows(
            ((_uuid(row_id, what="rowId"), parse_award(award)) for row_id, award in command.awards),
            now=now,
        )
        self._protocols.save(protocol)
        return self._detail(protocol)

    def clear_awards(self, protocol_id: str) -> ProtocolDetailView:
        """Clear every result in the protocol (a rehearsal run, or the wrong day's list)."""
        now = self._clock.utcnow()
        protocol = self._load(protocol_id)
        protocol.clear_awards(now=now)
        self._protocols.save(protocol)
        return self._detail(protocol)

    # ------------------------------------------------------------------
    # Publication
    # ------------------------------------------------------------------

    def publish(self, command: PublishProtocolCommand) -> PublicationResultView:
        """Publish the results: the page, the diplomas, and the letters.

        The order below is the contract, not an implementation detail - see the module
        docstring. The two side effects are attempted even if the other fails, and both
        are counted in the response: an organizer who publishes results and gets no mail
        must be told that, not left to find out from a participant.
        """
        now = self._clock.utcnow()
        protocol = self._load(command.protocol_id)
        if command.columns is not None:
            protocol.show_columns(parse_columns(command.columns), now=now)
        protocol.publish(slug=self._mint_slug(), now=now)
        # Saved before anything leaves this context: a diploma that carries a degree from
        # a protocol the database still calls a draft is the one inconsistency here that
        # nobody could explain afterwards.
        self._protocols.save(protocol)

        awarded = self._record_awards(protocol, now=now)
        letters_sent, letters_skipped = self._send_letters(protocol) if command.notify else (0, 0)

        decided = len(protocol.decided_rows)
        return PublicationResultView(
            protocol=self._detail(protocol),
            diplomas_awarded=len(awarded),
            diplomas_created=sum(1 for entry in awarded if entry.created),
            diplomas_missing=max(0, decided - len(awarded)),
            letters_sent=letters_sent,
            letters_skipped=letters_skipped,
        )

    def unpublish(self, protocol_id: str) -> ProtocolDetailView:
        """Take a protocol back off the public page (a publication in error).

        Deliberately narrow: the page stops resolving, and nothing else is undone. The
        degrees already written onto diplomas stay - a diploma that has reached a
        participant's cabinet is a document that was issued, and pretending otherwise
        would be a worse lie than a withdrawn page. Correcting a degree means publishing
        a corrected protocol, which is what revisions are for.
        """
        now = self._clock.utcnow()
        protocol = self._load(protocol_id)
        protocol.unpublish(now=now)
        self._protocols.save(protocol)
        return self._detail(protocol)

    def _record_awards(self, protocol: Protocol, *, now: datetime) -> tuple[AwardedDiploma, ...]:
        """Hand the decided rows to the diploma register, if one is wired up."""
        if self._awards is None:
            return ()
        pairs = [(row.submission_id, AWARD_LABELS[row.award]) for row in protocol.decided_rows if row.award is not None]
        if not pairs:
            return ()
        return self._awards.record_awards(
            competition_id=protocol.competition_id,
            nomination_id=protocol.nomination_id,
            awards=pairs,
            now=now,
        )

    def _send_letters(self, protocol: Protocol) -> tuple[int, int]:
        """One letter per applicant, carrying every result of theirs in this protocol.

        Grouped by applicant rather than sent per row: a studio that entered thirty acts
        gets one letter listing thirty results. That is both kinder to the recipient and
        the difference between thirty messages and one against a provider that counts its
        allowance per minute.

        An applicant with no email on file is skipped and counted, never guessed at.
        """
        if self._notifier is None or protocol.slug is None:
            return 0, 0
        performances = self._resolve_performances(protocol.rows)
        competition = self._catalog.competition_title(protocol.competition_id)
        nomination = self._catalog.nomination_title(protocol.nomination_id)
        url = PUBLIC_PROTOCOL_PATH.format(slug=protocol.slug)

        grouped: dict[uuid.UUID, list[tuple[str, str]]] = defaultdict(list)
        recipients: dict[uuid.UUID, CatalogPerformance] = {}
        skipped = 0
        for row in protocol.decided_rows:
            performance = performances.get(row.submission_id)
            if performance is None or row.award is None:
                # The act is gone from Applications entirely: there is nobody to write to.
                skipped += 1
                continue
            if performance.applicant_id is None or not performance.applicant_email:
                skipped += 1
                continue
            grouped[performance.applicant_id].append((performance.title, AWARD_LABELS[row.award]))
            recipients.setdefault(performance.applicant_id, performance)

        sent = 0
        for applicant_id, results in grouped.items():
            performance = recipients[applicant_id]
            self._notifier.notify_results_published(
                user_id=str(applicant_id),
                email=str(performance.applicant_email),
                applicant_name=performance.applicant_name,
                competition_title=competition,
                nomination_title=nomination,
                results=tuple(results),
                protocol_url=url,
            )
            sent += 1
        return sent, skipped

    # ------------------------------------------------------------------
    # Public reads
    # ------------------------------------------------------------------

    def public_protocol(self, slug: str) -> PublicProtocolView | None:
        """Resolve a public link into the table it publishes, or ``None``.

        Rendered from the protocol's **frozen snapshot**, never from its live rows: a jury
        that corrects a result after the ceremony has changed a draft, and nothing reaches
        this page until somebody publishes again. That is the whole difference between an
        editable protocol and a leaky one.

        The names are still read live, and deliberately: a misspelled surname is corrected in
        the entry and the public page follows at once, because a child's name is not part of
        the verdict. An act deleted from Applications outright keeps its line, since the
        published protocol said it competed.

        Only the columns the snapshot was cut to are rendered into cells, so a column the
        organizer did not publish never reaches the response and cannot be read off the wire
        by anyone holding the link.
        """
        protocol = self._protocols.get_by_slug(slug)
        if protocol is None:
            return None
        snapshot = protocol.published_snapshot
        if snapshot is None:
            # Published with no snapshot is not a state the aggregate can reach; treating it
            # as an unresolvable link beats rendering the live draft by accident.
            return None
        columns = snapshot.columns
        performances = self._catalog.performances_by_id([result.submission_id for result in snapshot.results])
        return PublicProtocolView(
            name=snapshot.name,
            slug=str(protocol.slug),
            competition_title=self._catalog.competition_title(protocol.competition_id),
            nomination=self._catalog.nomination_title(protocol.nomination_id),
            revision=protocol.revision,
            published_at=protocol.published_at,
            columns=self._column_views(columns),
            rows=tuple(
                PublicProtocolRowView(
                    cells=self._published_cells(result, performances.get(result.submission_id), columns),
                    award=result.award.value if result.award is not None else None,
                )
                for result in snapshot.results
            ),
        )

    def published_links(self, competition_id: str) -> tuple[PublishedProtocolLinkView, ...]:
        """The competition's published protocols - the landing page's "Результаты".

        The second unauthenticated read. Deliberately links rather than contents: a
        landing page lists the documents a competition has published, and each document
        decides for itself what it shows.
        """
        protocols = self._protocols.list_published_for_competition(_uuid(competition_id, what="competitionId"))
        links: list[PublishedProtocolLinkView] = []
        for protocol in protocols:
            if protocol.slug is None:  # pragma: no cover - published implies a slug
                continue
            links.append(
                PublishedProtocolLinkView(
                    nomination=self._catalog.nomination_title(protocol.nomination_id),
                    name=str(protocol.name),
                    slug=str(protocol.slug),
                    path=PUBLIC_PROTOCOL_PATH.format(slug=protocol.slug),
                    revision=protocol.revision,
                    published_at=protocol.published_at,
                )
            )
        return tuple(links)

    def protocol_table(self, *, protocol_id: str, columns: Sequence[str] = ()) -> ProtocolTableView:
        """Render the protocol as a plain table of the chosen columns.

        The organizer's own cut, for printing or sending on. It goes through the same
        cell renderer as the public page, so an exported table and the published one can
        never disagree about what a cell says. An empty selection means every column -
        an export is for the organizer, who is allowed to see all of it.
        """
        protocol = self._load(protocol_id)
        chosen = parse_columns(columns) if columns else tuple(ProtocolColumn)
        performances = self._resolve_performances(protocol.rows)
        competition = self._catalog.competition_title(protocol.competition_id)
        nomination = self._catalog.nomination_title(protocol.nomination_id)
        return ProtocolTableView(
            title=str(protocol.name),
            subtitle=" · ".join(part for part in (competition, nomination) if part) or None,
            columns=self._column_views(chosen),
            rows=tuple(self._cells(row, performances.get(row.submission_id), chosen) for row in protocol.rows),
        )

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    def _load(self, protocol_id: str) -> Protocol:
        protocol = self._protocols.get(_uuid(protocol_id, what="protocolId"))
        if protocol is None:
            raise ProtocolNotFoundError(f"Protocol {protocol_id} does not exist.")
        return protocol

    def _default_name(self, nomination_id: uuid.UUID) -> str:
        """Name a protocol after its nomination, which is what an organizer would type."""
        return self._catalog.nomination_title(nomination_id) or "Протокол"

    def _seed(self, protocol: Protocol, *, now: datetime) -> None:
        """Append every act of this nomination that has no row yet.

        Order of preference is the programme first, the catalog second, and it matters:
        the programme knows the order the acts *performed in* and the numbers they were
        announced under, and a protocol that lists them in any other order is a document
        the jury cannot follow. The catalog fallback exists because a nomination judged
        without a printed programme is normal, not an error.

        Only ever appends: an existing row keeps its position and its award, so this is
        safe to press twice and safe to press after results have been entered.
        """
        taken = set(protocol.submission_ids)
        available = {
            performance.submission_id: performance
            for performance in self._catalog.competing_performances(
                competition_id=protocol.competition_id,
                nomination_id=protocol.nomination_id,
            )
        }
        order = self._running_order.running_order(
            competition_id=protocol.competition_id,
            nomination_id=protocol.nomination_id,
        )
        if order:
            program_id = self._running_order.program_id_for(
                competition_id=protocol.competition_id,
                nomination_id=protocol.nomination_id,
            )
            if program_id is not None and protocol.seeded_from_program_id is None:
                protocol.seeded_from(program_id, now=now)
            for entry in order:
                # An act in the programme that is no longer a competing entry (withdrawn
                # after the running order was printed) gets no row: a protocol may not
                # name a result for something that did not compete.
                if entry.submission_id in taken or entry.submission_id not in available:
                    continue
                protocol.add_row(
                    row_id=uuid.uuid4(),
                    submission_id=entry.submission_id,
                    number=entry.number,
                    now=now,
                )
                taken.add(entry.submission_id)
        for performance in available.values():
            if performance.submission_id in taken:
                continue
            protocol.add_row(
                row_id=uuid.uuid4(),
                submission_id=performance.submission_id,
                now=now,
            )
            taken.add(performance.submission_id)

    def _require_competed(self, protocol: Protocol, submission_id: uuid.UUID) -> CatalogPerformance:
        """The act must be a competing act of this protocol's nomination."""
        for performance in self._catalog.competing_performances(
            competition_id=protocol.competition_id,
            nomination_id=protocol.nomination_id,
        ):
            if performance.submission_id == submission_id:
                return performance
        raise PerformanceNotAvailableError(f"Act {submission_id} did not compete in this protocol's nomination.")

    def _mint_slug(self) -> PublicSlug:
        for _ in range(_SLUG_ATTEMPTS):
            candidate = self._slugs.new_slug()
            if not self._protocols.slug_taken(candidate):
                return PublicSlug(candidate)
        raise SlugUnavailableError("Could not mint a free public slug; please retry.")

    def _resolve_performances(self, rows: Sequence[ProtocolRow]) -> dict[uuid.UUID, CatalogPerformance]:
        ids = [row.submission_id for row in rows]
        return self._catalog.performances_by_id(ids) if ids else {}

    @staticmethod
    def _column_views(columns: Sequence[ProtocolColumn]) -> tuple[ColumnView, ...]:
        return tuple(ColumnView(key=column.value, label=COLUMN_LABELS[column]) for column in columns)

    @staticmethod
    def _award_options() -> tuple[AwardOptionView, ...]:
        """The award vocabulary, in order of seniority."""
        return tuple(
            AwardOptionView(value=kind.value, label=kind.label, seniority=kind.seniority)
            for kind in sorted(AwardKind, key=lambda kind: kind.seniority)
        )

    def _cells(
        self,
        row: ProtocolRow,
        performance: CatalogPerformance | None,
        columns: Sequence[ProtocolColumn],
    ) -> tuple[str, ...]:
        """Render one live row as plain text, one cell per requested column."""
        return tuple(self._cell(column, number=row.number, award=row.award, performance=performance) for column in columns)

    def _published_cells(
        self,
        result: PublishedResult,
        performance: CatalogPerformance | None,
        columns: Sequence[ProtocolColumn],
    ) -> tuple[str, ...]:
        """Render one published line the same way, from the frozen verdict.

        Deliberately the same renderer as the live table: the organizer's export and the
        public page must never disagree about what a cell says, and two renderers is how they
        would come to.
        """
        return tuple(self._cell(column, number=result.number, award=result.award, performance=performance) for column in columns)

    @staticmethod
    def _cell(
        column: ProtocolColumn,
        *,
        number: int,
        award: AwardKind | None,
        performance: CatalogPerformance | None,
    ) -> str:
        """Render one cell of the table as plain text.

        Every column resolves to a string - including the empty one - so a client renders a
        row without knowing what any column means. A row whose act has been withdrawn renders
        blanks rather than a placeholder that would read like missing data.
        """
        match column:
            case ProtocolColumn.POSITION:
                return str(number)
            case ProtocolColumn.PARTICIPANT:
                return (performance.lead_participant or "") if performance is not None else ""
            case ProtocolColumn.TITLE:
                if performance is not None:
                    return performance.title
                # The row holds the place of an act that is gone from Applications. Saying
                # so beats a blank line the organizer cannot account for.
                return "Выступление удалено"
            case ProtocolColumn.AWARD:
                return award.label if award is not None else ""
            case ProtocolColumn.NOMINATION:
                return (performance.nomination or "") if performance is not None else ""
            case ProtocolColumn.DISCIPLINE:
                return (performance.discipline or "") if performance is not None else ""
            case ProtocolColumn.PARTICIPANT_GROUP:
                return (performance.participant_group or "") if performance is not None else ""
            case ProtocolColumn.AGE_CATEGORY:
                return (performance.age_category or "") if performance is not None else ""
            case ProtocolColumn.PARTICIPATION_FORMAT:
                return (performance.participation_format or "") if performance is not None else ""
            case ProtocolColumn.TEACHERS:
                return ", ".join(performance.teachers) if performance is not None else ""
            case ProtocolColumn.ORGANIZATION:
                return (performance.organization or "") if performance is not None else ""
        return ""

    def _summary(self, protocol: Protocol) -> ProtocolSummaryView:
        return ProtocolSummaryView(
            id=str(protocol.id),
            competition_id=str(protocol.competition_id),
            nomination_id=str(protocol.nomination_id),
            nomination=self._catalog.nomination_title(protocol.nomination_id),
            name=str(protocol.name),
            status=protocol.status.value,
            row_count=len(protocol.rows),
            decided_count=len(protocol.decided_rows),
            revision=protocol.revision,
            slug=str(protocol.slug) if protocol.slug is not None else None,
            path=PUBLIC_PROTOCOL_PATH.format(slug=protocol.slug) if protocol.slug is not None else None,
            published_at=protocol.published_at,
            has_unpublished_changes=protocol.has_unpublished_changes,
            created_at=protocol.created_at,
            updated_at=protocol.updated_at,
        )

    def _detail(self, protocol: Protocol) -> ProtocolDetailView:
        performances = self._resolve_performances(protocol.rows)
        return ProtocolDetailView(
            id=str(protocol.id),
            competition_id=str(protocol.competition_id),
            nomination_id=str(protocol.nomination_id),
            nomination=self._catalog.nomination_title(protocol.nomination_id),
            competition_title=self._catalog.competition_title(protocol.competition_id),
            name=str(protocol.name),
            status=protocol.status.value,
            rows=tuple(self._row_view(row, performances.get(row.submission_id)) for row in protocol.rows),
            available_columns=self._column_views(tuple(ProtocolColumn)),
            public_columns=self._column_views(protocol.public_columns),
            award_options=self._award_options(),
            revision=protocol.revision,
            slug=str(protocol.slug) if protocol.slug is not None else None,
            path=PUBLIC_PROTOCOL_PATH.format(slug=protocol.slug) if protocol.slug is not None else None,
            published_at=protocol.published_at,
            has_unpublished_changes=protocol.has_unpublished_changes,
            seeded_from_program_id=str(protocol.seeded_from_program_id) if protocol.seeded_from_program_id else None,
            created_at=protocol.created_at,
            updated_at=protocol.updated_at,
            version=protocol.version,
        )

    @staticmethod
    def _row_view(row: ProtocolRow, performance: CatalogPerformance | None) -> ProtocolRowView:
        return ProtocolRowView(
            id=str(row.id),
            number=row.number,
            submission_id=str(row.submission_id),
            title=performance.title if performance is not None else "Выступление удалено",
            award=row.award.value if row.award is not None else None,
            award_label=row.award.label if row.award is not None else None,
            lead_participant=performance.lead_participant if performance is not None else None,
            participants=performance.participants if performance is not None else (),
            teachers=performance.teachers if performance is not None else (),
            nomination=performance.nomination if performance is not None else None,
            discipline=performance.discipline if performance is not None else None,
            age_category=performance.age_category if performance is not None else None,
            participant_group=performance.participant_group if performance is not None else None,
            participation_format=performance.participation_format if performance is not None else None,
            organization=performance.organization if performance is not None else None,
            missing_performance=performance is None,
        )
