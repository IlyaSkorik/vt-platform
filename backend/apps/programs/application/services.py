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
from collections.abc import Callable, Sequence
from datetime import datetime, timedelta
from enum import StrEnum
from pathlib import PurePosixPath
from typing import Final

from apps.programs.application.commands import (
    AddBlockCommand,
    AddColumnCommand,
    AddPerformanceCommand,
    AnnotateItemCommand,
    AnnounceProgramCommand,
    ArrangementPayload,
    ArrangeProgramCommand,
    CreateProgramCommand,
    CreateShareCommand,
    EditItemCommand,
    FillCellsCommand,
    HostReorderCommand,
    MarkBackstageCommand,
    RenameColumnCommand,
    ReorderItemsCommand,
    SetItemProgressCommand,
    UpdateProgramCommand,
    UpdateShareCommand,
)
from apps.programs.application.dto import (
    AnnouncementView,
    ArchiveFileView,
    ArrangementView,
    ColumnView,
    ProgramArchiveView,
    ProgramDetailView,
    ProgramItemView,
    ProgramShareView,
    ProgramSummaryView,
    ProgramTableView,
    PublicProgramRowView,
    PublicProgramView,
    SchedulePosition,
)
from apps.programs.application.interfaces import (
    CatalogApplicant,
    CatalogPerformance,
    Clock,
    PerformanceCatalog,
    PerformanceSchedule,
    ProgramNotifier,
    ProgramRepository,
    SlugFactory,
    TableRenderer,
)
from apps.programs.application.rendering import clock as _clock
from apps.programs.domain.arrangement import ArrangedItem, ArrangementCandidate, arrange
from apps.programs.domain.entities import Program, ProgramItem, ProgramShare
from apps.programs.domain.exceptions import (
    ExportUnavailableError,
    InvalidProgramDataError,
    NoRestorePointError,
    PerformanceNotAvailableError,
    ProgramConcurrencyError,
    ProgramNotFoundError,
    ProgramShareNotFoundError,
    RunningOrderNotControllableError,
    SlugUnavailableError,
)
from apps.programs.domain.schedule import ScheduledItem, build_schedule, total_duration_seconds
from apps.programs.domain.value_objects import (
    COLUMN_LABELS,
    DEFAULT_AWARD_SECONDS,
    DEFAULT_AWARD_TITLE,
    DEFAULT_BREAK_SECONDS,
    DEFAULT_BREAK_TITLE,
    DEFAULT_GROUPING,
    DEFAULT_OPENING_SECONDS,
    DEFAULT_OPENING_TITLE,
    ArrangementBlock,
    ArrangementSettings,
    BreakRule,
    CellValue,
    ColumnRef,
    ColumnTitle,
    GroupingAxis,
    HostNote,
    ItemDuration,
    ItemTitle,
    PerformanceOrder,
    ProgramColumn,
    ProgramItemKind,
    ProgramItemProgress,
    ProgramName,
    PublicSlug,
    ShareName,
    TimeBuffer,
    parse_column_refs,
)

__all__ = ["PUBLIC_PROGRAM_PATH", "ProgramService"]

#: The client-side route a public slug resolves to. Rendered into API responses so
#: the organizer can copy a link without the frontend re-deriving the URL shape.
PUBLIC_PROGRAM_PATH = "/program/{slug}"

#: How many times a partial settings edit is replayed on a program that moved underneath.
#: Two, not more: one retry covers the single overlapping write that actually happens,
#: and a loop that keeps trying would hide a program being written to continuously.
_UPDATE_ATTEMPTS: Final = 2

#: How many times to re-roll a slug before giving up. A collision needs two of ~57
#: random bits to coincide, so a single retry is already generous; the loop exists so
#: the failure is an explicit error instead of an integrity error from the database.
_SLUG_ATTEMPTS = 8


def _uuid(value: str, *, what: str) -> uuid.UUID:
    try:
        return uuid.UUID(str(value))
    except (ValueError, TypeError, AttributeError) as exc:
        raise InvalidProgramDataError(f"{what} must be a UUID, got {value!r}.") from exc


def _duration(seconds: int) -> str:
    minutes, remainder = divmod(max(0, seconds), 60)
    return f"{minutes}:{remainder:02d}"


#: Characters a file name may not carry into an archive. Slashes would invent folders
#: and the rest are what Windows refuses outright, which is where these files are
#: usually unpacked.
_FILENAME_FORBIDDEN: Final = str.maketrans(dict.fromkeys('/\\:*?"<>|', " "))


def _safe(text: str) -> str:
    """``text`` as a file name: no separators, no double spaces, not empty."""
    cleaned = " ".join(text.translate(_FILENAME_FORBIDDEN).split())
    return cleaned or "—"


def _act_label(number: int, performance: CatalogPerformance | None) -> str:
    """``01 — Иванова Анна — Вальс``: the number first, because that is what is cued.

    Every performer the entry listed, not just the first: a folder named after one half
    of a duet is a folder the sound desk cannot match to the act in front of it.
    """
    title = performance.title if performance is not None else ""
    performers = ", ".join(performance.participants) if performance is not None else ""
    parts = [f"{number:02d}", *(part for part in (performers, title) if part)]
    return _safe(" — ".join(parts))


def _extension(reference: str) -> str:
    """The uploaded file's suffix, lower-cased, so players still recognise the track."""
    return PurePosixPath(reference).suffix.lower()


def _stored_name(reference: str, *, fallback: str) -> str:
    """The applicant's own file name, as it should appear inside the act's folder.

    Storage keeps the uploaded name as the last segment of the key, and that is the most
    useful thing to show: inside a folder already titled with the number and the performer,
    ``track.mp3`` and ``photo-2.jpg`` say which file is which, where a repeated act label
    would not. Sanitised, so nothing in the name can climb out of its folder; a key with no
    usable tail falls back to the act's own label.
    """
    name = _safe(PurePosixPath(reference).name)
    return name if PurePosixPath(name).suffix else f"{fallback}{_extension(reference)}"


def _enum[E: StrEnum](enum: type[E], raw: str | None, *, default: E, what: str) -> E:
    """Read one wire value onto its domain enum, or fall back to the default.

    An unknown value is a rejected request rather than a silent default: a client that
    sends ``"BY_AGE"`` where the contract says ``"AGE_ASC"`` has a bug, and quietly
    generating a differently-ordered festival would hide it.
    """
    if raw is None:
        return default
    try:
        return enum(raw)
    except ValueError as exc:
        raise InvalidProgramDataError(f"Unknown {what}: {raw!r}.") from exc


def _block(title: str | None, seconds: int | None, *, default_title: str, default_seconds: int) -> ArrangementBlock | None:
    """One optional service block, present as soon as the organizer said anything about it.

    Naming it or timing it is the way to switch it on, so the common case ("да, открытие,
    как обычно") is one tick on a form rather than a title and a duration typed out.
    """
    if title is None and seconds is None:
        return None
    return ArrangementBlock.of(title or default_title, seconds=seconds if seconds is not None else default_seconds)


def _arrangement_settings(payload: ArrangementPayload | None, *, saved: ArrangementSettings | None) -> ArrangementSettings:
    """The rules one generation run uses.

    No payload means "the rules this programme was last built from", and the defaults
    for one that has never been generated - which is the whole of what "пересобрать"
    has to mean. A payload that *is* present is read as complete, so every field it
    leaves out takes the domain default rather than a saved value the organizer can no
    longer see on the form.
    """
    if payload is None:
        return saved if saved is not None else ArrangementSettings()
    rule = _enum(BreakRule, payload.break_rule, default=BreakRule.NONE, what="break rule")
    return ArrangementSettings(
        grouping=(
            tuple(_enum(GroupingAxis, axis, default=GroupingAxis.NOMINATION, what="grouping axis") for axis in payload.grouping)
            if payload.grouping is not None
            else DEFAULT_GROUPING
        ),
        order_within_group=_enum(PerformanceOrder, payload.order_within_group, default=PerformanceOrder.AGE_ASC, what="performance order"),
        break_rule=rule,
        break_after_seconds=payload.break_after_seconds or 0,
        break_after_items=payload.break_after_items or 0,
        break_block=(
            _block(
                payload.break_title,
                payload.break_duration_seconds,
                default_title=DEFAULT_BREAK_TITLE,
                default_seconds=DEFAULT_BREAK_SECONDS,
            )
            # A rule that fires needs something to insert, so choosing one is itself the
            # request for a break - the title and the length are the optional part.
            or (ArrangementBlock.of(DEFAULT_BREAK_TITLE, seconds=DEFAULT_BREAK_SECONDS) if rule is not BreakRule.NONE else None)
        ),
        repeat_gap=payload.repeat_gap or 0,
        opens_with=_block(
            payload.opening_title,
            payload.opening_duration_seconds,
            default_title=DEFAULT_OPENING_TITLE,
            default_seconds=DEFAULT_OPENING_SECONDS,
        ),
        closes_with=_block(
            payload.award_title,
            payload.award_duration_seconds,
            default_title=DEFAULT_AWARD_TITLE,
            default_seconds=DEFAULT_AWARD_SECONDS,
        ),
    )


def _arrangement_view(settings: ArrangementSettings | None) -> ArrangementView | None:
    """Render saved rules back onto the flat shape the settings form reads."""
    if settings is None:
        return None
    return ArrangementView(
        grouping=tuple(axis.value for axis in settings.grouping),
        order_within_group=settings.order_within_group.value,
        break_rule=settings.break_rule.value,
        break_after_seconds=settings.break_after_seconds,
        break_after_items=settings.break_after_items,
        break_title=str(settings.break_block.title) if settings.break_block else None,
        break_duration_seconds=settings.break_block.duration.seconds if settings.break_block else None,
        repeat_gap=settings.repeat_gap,
        opening_title=str(settings.opens_with.title) if settings.opens_with else None,
        opening_duration_seconds=settings.opens_with.duration.seconds if settings.opens_with else None,
        award_title=str(settings.closes_with.title) if settings.closes_with else None,
        award_duration_seconds=settings.closes_with.duration.seconds if settings.closes_with else None,
    )


def _candidate(performance: CatalogPerformance) -> ArrangementCandidate:
    """Hand one catalog act to the generator in the vocabulary the rules are written in."""
    return ArrangementCandidate(
        submission_id=performance.submission_id,
        duration_seconds=performance.duration_seconds,
        title=performance.title,
        nomination=performance.nomination,
        discipline=performance.discipline,
        age_category=performance.age_category,
        age_order=performance.age_order,
        participant_group=performance.participant_group,
        participation_format=performance.participation_format,
        organization=performance.organization,
        participants=performance.participants,
    )


def _arranged_to_item(entry: ArrangedItem) -> ProgramItem:
    """Turn one planned slot into the aggregate's own item, with a fresh identity."""
    if entry.submission_id is not None:
        return ProgramItem.performance(item_id=uuid.uuid4(), submission_id=entry.submission_id, duration=entry.duration)
    if entry.title is None:
        raise InvalidProgramDataError("A generated block must carry a title.")
    return ProgramItem.block(item_id=uuid.uuid4(), kind=entry.kind, title=entry.title, duration=entry.duration)


class ProgramService:
    """Everything an organizer does to a program, and the one public read."""

    def __init__(
        self,
        *,
        programs: ProgramRepository,
        catalog: PerformanceCatalog,
        clock: Clock,
        slugs: SlugFactory,
        tables: TableRenderer | None = None,
        notifier: ProgramNotifier | None = None,
        schedule: PerformanceSchedule | None = None,
    ) -> None:
        self._programs = programs
        self._catalog = catalog
        self._clock = clock
        self._slugs = slugs
        # Optional: every use case except the export works without a renderer, and a test
        # that never exports should not have to supply one. Same for the notifier and the
        # announcement.
        self._tables = tables
        self._notifier = notifier
        # Optional for the same reason, and with one extra consequence worth naming: a
        # service assembled without it builds programmes that never tell Applications an
        # act was scheduled. That is the right default for a unit test of the running
        # order and the wrong one in production, where `composition` always supplies it.
        self._schedule = schedule

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
        """Rename, re-buffer or re-time a program.

        Retried once if the program moved underneath, because this command is a
        *partial* edit and replaying it is exactly right: "set the start to 10:00" means
        the same thing on a fresher copy, and nothing of the other write is lost. The
        settings are also the one thing an organizer changes while the rest of the
        programme is being worked on — the buffer set a moment before a row is dragged —
        so a conflict here is both the likeliest and the least interesting to report.
        """
        for attempt in range(_UPDATE_ATTEMPTS):
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
            try:
                self._programs.save(program)
            except ProgramConcurrencyError:
                if attempt + 1 < _UPDATE_ATTEMPTS:
                    continue
                raise
            return self._detail(program)
        raise AssertionError("unreachable")  # pragma: no cover - the loop always returns or raises

    def delete_program(self, program_id: str) -> None:
        """Soft-delete a program — refused while it still has public links.

        The guard lives in the aggregate (:meth:`Program.delete`), so the rule holds
        whoever asks; this edge only has to carry the refusal back out.
        """
        program = self._load(program_id)
        before = self._slots_of(program)
        program.delete(now=self._clock.utcnow())
        self._programs.save(program)
        # A deleted programme holds nothing, whatever its items still say in memory:
        # the rows went down with it, which is what `submission_ids_with_slots` reads.
        self._sync_schedule(before, frozenset())

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
        before = self._slots_of(program)
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
        self._sync_schedule(before, self._slots_of(program))
        return self._detail(program)

    def fill_from_scope(self, program_id: str) -> ProgramDetailView:
        """Append every remaining competing act of the program's scope, in catalog order.

        The bulk half of building a program: one action turns "все выступления" of a
        nomination into slots, after which the organizer only rearranges. Acts already
        in the program keep their place - filling twice adds nothing.
        """
        now = self._clock.utcnow()
        program = self._load(program_id)
        before = self._slots_of(program)
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
        self._sync_schedule(before, self._slots_of(program))
        return self._detail(program)

    def arrange_program(self, command: ArrangeProgramCommand) -> ProgramDetailView:
        """Build the whole running order from rules, replacing whatever stood there.

        The alternative to "Добавить все, потом тащить мышью сто строк": the organizer
        states how the day should read - grouped by nomination and age, младшие вперёд,
        перерыв каждые полтора часа, один участник не два номера подряд - and the
        programme arrives in that shape, still entirely editable afterwards.

        The scope is the programme's own, so this never pulls in an act from a different
        nomination, and the rules are kept on the aggregate so the next rebuild needs no
        form at all.
        """
        now = self._clock.utcnow()
        program = self._load(command.program_id)
        before = self._slots_of(program)
        settings = _arrangement_settings(command.settings, saved=program.arrangement)
        candidates = tuple(
            _candidate(performance)
            for performance in self._catalog.competing_performances(
                competition_id=program.competition_id,
                nomination_id=program.nomination_id,
            )
        )
        plan = arrange(candidates=candidates, settings=settings, buffer=program.buffer)
        program.rebuild([_arranged_to_item(entry) for entry in plan], settings=settings, now=now)
        self._programs.save(program)
        self._sync_schedule(before, self._slots_of(program))
        return self._detail(program)

    def undo_arrange(self, program_id: str) -> ProgramDetailView:
        """Put back the running order the last rebuild replaced.

        Regeneration is a replacement and says so, but "I understood the warning" and "I
        meant to press that" are different things, and only the second one is a decision.
        The replaced slots are soft-deleted rather than erased, so the whole of the
        previous order is still on disk under the instant it was retired at; this reads it
        back and hands it to the aggregate.

        Deliberately not a general undo stack. One step, consumed when used, and only for
        the one action that destroys an afternoon of work in a single click.
        """
        now = self._clock.utcnow()
        program = self._load(program_id)
        before = self._slots_of(program)
        if program.rebuilt_at is None:
            raise NoRestorePointError("Отменять нечего: программу не пересобирали, либо отмену уже применили.")
        program.restore_order(self._programs.items_retired_at(program.id, program.rebuilt_at), now=now)
        self._programs.save(program)
        self._sync_schedule(before, self._slots_of(program))
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
        before = self._slots_of(program)
        program.remove_item(_uuid(item_id, what="itemId"), now=now)
        self._programs.save(program)
        self._sync_schedule(before, self._slots_of(program))
        return self._detail(program)

    def reorder_items(self, command: ReorderItemsCommand) -> ProgramDetailView:
        """Apply a new running order, leaving every permanent number where it is."""
        now = self._clock.utcnow()
        program = self._load(command.program_id)
        program.reorder([_uuid(item_id, what="itemId") for item_id in command.item_ids], now=now)
        self._programs.save(program)
        return self._detail(program)

    def renumber_items(self, program_id: str) -> ProgramDetailView:
        """Re-issue numbers 1..N along the current order (the explicit, opt-in reset)."""
        now = self._clock.utcnow()
        program = self._load(program_id)
        program.renumber_sequentially(now=now)
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
            columns=parse_column_refs(command.columns),
            item_ids=[_uuid(item_id, what="itemId") for item_id in command.item_ids],
            controls_running_order=command.controls_running_order,
        )
        self._programs.save(program)
        return self._detail(program), self._share_view(share, program)

    def update_share(self, command: UpdateShareCommand) -> tuple[ProgramDetailView, ProgramShareView]:
        """Rename an edition, re-column it, or change what it may control."""
        now = self._clock.utcnow()
        program = self._load(command.program_id)
        share_id = _uuid(command.share_id, what="shareId")
        if command.name is not None:
            program.rename_share(share_id, ShareName(command.name), now=now)
        if command.columns is not None:
            program.set_share_columns(share_id, parse_column_refs(command.columns), now=now)
        if command.controls_running_order is not None:
            program.set_share_control(share_id, allowed=command.controls_running_order, now=now)
        self._programs.save(program)
        return self._detail(program), self._share_view(program.share(share_id), program)

    # ------------------------------------------------------------------
    # Custom columns
    # ------------------------------------------------------------------

    def add_column(self, command: AddColumnCommand) -> ProgramDetailView:
        """Add a column of the organizer's own to this programme's table."""
        now = self._clock.utcnow()
        program = self._load(command.program_id)
        program.add_custom_column(column_id=uuid.uuid4(), title=ColumnTitle(command.title), now=now)
        self._programs.save(program)
        return self._detail(program)

    def rename_column(self, command: RenameColumnCommand) -> ProgramDetailView:
        """Rename a custom column, keeping every value in it."""
        now = self._clock.utcnow()
        program = self._load(command.program_id)
        program.rename_custom_column(_uuid(command.column_id, what="columnId"), ColumnTitle(command.title), now=now)
        self._programs.save(program)
        return self._detail(program)

    def remove_column(self, *, program_id: str, column_id: str) -> ProgramDetailView:
        """Drop a custom column, its values, and its place on every published link."""
        now = self._clock.utcnow()
        program = self._load(program_id)
        program.remove_custom_column(_uuid(column_id, what="columnId"), now=now)
        self._programs.save(program)
        return self._detail(program)

    def fill_cells(self, command: FillCellsCommand) -> ProgramDetailView:
        """Write the hand-filled cells of one row."""
        now = self._clock.utcnow()
        program = self._load(command.program_id)
        item_id = _uuid(command.item_id, what="itemId")
        for raw_key, raw_value in command.values:
            ref = ColumnRef.parse(raw_key)
            if not ref.is_custom or ref.custom_id is None:
                raise InvalidProgramDataError("Эту колонку нельзя заполнить вручную.")
            program.fill_cell(item_id=item_id, column_id=ref.custom_id, value=CellValue(str(raw_value)), now=now)
        self._programs.save(program)
        return self._detail(program)

    # ------------------------------------------------------------------
    # Export
    # ------------------------------------------------------------------

    def program_table(self, *, program_id: str, columns: Sequence[str] = ()) -> ProgramTableView:
        """Render the programme as a plain table of the chosen columns.

        The organizer's own cut of the programme, for printing or sending on. It goes through
        the same cell renderer as a published link, so an exported table and a screen never
        disagree about what a cell says. An empty selection means every column the programme
        has - an export is for the organizer, who is allowed to see all of it.

        The columns come out in the order they were asked for, unlike a published edition:
        a printed page is laid out for one purpose by the person printing it, and which
        column the eye reaches first is that person's decision, not the programme's.
        """
        program = self._load(program_id)
        chosen = program.select_columns(parse_column_refs(columns)) if columns else program.columns
        rows = self._rows(program, program.items, chosen)
        nomination = self._catalog.nomination_title(program.nomination_id) if program.nomination_id else None
        competition = self._catalog.competition_title(program.competition_id)
        return ProgramTableView(
            title=str(program.name),
            subtitle=" · ".join(part for part in (competition, nomination) if part) or None,
            starts_at=program.starts_at,
            total_seconds=total_duration_seconds(items=program.items, buffer=program.buffer),
            columns=self._column_views(program, chosen),
            rows=tuple(cells for _item, cells in rows),
        )

    def export_pdf(self, *, program_id: str, columns: Sequence[str] = ()) -> bytes:
        """Render the programme table as a PDF document."""
        if self._tables is None:
            raise ExportUnavailableError("Экспорт таблицы сейчас недоступен.")
        return self._tables.render(self.program_table(program_id=program_id, columns=columns))

    def music_archive(self, *, program_id: str) -> ProgramArchiveView:
        """Every backing track of the programme, named for the running order.

        What the sound desk needs the morning of the event: the tracks in the order they
        will be played, under names that say which number each belongs to, and a list of
        the slots that brought no track at all.
        """
        return self._archive(program_id=program_id, references=self._catalog.music_references)

    def media_archive(self, *, program_id: str) -> ProgramArchiveView:
        """Every video and photograph of the programme, named for the running order.

        The screen operator's counterpart to the sound desk's archive, and a separate
        download for a reason: handing either of them the other's files means searching
        through material they will never play.
        """
        return self._archive(program_id=program_id, references=self._catalog.media_references)

    def _archive(
        self,
        *,
        program_id: str,
        references: Callable[[Sequence[uuid.UUID]], dict[uuid.UUID, tuple[str, ...]]],
    ) -> ProgramArchiveView:
        """One archive of whatever files ``references`` resolves, in running order.

        A slot's own number leads the name when the programme has frozen its numbers;
        before that it has none, and the position in the running order stands in — the
        same number the organizer is looking at on screen.
        """
        program = self._load(program_id)
        acts = [item for item in program.items if item.submission_id is not None]
        performances = self._resolve_performances(acts)
        resolved = references([item.submission_id for item in acts if item.submission_id is not None])

        files: list[ArchiveFileView] = []
        missing: list[str] = []
        ordinal = 0
        for item in program.items:
            if item.submission_id is None:
                continue
            # The slot's own number, or - on a programme that has somehow never been
            # numbered - its place among the acts. Never its row index: that counts the
            # breaks too, and the desk cues from the numbers on the running order.
            ordinal += 1
            number = item.number or ordinal
            performance = performances.get(item.submission_id)
            label = _act_label(number, performance)
            act_files = resolved.get(item.submission_id, ())
            if not act_files:
                missing.append(label)
                continue
            for reference in act_files:
                # A folder per act, everything of that act inside it. An act brings several
                # files often enough — two phonograms, a video and a handful of photographs —
                # and a flat archive of two hundred names sorted by number is worse to work
                # from than twenty folders. Two files that arrive under one name still both
                # survive: the archive writer numbers the collision inside the folder.
                files.append(
                    ArchiveFileView(
                        number=number,
                        filename=f"{label}/{_stored_name(reference, fallback=label)}",
                        reference=reference,
                    )
                )

        return ProgramArchiveView(title=str(program.name), files=tuple(files), missing=tuple(missing))

    # ------------------------------------------------------------------
    # The day itself (driven from the host's link)
    # ------------------------------------------------------------------

    def ensure_host_control(self, slug: str) -> None:
        """Refuse a link that was not granted control, before anything else is read.

        Exists so the edge can answer the authorization question *first*. Both host
        writes used to validate the request body before reaching the service, which
        meant a link with no control over the day got a 400 about its payload rather
        than the refusal it had earned — and a reader of that 400 could reasonably
        conclude, as one did, that there was no gate at all. The refusal is now the
        same 404 whatever the body looks like.

        The cost is a second resolution of the slug on the write paths, which is a
        row by unique index on an operation a host performs a few times an hour.
        """
        self._host_program(slug)

    def set_item_progress(self, command: SetItemProgressCommand) -> PublicProgramView:
        """Mark how far one slot has got, from the host's own link.

        Answers with the host's view of the programme, so their screen redraws from the
        same payload every other screen is polling.
        """
        now = self._clock.utcnow()
        program, share = self._host_program(command.slug)
        try:
            progress = ProgramItemProgress(str(command.progress).upper())
        except ValueError as exc:
            raise InvalidProgramDataError("Неизвестный статус хода программы.") from exc
        program.set_item_progress(_uuid(command.item_id, what="itemId"), progress, now=now)
        self._programs.save(program)
        return self._public_view(program, share)

    def set_item_backstage(self, command: MarkBackstageCommand) -> PublicProgramView:
        """Note that one act is behind the stage, from the host's own link.

        The question the running order cannot answer. A host finds out that №14 is not in
        the building thirty seconds before announcing it, and the only record of who *is*
        there has until now been her memory and a biro on a printed page. This is that
        page: hers, kept on the same screen as the order she will have to change because
        of it, and rendered into no other edition's payload.
        """
        now = self._clock.utcnow()
        program, share = self._host_program(command.slug)
        program.mark_item_backstage(_uuid(command.item_id, what="itemId"), command.backstage, now=now)
        self._programs.save(program)
        return self._public_view(program, share)

    def annotate_item(self, command: AnnotateItemCommand) -> PublicProgramView:
        """Write the host's own note against one slot (an empty note clears it)."""
        now = self._clock.utcnow()
        program, share = self._host_program(command.slug)
        program.annotate_item(_uuid(command.item_id, what="itemId"), HostNote(command.note), now=now)
        self._programs.save(program)
        return self._public_view(program, share)

    def host_reorder(self, command: HostReorderCommand) -> PublicProgramView:
        """Rearrange what is still to come, from the host's link, mid-event.

        The numbers are frozen by now - publishing froze them - so the rows move and the
        participants' numbers stay theirs, which is exactly right in front of an audience.
        """
        now = self._clock.utcnow()
        program, share = self._host_program(command.slug)
        program.reorder([_uuid(item_id, what="itemId") for item_id in command.item_ids], now=now)
        self._programs.save(program)
        return self._public_view(program, share)

    def reset_progress(self, program_id: str) -> ProgramDetailView:
        """Put every slot back to pending (the organizer's reset after a rehearsal)."""
        now = self._clock.utcnow()
        program = self._load(program_id)
        program.reset_progress(now=now)
        self._programs.save(program)
        return self._detail(program)

    def announce_program(self, command: AnnounceProgramCommand) -> AnnouncementView:
        """Write to everyone in a published edition: the programme is up, here it is.

        The gap this closes is the ordinary one between a festival and the people in it:
        the running order exists, the link exists, and nobody knows. Until now the
        organizer pasted it into however many chats they could reach, and whoever was in
        none of them found out on the day.

        **One letter per applicant, listing every act of theirs the edition shows.** A
        studio that entered thirty numbers is told once, with thirty lines — which is
        both what a person wants to open and the difference between one message and
        thirty against a provider that counts its allowance per minute.

        Each line carries the number and the time, because those are what the letter is
        *for*: «№14, 11:47» is the whole of what a participant needs, and the link is
        there for everything else. Service blocks carry neither and are left out — a
        letter is addressed to people, and nobody is announced for the interval.

        A failed address does not stop the others: an applicant who cannot be written to
        is counted and the sending continues, because forty letters delivered is a
        better outcome than none plus an error about the forty-first.
        """
        if self._notifier is None:  # pragma: no cover - the composition root always supplies one
            raise InvalidProgramDataError("Рассылка недоступна: не настроена отправка писем.")
        program = self._load(command.program_id)
        share = program.share(_uuid(command.share_id, what="shareId"))
        items = [item for item in program.items_for(share) if item.kind.takes_number]
        schedule = {entry.item.id: entry for entry in build_schedule(items=program.items, buffer=program.buffer, starts_at=program.starts_at)}
        performances = self._resolve_performances(items)
        applicants = self._catalog.applicants_for([item.submission_id for item in items if item.submission_id is not None])

        # Grouped before anything is sent: the unit of this message is the applicant,
        # and the order inside each letter is the order of the day.
        lines_by_applicant: dict[uuid.UUID, tuple[CatalogApplicant, list[tuple[str, str, str]]]] = {}
        skipped = 0
        for item in items:
            applicant = applicants.get(item.submission_id) if item.submission_id is not None else None
            if applicant is None:
                skipped += 1
                continue
            entry = schedule.get(item.id)
            _, lines = lines_by_applicant.setdefault(applicant.user_id, (applicant, []))
            lines.append(
                (
                    str(item.number or (entry.position if entry is not None else 0)),
                    _clock(entry.starts_at) if entry is not None else "",
                    self._item_title(item, performances.get(item.submission_id) if item.submission_id is not None else None),
                )
            )

        competition_title = self._catalog.competition_title(program.competition_id)
        program_url = PUBLIC_PROGRAM_PATH.format(slug=share.slug)
        notified = 0
        for applicant, lines in lines_by_applicant.values():
            self._notifier.notify_program_published(
                user_id=applicant.user_id,
                email=applicant.email,
                applicant_name=applicant.name,
                competition_title=competition_title,
                program_name=str(program.name),
                starts_at=program.starts_at,
                slots=tuple(lines),
                program_url=program_url,
                note=(command.note or "").strip() or None,
            )
            notified += 1
        return AnnouncementView(notified=notified, acts=len(items) - skipped, skipped=skipped)

    def remove_share(self, *, program_id: str, share_id: str) -> ProgramDetailView:
        """Revoke a public edition; its link stops resolving at once."""
        now = self._clock.utcnow()
        program = self._load(program_id)
        program.remove_share(_uuid(share_id, what="shareId"), now=now)
        self._programs.save(program)
        return self._detail(program)

    def public_program_stamp(self, slug: str) -> str | None:
        """A short string that changes whenever this edition's table could have changed.

        The cheap half of the public read. Every mutation of a programme touches the
        aggregate's version - a row marked on stage, a reorder, a republished column
        set - so the version plus the edition's id identify a rendered table exactly,
        and two editions of one programme never share a stamp because their columns
        differ.

        What it deliberately does *not* cover is data owned by other contexts: a
        participant renamed in Applications does not move this version. The caller
        bounds that staleness with time rather than pretending otherwise.
        """
        stamp = self._programs.stamp_for_slug(slug)
        if stamp is None:
            return None
        share_id, version = stamp
        return f"{share_id.hex}.{version}"

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
        return self._public_view(program, share)

    def _public_view(self, program: Program, share: ProgramShare) -> PublicProgramView:
        """Render one published edition of a programme as its table."""
        columns = share.columns
        items = program.items_for(share)
        rows = self._rows(program, items, columns)
        return PublicProgramView(
            name=str(share.name),
            slug=str(share.slug),
            competition_title=self._catalog.competition_title(program.competition_id),
            nomination=self._catalog.nomination_title(program.nomination_id) if program.nomination_id else None,
            starts_at=self._first_start(program, items) or program.starts_at,
            total_seconds=total_duration_seconds(items=items, buffer=program.buffer),
            columns=self._column_views(program, columns),
            rows=tuple(
                PublicProgramRowView(
                    kind=item.kind.value,
                    cells=cells,
                    progress=item.progress.value,
                    # Only the host needs a handle on a row, and only the host's link gets
                    # one: a read-only edition carries no ids at all. Her two private marks
                    # are gated on the same answer, and for a stronger reason - this is the
                    # line past which «кто за сценой» and whatever she wrote to herself stop
                    # existing, so there is nothing for another screen to reveal.
                    id=str(item.id) if share.controls_running_order else None,
                    backstage=item.backstage if share.controls_running_order else None,
                    note=str(item.host_note) if share.controls_running_order else None,
                )
                for item, cells in rows
            ),
            controls_running_order=share.controls_running_order,
        )

    def _rows(
        self,
        program: Program,
        items: Sequence[ProgramItem],
        columns: Sequence[ColumnRef],
    ) -> tuple[tuple[ProgramItem, tuple[str, ...]], ...]:
        """Render ``items`` into ``(item, cells)`` pairs.

        The single place a programme becomes text, shared by the public screen and every
        export: one renderer means an exported table and a screen can never disagree about
        what a cell says.

        The item travels back beside its own cells rather than a copy of a few of its
        fields. A published row needs its kind, its progress and - on the host's edition -
        two marks that are in no column of the table at all, and a tuple that grows a slot
        each time a caller needs one more field is how a shared renderer stops being one.
        """
        schedule_by_item = {entry.item.id: entry for entry in build_schedule(items=program.items, buffer=program.buffer, starts_at=program.starts_at)}
        performances = self._resolve_performances(items)
        rendered: list[tuple[ProgramItem, tuple[str, ...]]] = []
        for position, item in enumerate(items, start=1):
            entry = schedule_by_item[item.id]
            performance = performances.get(item.submission_id) if item.submission_id is not None else None
            rendered.append(
                (
                    item,
                    tuple(self._cell(column, item=item, performance=performance, position=position, starts_at=entry.starts_at) for column in columns),
                )
            )
        return tuple(rendered)

    def _first_start(self, program: Program, items: Sequence[ProgramItem]) -> datetime | None:
        """When the first of ``items`` begins, on the whole programme's timeline."""
        if not items:
            return None
        schedule = {entry.item.id: entry for entry in build_schedule(items=program.items, buffer=program.buffer, starts_at=program.starts_at)}
        return schedule[items[0].id].starts_at

    def _host_program(self, slug: str) -> tuple[Program, ProgramShare]:
        """Resolve a host link, refusing anything that was not granted control.

        An unknown slug and a read-only one are the same refusal, so a link cannot be
        probed for whether it happens to be the host's.
        """
        found = self._programs.get_by_slug(slug)
        if found is None:
            raise RunningOrderNotControllableError("По этой ссылке программа не найдена.")
        program, share_id = found
        try:
            share = program.share(share_id)
        except ProgramShareNotFoundError as exc:
            raise RunningOrderNotControllableError("По этой ссылке программа не найдена.") from exc
        if not share.controls_running_order:
            raise RunningOrderNotControllableError("По этой ссылке нельзя управлять ходом программы.")
        return program, share

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    def _slots_of(self, program: Program) -> frozenset[uuid.UUID]:
        """Which acts this programme holds — the input to the schedule diff."""
        return frozenset(program.performance_submission_ids)

    def _sync_schedule(self, before: frozenset[uuid.UUID], after: frozenset[uuid.UUID]) -> None:
        """Tell Applications which acts gained a slot and which lost their last one.

        Driven from a diff rather than hooked onto each use case: a programme is
        mutated six different ways — one act added, the whole scope filled, a slot
        pulled, the order rebuilt from rules, a rebuild undone, the programme deleted
        — and every one of them ends in the same ``save``. Six hooks would be six
        chances to forget one, and the one forgotten is a status that silently
        disagrees with the programme beside it.

        Losing a slot here is not the same as losing every slot. A competition runs
        several programmes and an act pulled from one may still stand in another, so
        the departed ids are checked against the rest before anything is unscheduled.
        """
        if self._schedule is None:
            return
        gained = after - before
        if gained:
            self._schedule.mark_scheduled(tuple(gained))
        lost = before - after
        if lost:
            still_seated = self._programs.submission_ids_with_slots(tuple(lost))
            orphaned = tuple(submission_id for submission_id in lost if submission_id not in still_seated)
            if orphaned:
                self._schedule.mark_unscheduled(orphaned)

    def _load(self, program_id: str) -> Program:
        program = self._programs.get(_uuid(program_id, what="programId"))
        if program is None:
            raise ProgramNotFoundError("Программа не найдена.")
        return program

    def _kind(self, raw: str) -> ProgramItemKind:
        try:
            kind = ProgramItemKind(str(raw).upper())
        except ValueError as exc:
            raise InvalidProgramDataError("Неизвестный тип строки программы.") from exc
        if kind.binds_performance:
            raise InvalidProgramDataError("Выступление добавляется отдельным действием, а не как блок программы.")
        return kind

    def _require_available(self, program: Program, submission_id: uuid.UUID) -> CatalogPerformance:
        """The act must be a competing act of this program's competition and scope."""
        for performance in self._catalog.competing_performances(
            competition_id=program.competition_id,
            nomination_id=program.nomination_id,
        ):
            if performance.submission_id == submission_id:
                return performance
        raise PerformanceNotAvailableError("Это выступление не участвует в той части фестиваля, для которой составлена программа.")

    def _mint_slug(self) -> PublicSlug:
        for _ in range(_SLUG_ATTEMPTS):
            candidate = self._slugs.new_slug()
            if not self._programs.slug_taken(candidate):
                return PublicSlug(candidate)
        raise SlugUnavailableError("Не удалось создать публичную ссылку. Попробуйте ещё раз.")

    def _resolve_performances(self, items: Sequence[ProgramItem]) -> dict[uuid.UUID, CatalogPerformance]:
        ids = [item.submission_id for item in items if item.submission_id is not None]
        return self._catalog.performances_by_id(ids) if ids else {}

    @staticmethod
    def _column_views(program: Program, refs: Sequence[ColumnRef]) -> tuple[ColumnView, ...]:
        """Name each column: built-ins from the domain's headers, custom ones by title."""
        titles = {column.id: str(column.title) for column in program.custom_columns}
        views: list[ColumnView] = []
        for ref in refs:
            if ref.is_custom and ref.custom_id is not None:
                views.append(ColumnView(key=ref.key, label=titles.get(ref.custom_id, "—"), custom=True))
            elif ref.builtin is not None:
                views.append(ColumnView(key=ref.key, label=COLUMN_LABELS[ref.builtin]))
        return tuple(views)

    def _cell(
        self,
        ref: ColumnRef,
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
        if ref.is_custom:
            # A hand-filled column: whatever the organizer typed, or nothing.
            return str(item.value_in(ref.custom_id)) if ref.custom_id is not None else ""
        column = ref.builtin
        if column is None:  # pragma: no cover - guaranteed by ColumnRef
            return ""
        match column:
            case ProgramColumn.POSITION:
                # The participant's permanent number, not the row's index: a programme
                # that was rearranged legitimately reads 2, 3, 5, 4. A break carries no
                # number at all and gets a blank - it is a gap in the running order, not
                # an act anybody was told to be ready for.
                if not item.kind.takes_number:
                    return ""
                return str(item.number or position)
            case ProgramColumn.TIME:
                return _clock(starts_at)
            case ProgramColumn.PARTICIPANT:
                # Everyone the entry listed, not just the first of them: a duet is two
                # performer rows and both names belong in «Участник». How many people a
                # collective puts on stage is a different fact, with its own column.
                return ", ".join(performance.participants) if performance is not None else ""
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
            case ProgramColumn.PARTICIPANT_COUNT:
                # A collective is one row in the entry and twenty people on stage, so this
                # is the headcount the applicant stated - never the number of rows.
                if performance is None or performance.participant_count <= 0:
                    return ""
                return str(performance.participant_count)
            case ProgramColumn.AGE_CATEGORY:
                return (performance.age_category or "") if performance is not None else ""
            case ProgramColumn.PARTICIPATION_FORMAT:
                return (performance.participation_format or "") if performance is not None else ""
            case ProgramColumn.TEACHERS:
                return ", ".join(performance.teachers) if performance is not None else ""
            case ProgramColumn.ORGANIZATION:
                return (performance.organization or "") if performance is not None else ""
            case ProgramColumn.CONTACTS:
                return ", ".join(performance.contacts) if performance is not None else ""
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
            available_columns=self._column_views(program, program.columns),
            numbers_frozen=program.numbers_frozen,
            numbers_frozen_at=program.numbers_frozen_at,
            total_seconds=total,
            ends_at=program.starts_at + timedelta(seconds=total) if program.starts_at is not None else None,
            arrangement=_arrangement_view(program.arrangement),
            can_undo_arrange=program.can_undo_rebuild,
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
            number=item.number or entry.position,
            duration_seconds=item.duration.seconds,
            schedule=SchedulePosition(
                position=entry.position,
                offset_seconds=entry.offset_seconds,
                slot_seconds=entry.slot_seconds,
                starts_at=entry.starts_at,
                ends_at=entry.ends_at,
            ),
            submission_id=str(item.submission_id) if item.submission_id is not None else None,
            participants=performance.participants if performance is not None else (),
            participant_count=performance.participant_count if performance is not None else 0,
            teachers=performance.teachers if performance is not None else (),
            contacts=performance.contacts if performance is not None else (),
            nomination=performance.nomination if performance is not None else None,
            discipline=performance.discipline if performance is not None else None,
            age_category=performance.age_category if performance is not None else None,
            participant_group=performance.participant_group if performance is not None else None,
            participation_format=performance.participation_format if performance is not None else None,
            organization=performance.organization if performance is not None else None,
            comment=performance.comment if performance is not None else None,
            missing_performance=item.submission_id is not None and performance is None,
            custom_values=tuple(
                (ColumnRef.custom(column_id).key, str(value)) for column_id, value in item.custom_values.items() if not value.is_blank
            ),
            progress=item.progress.value,
        )

    def _share_view(self, share: ProgramShare, program: Program) -> ProgramShareView:
        selected = program.items_for(share)
        return ProgramShareView(
            id=str(share.id),
            name=str(share.name),
            slug=str(share.slug),
            path=PUBLIC_PROGRAM_PATH.format(slug=share.slug),
            columns=self._column_views(program, share.columns),
            item_count=len(selected),
            covers_whole_program=share.covers_whole_program,
            controls_running_order=share.controls_running_order,
            created_at=share.created_at,
        )
