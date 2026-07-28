"""Use cases of the Programs bounded context.

One service over one aggregate: every operation loads the program, asks the domain
to change it, saves it, and renders the result. The rules live in the aggregate and
in :mod:`apps.programs.domain.schedule` - this layer only orchestrates, and reaches
other contexts exclusively through :class:`PerformanceCatalog`.

The write methods all return the freshly rendered
:class:`~apps.programs.application.dto.ProgramDetailView`. A constructor UI needs the
whole recomputed timetable after every edit anyway - inserting a break changes the
start time of everything after it - so returning it removes a follow-up request and
with it any chance of the client rendering a stale schedule.
"""

from __future__ import annotations

import uuid
from collections.abc import Sequence
from datetime import datetime, timedelta

from apps.programs.application.commands import (
    AddBlockCommand,
    AddPerformanceCommand,
    CreateProgramCommand,
    CreateShareCommand,
    EditItemCommand,
    ReorderItemsCommand,
    UpdateProgramCommand,
    UpdateShareCommand,
)
from apps.programs.application.dto import (
    ColumnView,
    ProgramDetailView,
    ProgramItemView,
    ProgramShareView,
    ProgramSummaryView,
    PublicProgramRowView,
    PublicProgramView,
    SchedulePosition,
)
from apps.programs.application.interfaces import (
    CatalogPerformance,
    Clock,
    PerformanceCatalog,
    ProgramRepository,
    SlugFactory,
)
from apps.programs.domain.entities import Program, ProgramItem, ProgramShare
from apps.programs.domain.exceptions import (
    InvalidProgramDataError,
    PerformanceNotAvailableError,
    ProgramNotFoundError,
    ProgramShareNotFoundError,
    SlugUnavailableError,
)
from apps.programs.domain.schedule import ScheduledItem, build_schedule, total_duration_seconds
from apps.programs.domain.value_objects import (
    COLUMN_LABELS,
    ItemDuration,
    ItemTitle,
    ProgramColumn,
    ProgramItemKind,
    ProgramName,
    PublicSlug,
    ShareName,
    TimeBuffer,
    parse_columns,
)

__all__ = ["PUBLIC_PROGRAM_PATH", "ProgramService"]

#: The client-side route a public slug resolves to. Rendered into API responses so
#: the organizer can copy a link without the frontend re-deriving the URL shape.
PUBLIC_PROGRAM_PATH = "/program/{slug}"

#: How many times to re-roll a slug before giving up. A collision needs two of ~57
#: random bits to coincide, so a single retry is already generous; the loop exists so
#: the failure is an explicit error instead of an integrity error from the database.
_SLUG_ATTEMPTS = 8


def _uuid(value: str, *, what: str) -> uuid.UUID:
    try:
        return uuid.UUID(str(value))
    except (ValueError, TypeError, AttributeError) as exc:
        raise InvalidProgramDataError(f"{what} must be a UUID, got {value!r}.") from exc


def _clock(moment: datetime | None) -> str:
    """A cell's time of day, or blank when the programme is not timed yet."""
    return "" if moment is None else moment.strftime("%H:%M")


def _duration(seconds: int) -> str:
    minutes, remainder = divmod(max(0, seconds), 60)
    return f"{minutes}:{remainder:02d}"


class ProgramService:
    """Everything an organizer does to a program, and the one public read."""

    def __init__(
        self,
        *,
        programs: ProgramRepository,
        catalog: PerformanceCatalog,
        clock: Clock,
        slugs: SlugFactory,
    ) -> None:
        self._programs = programs
        self._catalog = catalog
        self._clock = clock
        self._slugs = slugs

    # ------------------------------------------------------------------
    # Programs
    # ------------------------------------------------------------------

    def create_program(self, command: CreateProgramCommand) -> ProgramDetailView:
        """Create an empty program to build a running order in."""
        now = self._clock.utcnow()
        program = Program.create(
            program_id=uuid.uuid4(),
            competition_id=_uuid(command.competition_id, what="competitionId"),
            name=ProgramName(command.name),
            now=now,
            nomination_id=_uuid(command.nomination_id, what="nominationId") if command.nomination_id else None,
            starts_at=command.starts_at,
            buffer=TimeBuffer(int(command.buffer_seconds)),
        )
        self._programs.save(program)
        return self._detail(program)

    def list_programs(self, *, competition_id: str, nomination_id: str | None = None) -> tuple[ProgramSummaryView, ...]:
        """Every program of a competition, optionally narrowed to one nomination."""
        programs = self._programs.list_for_competition(
            competition_id=_uuid(competition_id, what="competitionId"),
            nomination_id=_uuid(nomination_id, what="nominationId") if nomination_id else None,
        )
        return tuple(self._summary(program) for program in programs)

    def get_program(self, program_id: str) -> ProgramDetailView:
        """One program with its recomputed timetable."""
        return self._detail(self._load(program_id))

    def update_program(self, command: UpdateProgramCommand) -> ProgramDetailView:
        """Rename, re-buffer or re-time a program."""
        now = self._clock.utcnow()
        program = self._load(command.program_id)
        if command.name is not None:
            program.rename(ProgramName(command.name), now=now)
        if command.buffer_seconds is not None:
            program.set_buffer(TimeBuffer(int(command.buffer_seconds)), now=now)
        if command.clear_starts_at:
            program.set_start(None, now=now)
        elif command.starts_at is not None:
            program.set_start(command.starts_at, now=now)
        self._programs.save(program)
        return self._detail(program)

    def delete_program(self, program_id: str) -> None:
        """Soft-delete a program; every public link into it stops resolving."""
        program = self._load(program_id)
        program.delete(now=self._clock.utcnow())
        self._programs.save(program)

    # ------------------------------------------------------------------
    # Items
    # ------------------------------------------------------------------

    def candidates(self, program_id: str) -> tuple[CatalogPerformance, ...]:
        """The competing acts of this program's scope that have no slot yet.

        This is the left-hand side of "Вокал → все выступления → программа": what the
        organizer can still pull in, already excluding what is in the program.
        """
        program = self._load(program_id)
        taken = set(program.performance_submission_ids)
        available = self._catalog.competing_performances(
            competition_id=program.competition_id,
            nomination_id=program.nomination_id,
        )
        return tuple(performance for performance in available if performance.submission_id not in taken)

    def add_performance(self, command: AddPerformanceCommand) -> ProgramDetailView:
        """Give one act a slot, seeding the slot's length from the act."""
        now = self._clock.utcnow()
        program = self._load(command.program_id)
        submission_id = _uuid(command.submission_id, what="submissionId")
        performance = self._require_available(program, submission_id)
        duration = ItemDuration(int(command.duration_seconds)) if command.duration_seconds is not None else ItemDuration(performance.duration_seconds)
        program.add_performance(
            item_id=uuid.uuid4(),
            submission_id=submission_id,
            duration=duration,
            now=now,
            position=command.position,
        )
        self._programs.save(program)
        return self._detail(program)

    def fill_from_scope(self, program_id: str) -> ProgramDetailView:
        """Append every remaining competing act of the program's scope, in catalog order.

        The bulk half of building a program: one action turns "все выступления" of a
        nomination into slots, after which the organizer only rearranges. Acts already
        in the program keep their place - filling twice adds nothing.
        """
        now = self._clock.utcnow()
        program = self._load(program_id)
        taken = set(program.performance_submission_ids)
        for performance in self._catalog.competing_performances(
            competition_id=program.competition_id,
            nomination_id=program.nomination_id,
        ):
            if performance.submission_id in taken:
                continue
            program.add_performance(
                item_id=uuid.uuid4(),
                submission_id=performance.submission_id,
                duration=ItemDuration(performance.duration_seconds),
                now=now,
            )
        self._programs.save(program)
        return self._detail(program)

    def add_block(self, command: AddBlockCommand) -> ProgramDetailView:
        """Insert a break (or any other standalone block) into the running order."""
        now = self._clock.utcnow()
        program = self._load(command.program_id)
        program.add_block(
            item_id=uuid.uuid4(),
            kind=self._kind(command.kind),
            title=ItemTitle(command.title),
            duration=ItemDuration(int(command.duration_seconds)),
            now=now,
            position=command.position,
        )
        self._programs.save(program)
        return self._detail(program)

    def edit_item(self, command: EditItemCommand) -> ProgramDetailView:
        """Retitle a block or resize any slot."""
        now = self._clock.utcnow()
        program = self._load(command.program_id)
        program.edit_item(
            _uuid(command.item_id, what="itemId"),
            now=now,
            title=ItemTitle(command.title) if command.title is not None else None,
            duration=ItemDuration(int(command.duration_seconds)) if command.duration_seconds is not None else None,
        )
        self._programs.save(program)
        return self._detail(program)

    def remove_item(self, *, program_id: str, item_id: str) -> ProgramDetailView:
        """Remove one slot - a cancelled break, an act pulled from the running order."""
        now = self._clock.utcnow()
        program = self._load(program_id)
        program.remove_item(_uuid(item_id, what="itemId"), now=now)
        self._programs.save(program)
        return self._detail(program)

    def reorder_items(self, command: ReorderItemsCommand) -> ProgramDetailView:
        """Apply a new running order."""
        now = self._clock.utcnow()
        program = self._load(command.program_id)
        program.reorder([_uuid(item_id, what="itemId") for item_id in command.item_ids], now=now)
        self._programs.save(program)
        return self._detail(program)

    # ------------------------------------------------------------------
    # Public editions
    # ------------------------------------------------------------------

    def create_share(self, command: CreateShareCommand) -> tuple[ProgramDetailView, ProgramShareView]:
        """Publish an edition of the program and mint its permanent link."""
        now = self._clock.utcnow()
        program = self._load(command.program_id)
        share = program.add_share(
            share_id=uuid.uuid4(),
            name=ShareName(command.name),
            slug=self._mint_slug(),
            now=now,
            columns=parse_columns(command.columns),
            item_ids=[_uuid(item_id, what="itemId") for item_id in command.item_ids],
        )
        self._programs.save(program)
        return self._detail(program), self._share_view(share, program)

    def update_share(self, command: UpdateShareCommand) -> tuple[ProgramDetailView, ProgramShareView]:
        """Rename an edition and/or change the columns it publishes, keeping its link."""
        now = self._clock.utcnow()
        program = self._load(command.program_id)
        share_id = _uuid(command.share_id, what="shareId")
        if command.name is not None:
            program.rename_share(share_id, ShareName(command.name), now=now)
        if command.columns is not None:
            program.set_share_columns(share_id, parse_columns(command.columns), now=now)
        self._programs.save(program)
        return self._detail(program), self._share_view(program.share(share_id), program)

    def remove_share(self, *, program_id: str, share_id: str) -> ProgramDetailView:
        """Revoke a public edition; its link stops resolving at once."""
        now = self._clock.utcnow()
        program = self._load(program_id)
        program.remove_share(_uuid(share_id, what="shareId"), now=now)
        self._programs.save(program)
        return self._detail(program)

    def public_program(self, slug: str) -> PublicProgramView | None:
        """Resolve a public link into the table it publishes, or ``None``.

        The single unauthenticated read in this context. It renders from the same
        aggregate and the same schedule rule as the organizer view - one running order
        means one timetable, never a second calculation that could disagree.

        Only the edition's own columns are rendered into cells: a column the organizer
        did not publish never reaches the response, so it cannot be read off the wire
        by anyone holding the link.
        """
        found = self._programs.get_by_slug(slug)
        if found is None:
            return None
        program, share_id = found
        try:
            share = program.share(share_id)
        except ProgramShareNotFoundError:
            # Revoked between the slug lookup and the read: the link is simply gone.
            return None
        columns = share.columns
        items = program.items_for(share)
        schedule_by_item = {entry.item.id: entry for entry in build_schedule(items=program.items, buffer=program.buffer, starts_at=program.starts_at)}
        performances = self._resolve_performances(items)
        rows: list[PublicProgramRowView] = []
        first_start: datetime | None = None
        for position, item in enumerate(items, start=1):
            entry = schedule_by_item[item.id]
            if position == 1:
                first_start = entry.starts_at
            performance = performances.get(item.submission_id) if item.submission_id is not None else None
            rows.append(
                PublicProgramRowView(
                    kind=item.kind.value,
                    cells=tuple(
                        self._cell(
                            column,
                            item=item,
                            performance=performance,
                            position=position,
                            starts_at=entry.starts_at,
                        )
                        for column in columns
                    ),
                )
            )
        return PublicProgramView(
            name=str(share.name),
            slug=str(share.slug),
            competition_title=self._catalog.competition_title(program.competition_id),
            nomination=self._catalog.nomination_title(program.nomination_id) if program.nomination_id else None,
            starts_at=first_start or program.starts_at,
            total_seconds=total_duration_seconds(items=items, buffer=program.buffer),
            columns=tuple(ColumnView(key=column.value, label=COLUMN_LABELS[column]) for column in columns),
            rows=tuple(rows),
        )

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    def _load(self, program_id: str) -> Program:
        program = self._programs.get(_uuid(program_id, what="programId"))
        if program is None:
            raise ProgramNotFoundError(f"Program {program_id} does not exist.")
        return program

    def _kind(self, raw: str) -> ProgramItemKind:
        try:
            kind = ProgramItemKind(str(raw).upper())
        except ValueError as exc:
            raise InvalidProgramDataError(f"{raw!r} is not a known program item kind.") from exc
        if kind.binds_performance:
            raise InvalidProgramDataError("Add a performance slot through the performance endpoint, not as a block.")
        return kind

    def _require_available(self, program: Program, submission_id: uuid.UUID) -> CatalogPerformance:
        """The act must be a competing act of this program's competition and scope."""
        for performance in self._catalog.competing_performances(
            competition_id=program.competition_id,
            nomination_id=program.nomination_id,
        ):
            if performance.submission_id == submission_id:
                return performance
        raise PerformanceNotAvailableError(f"Act {submission_id} is not a competing act of this program's scope.")

    def _mint_slug(self) -> PublicSlug:
        for _ in range(_SLUG_ATTEMPTS):
            candidate = self._slugs.new_slug()
            if not self._programs.slug_taken(candidate):
                return PublicSlug(candidate)
        raise SlugUnavailableError("Could not mint a free public slug; please retry.")

    def _resolve_performances(self, items: Sequence[ProgramItem]) -> dict[uuid.UUID, CatalogPerformance]:
        ids = [item.submission_id for item in items if item.submission_id is not None]
        return self._catalog.performances_by_id(ids) if ids else {}

    def _cell(
        self,
        column: ProgramColumn,
        *,
        item: ProgramItem,
        performance: CatalogPerformance | None,
        position: int,
        starts_at: datetime | None,
    ) -> str:
        """Render one cell of the table as plain text.

        Every column resolves to a string here - including the empty one - so a client
        renders a row without knowing what any column means. A break has no participant
        and no age category, and gets blanks rather than a placeholder that would read
        like missing data.
        """
        match column:
            case ProgramColumn.POSITION:
                return str(position)
            case ProgramColumn.TIME:
                return _clock(starts_at)
            case ProgramColumn.PARTICIPANT:
                return performance.lead_participant or "" if performance is not None else ""
            case ProgramColumn.TITLE:
                return self._item_title(item, performance)
            case ProgramColumn.DURATION:
                return _duration(item.duration.seconds)
            case ProgramColumn.NOMINATION:
                return (performance.nomination or "") if performance is not None else ""
            case ProgramColumn.DISCIPLINE:
                return (performance.discipline or "") if performance is not None else ""
            case ProgramColumn.PARTICIPANT_GROUP:
                return (performance.participant_group or "") if performance is not None else ""
            case ProgramColumn.AGE_CATEGORY:
                return (performance.age_category or "") if performance is not None else ""
            case ProgramColumn.PARTICIPATION_FORMAT:
                return (performance.participation_format or "") if performance is not None else ""
            case ProgramColumn.TEACHERS:
                return ", ".join(performance.teachers) if performance is not None else ""
            case ProgramColumn.ORGANIZATION:
                return (performance.organization or "") if performance is not None else ""
            case ProgramColumn.COMMENT:
                return (performance.comment or "") if performance is not None else ""
        return ""

    @staticmethod
    def _item_title(item: ProgramItem, performance: CatalogPerformance | None) -> str:
        if item.title is not None:
            return str(item.title)
        if performance is not None:
            return performance.title
        # A slot whose act is gone still holds its place in the running order; naming
        # it plainly beats an empty line the organizer cannot account for.
        return "Выступление удалено"

    def _summary(self, program: Program) -> ProgramSummaryView:
        return ProgramSummaryView(
            id=str(program.id),
            competition_id=str(program.competition_id),
            nomination_id=str(program.nomination_id) if program.nomination_id else None,
            name=str(program.name),
            buffer_seconds=program.buffer.seconds,
            starts_at=program.starts_at,
            item_count=len(program.items),
            performance_count=len(program.performance_submission_ids),
            total_seconds=total_duration_seconds(items=program.items, buffer=program.buffer),
            share_count=len(program.shares),
            created_at=program.created_at,
            updated_at=program.updated_at,
        )

    def _detail(self, program: Program) -> ProgramDetailView:
        schedule = build_schedule(items=program.items, buffer=program.buffer, starts_at=program.starts_at)
        performances = self._resolve_performances(program.items)
        total = total_duration_seconds(items=program.items, buffer=program.buffer)
        return ProgramDetailView(
            id=str(program.id),
            competition_id=str(program.competition_id),
            nomination_id=str(program.nomination_id) if program.nomination_id else None,
            name=str(program.name),
            buffer_seconds=program.buffer.seconds,
            starts_at=program.starts_at,
            items=tuple(self._item_view(entry, performances) for entry in schedule),
            shares=tuple(self._share_view(share, program) for share in program.shares),
            available_columns=tuple(ColumnView(key=column.value, label=COLUMN_LABELS[column]) for column in ProgramColumn),
            total_seconds=total,
            ends_at=program.starts_at + timedelta(seconds=total) if program.starts_at is not None else None,
            created_at=program.created_at,
            updated_at=program.updated_at,
            version=program.version,
        )

    def _item_view(self, entry: ScheduledItem, performances: dict[uuid.UUID, CatalogPerformance]) -> ProgramItemView:
        item = entry.item
        performance = performances.get(item.submission_id) if item.submission_id is not None else None
        return ProgramItemView(
            id=str(item.id),
            kind=item.kind.value,
            title=self._item_title(item, performance),
            duration_seconds=item.duration.seconds,
            schedule=SchedulePosition(
                position=entry.position,
                offset_seconds=entry.offset_seconds,
                slot_seconds=entry.slot_seconds,
                starts_at=entry.starts_at,
                ends_at=entry.ends_at,
            ),
            submission_id=str(item.submission_id) if item.submission_id is not None else None,
            lead_participant=performance.lead_participant if performance is not None else None,
            participants=performance.participants if performance is not None else (),
            teachers=performance.teachers if performance is not None else (),
            nomination=performance.nomination if performance is not None else None,
            discipline=performance.discipline if performance is not None else None,
            age_category=performance.age_category if performance is not None else None,
            participant_group=performance.participant_group if performance is not None else None,
            participation_format=performance.participation_format if performance is not None else None,
            organization=performance.organization if performance is not None else None,
            comment=performance.comment if performance is not None else None,
            missing_performance=item.submission_id is not None and performance is None,
        )

    @staticmethod
    def _share_view(share: ProgramShare, program: Program) -> ProgramShareView:
        selected = program.items_for(share)
        return ProgramShareView(
            id=str(share.id),
            name=str(share.name),
            slug=str(share.slug),
            path=PUBLIC_PROGRAM_PATH.format(slug=share.slug),
            columns=tuple(ColumnView(key=column.value, label=COLUMN_LABELS[column]) for column in share.columns),
            item_count=len(selected),
            covers_whole_program=share.covers_whole_program,
            created_at=share.created_at,
        )
