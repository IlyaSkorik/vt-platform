"""Use-case tests for the Programs bounded context (in-memory ports, no database).

Covers the flows an organizer actually performs: build a program from a nomination,
insert and remove a break, change the buffer, reorder, publish a public edition, and
read one back through its link.
"""

from __future__ import annotations

import uuid
from dataclasses import replace
from datetime import UTC, datetime, timedelta

import pytest

from apps.programs.application.commands import (
    AddBlockCommand,
    AddColumnCommand,
    AddPerformanceCommand,
    ArrangementPayload,
    ArrangeProgramCommand,
    CreateProgramCommand,
    CreateShareCommand,
    EditItemCommand,
    FillCellsCommand,
    ReorderItemsCommand,
    UpdateProgramCommand,
    UpdateShareCommand,
)
from apps.programs.application.interfaces import CatalogPerformance
from apps.programs.application.rendering import DISPLAY_TZ
from apps.programs.application.services import ProgramService
from apps.programs.domain.exceptions import (
    ExportUnavailableError,
    InvalidProgramDataError,
    NoRestorePointError,
    PerformanceAlreadyInProgramError,
    PerformanceNotAvailableError,
    ProgramHasSharesError,
    ProgramNotFoundError,
    ProgramNumbersFrozenError,
    ReorderMismatchError,
    SlugUnavailableError,
)

from .fakes import FixedClock, InMemoryProgramRepository, ScriptedSlugFactory, StubPerformanceCatalog

COMPETITION_ID = uuid.uuid4()
NOMINATION_ID = uuid.uuid4()
#: Ten in the morning **in the hall**, not in UTC: the cells a link and a PDF carry are
#: rendered in the festival's zone, so a fixture pinned to UTC would assert 13:00.
TEN_AM = datetime(2026, 8, 1, 10, 0, tzinfo=DISPLAY_TZ)


def _act(title: str, seconds: int, *, comment: str | None = None, performer: str = "Иванов Иван") -> CatalogPerformance:
    return CatalogPerformance(
        submission_id=uuid.uuid4(),
        title=title,
        duration_seconds=seconds,
        nomination_id=NOMINATION_ID,
        nomination="Вокал",
        discipline="Эстрадный вокал",
        age_category="10-12 лет",
        participant_group="Соло",
        participation_format="Очно",
        participants=(performer,),
        teachers=("Петрова Мария",),
        organization="Школа №1",
        comment=comment,
        status="ACCEPTED",
    )


class Env:
    """A service wired to in-memory ports."""

    def __init__(
        self,
        *performances: CatalogPerformance,
        slugs: tuple[str, ...] = ("Sound2345",),
        music: dict[uuid.UUID, tuple[str, ...]] | None = None,
        media: dict[uuid.UUID, tuple[str, ...]] | None = None,
    ) -> None:
        self.repository = InMemoryProgramRepository()
        self.catalog = StubPerformanceCatalog(*performances, music=music, media=media)
        self.slugs = ScriptedSlugFactory(*slugs)
        self.service = ProgramService(
            programs=self.repository,
            catalog=self.catalog,
            clock=FixedClock(),
            slugs=self.slugs,
        )

    def program(self, *, starts_at: datetime | None = TEN_AM, buffer_seconds: int = 0) -> str:
        created = self.service.create_program(
            CreateProgramCommand(
                competition_id=str(COMPETITION_ID),
                name="Вокал, 1 отделение",
                nomination_id=str(NOMINATION_ID),
                buffer_seconds=buffer_seconds,
                starts_at=starts_at,
            )
        )
        return created.id


class TestCreateProgram:
    def test_a_program_starts_empty(self) -> None:
        env = Env()
        program = env.service.get_program(env.program())
        assert program.items == ()
        assert program.total_seconds == 0
        assert program.name == "Вокал, 1 отделение"

    def test_a_blank_name_is_refused(self) -> None:
        env = Env()
        with pytest.raises(InvalidProgramDataError):
            env.service.create_program(CreateProgramCommand(competition_id=str(COMPETITION_ID), name="   "))

    def test_a_malformed_competition_id_is_refused(self) -> None:
        env = Env()
        with pytest.raises(InvalidProgramDataError):
            env.service.create_program(CreateProgramCommand(competition_id="not-a-uuid", name="Вокал"))

    def test_programs_are_listed_per_competition(self) -> None:
        env = Env()
        env.program()
        env.program()
        assert len(env.service.list_programs(competition_id=str(COMPETITION_ID))) == 2
        assert env.service.list_programs(competition_id=str(uuid.uuid4())) == ()

    def test_an_unknown_program_is_not_found(self) -> None:
        env = Env()
        with pytest.raises(ProgramNotFoundError):
            env.service.get_program(str(uuid.uuid4()))

    def test_a_deleted_program_is_gone(self) -> None:
        env = Env()
        program_id = env.program()
        env.service.delete_program(program_id)
        with pytest.raises(ProgramNotFoundError):
            env.service.get_program(program_id)


class TestBuildingTheRunningOrder:
    def test_candidates_are_the_acts_without_a_slot(self) -> None:
        first, second = _act("Катюша", 200), _act("Калинка", 180)
        env = Env(first, second)
        program_id = env.program()
        assert {c.submission_id for c in env.service.candidates(program_id)} == {first.submission_id, second.submission_id}

        env.service.add_performance(AddPerformanceCommand(program_id=program_id, submission_id=str(first.submission_id)))
        assert [c.submission_id for c in env.service.candidates(program_id)] == [second.submission_id]

    def test_filling_turns_a_nomination_into_a_running_order(self) -> None:
        env = Env(_act("Катюша", 200), _act("Калинка", 180), _act("Барыня", 240))
        program = env.service.fill_from_scope(env.program())
        assert len(program.items) == 3
        assert all(item.kind == "PERFORMANCE" for item in program.items)

    def test_filling_twice_adds_nothing_and_keeps_the_arrangement(self) -> None:
        env = Env(_act("Катюша", 200), _act("Калинка", 180))
        program_id = env.program()
        first_pass = env.service.fill_from_scope(program_id)
        order = [item.id for item in first_pass.items]
        env.service.reorder_items(ReorderItemsCommand(program_id=program_id, item_ids=tuple(reversed(order))))
        second_pass = env.service.fill_from_scope(program_id)
        assert [item.id for item in second_pass.items] == list(reversed(order))

    def test_a_slot_takes_its_length_from_the_act(self) -> None:
        act = _act("Катюша", 200)
        env = Env(act)
        program = env.service.add_performance(AddPerformanceCommand(program_id=env.program(), submission_id=str(act.submission_id)))
        assert program.items[0].duration_seconds == 200

    def test_a_slot_length_can_be_overridden_for_this_program_only(self) -> None:
        act = _act("Катюша", 200)
        env = Env(act)
        program = env.service.add_performance(
            AddPerformanceCommand(program_id=env.program(), submission_id=str(act.submission_id), duration_seconds=260)
        )
        assert program.items[0].duration_seconds == 260

    def test_an_act_outside_the_scope_cannot_be_scheduled(self) -> None:
        env = Env(_act("Катюша", 200))
        with pytest.raises(PerformanceNotAvailableError):
            env.service.add_performance(AddPerformanceCommand(program_id=env.program(), submission_id=str(uuid.uuid4())))

    def test_the_same_act_cannot_take_two_slots(self) -> None:
        act = _act("Катюша", 200)
        env = Env(act)
        program_id = env.program()
        env.service.add_performance(AddPerformanceCommand(program_id=program_id, submission_id=str(act.submission_id)))
        with pytest.raises(PerformanceAlreadyInProgramError):
            env.service.add_performance(AddPerformanceCommand(program_id=program_id, submission_id=str(act.submission_id)))

    def test_a_slot_carries_the_applicants_note_for_the_organizers(self) -> None:
        act = _act("Катюша", 200, comment="Выход с точки 3")
        env = Env(act)
        program = env.service.add_performance(AddPerformanceCommand(program_id=env.program(), submission_id=str(act.submission_id)))
        assert program.items[0].comment == "Выход с точки 3"


class TestBreaksAndBlocks:
    def test_a_break_is_inserted_and_re_times_the_rest(self) -> None:
        env = Env(_act("Катюша", 180), _act("Калинка", 180))
        program_id = env.program()
        env.service.fill_from_scope(program_id)
        program = env.service.add_block(AddBlockCommand(program_id=program_id, title="Перерыв", duration_seconds=900, position=2))
        assert [item.kind for item in program.items] == ["PERFORMANCE", "BREAK", "PERFORMANCE"]
        assert program.items[1].title == "Перерыв"
        assert program.items[2].schedule.starts_at == TEN_AM + timedelta(minutes=18)

    def test_a_break_can_be_removed_again(self) -> None:
        env = Env()
        program_id = env.program()
        program = env.service.add_block(AddBlockCommand(program_id=program_id, title="Обед", duration_seconds=2400))
        program = env.service.remove_item(program_id=program_id, item_id=program.items[0].id)
        assert program.items == ()

    def test_a_breaks_length_can_be_edited(self) -> None:
        env = Env()
        program_id = env.program()
        program = env.service.add_block(AddBlockCommand(program_id=program_id, title="Перерыв", duration_seconds=900))
        program = env.service.edit_item(EditItemCommand(program_id=program_id, item_id=program.items[0].id, duration_seconds=1200))
        assert program.items[0].duration_seconds == 1200

    def test_a_service_block_of_a_future_kind_already_schedules(self) -> None:
        # The extensibility claim, exercised: an award ceremony needs no new code.
        env = Env()
        program = env.service.add_block(AddBlockCommand(program_id=env.program(), title="Награждение", duration_seconds=1800, kind="AWARD"))
        assert program.items[0].kind == "AWARD"
        assert program.total_seconds == 1800

    def test_a_performance_cannot_be_added_as_a_block(self) -> None:
        env = Env()
        with pytest.raises(InvalidProgramDataError):
            env.service.add_block(AddBlockCommand(program_id=env.program(), title="Номер", duration_seconds=200, kind="PERFORMANCE"))

    def test_an_unknown_kind_is_refused(self) -> None:
        env = Env()
        with pytest.raises(InvalidProgramDataError):
            env.service.add_block(AddBlockCommand(program_id=env.program(), title="Что-то", duration_seconds=200, kind="PARTY"))


class TestScheduleAndBuffer:
    def test_the_schedule_is_recomputed_on_every_write(self) -> None:
        env = Env(_act("A", 200), _act("B", 200), _act("C", 200))
        program = env.service.fill_from_scope(env.program(buffer_seconds=40))
        assert [item.schedule.starts_at for item in program.items] == [
            TEN_AM,
            TEN_AM + timedelta(minutes=4),
            TEN_AM + timedelta(minutes=8),
        ]

    def test_changing_the_buffer_shifts_the_timetable_but_not_the_acts(self) -> None:
        env = Env(_act("A", 180), _act("B", 180))
        program_id = env.program()
        env.service.fill_from_scope(program_id)
        program = env.service.update_program(UpdateProgramCommand(program_id=program_id, buffer_seconds=60))
        assert program.buffer_seconds == 60
        assert program.items[0].duration_seconds == 180
        assert program.items[0].schedule.slot_seconds == 240
        assert program.items[1].schedule.starts_at == TEN_AM + timedelta(minutes=4)

    def test_the_end_of_the_program_is_reported(self) -> None:
        env = Env(_act("A", 600))
        program = env.service.fill_from_scope(env.program(buffer_seconds=60))
        assert program.total_seconds == 660
        assert program.ends_at == TEN_AM + timedelta(minutes=11)

    def test_a_program_without_a_start_time_has_offsets_but_no_clock(self) -> None:
        env = Env(_act("A", 200), _act("B", 200))
        program = env.service.fill_from_scope(env.program(starts_at=None))
        assert [item.schedule.offset_seconds for item in program.items] == [0, 200]
        assert all(item.schedule.starts_at is None for item in program.items)

    def test_a_start_time_can_be_dropped_explicitly(self) -> None:
        env = Env()
        program_id = env.program()
        program = env.service.update_program(UpdateProgramCommand(program_id=program_id, clear_starts_at=True))
        assert program.starts_at is None

    def test_a_buffer_over_the_ceiling_is_refused(self) -> None:
        env = Env()
        with pytest.raises(InvalidProgramDataError):
            env.service.update_program(UpdateProgramCommand(program_id=env.program(), buffer_seconds=7200))


class TestMusicArchive:
    """What the sound desk is handed: the tracks, named for the running order."""

    def test_tracks_are_named_by_number_performer_and_title(self) -> None:
        act = _act("Катюша", 200, performer="Иванова Анна")
        env = Env(act, music={act.submission_id: ("uploads/2026/abc123.mp3",)})
        program_id = env.program()
        env.service.fill_from_scope(program_id)

        archive = env.service.music_archive(program_id=program_id)
        # A folder per act, the uploaded file's own name inside it.
        assert [file.filename for file in archive.files] == ["01 — Иванова Анна — Катюша/abc123.mp3"]
        assert archive.missing == ()

    def test_a_slot_without_a_track_is_reported_rather_than_dropped(self) -> None:
        # A live act needs no backing track, but the person collecting the music has
        # to know which numbers brought none.
        with_track = _act("Катюша", 200, performer="Иванова Анна")
        without = _act("Гимн", 180, performer="Петров Пётр")
        env = Env(with_track, without, music={with_track.submission_id: ("uploads/2026/abc123.mp3",)})
        program_id = env.program()
        env.service.fill_from_scope(program_id)

        archive = env.service.music_archive(program_id=program_id)
        assert len(archive.files) == 1
        assert len(archive.missing) == 1
        assert "Петров Пётр" in archive.missing[0]

    def test_every_track_of_an_act_is_carried(self) -> None:
        act = _act("Катюша", 200, performer="Иванова Анна")
        env = Env(act, music={act.submission_id: ("uploads/a.mp3", "uploads/b.wav")})
        program_id = env.program()
        env.service.fill_from_scope(program_id)

        archive = env.service.music_archive(program_id=program_id)
        assert [file.filename for file in archive.files] == [
            "01 — Иванова Анна — Катюша/a.mp3",
            "01 — Иванова Анна — Катюша/b.wav",
        ]

    def test_a_folder_is_named_after_every_performer_of_the_act(self) -> None:
        # Half a duet's name on the folder is a folder the sound desk cannot match to
        # the pair standing in front of it.
        act = replace(_act("Катюша", 200), participants=("Иванова Анна", "Петров Пётр"))
        env = Env(act, music={act.submission_id: ("uploads/a.mp3",)})
        program_id = env.program()
        env.service.fill_from_scope(program_id)

        archive = env.service.music_archive(program_id=program_id)
        assert archive.files[0].filename == "01 — Иванова Анна, Петров Пётр — Катюша/a.mp3"

    def test_a_slash_in_a_title_does_not_invent_a_nested_folder(self) -> None:
        # There is one folder per act by design; a slash in the title must not turn it into
        # two, or "Зима/Весна" would scatter one act across a tree.
        act = _act("Зима/Весна", 200, performer="Иванова Анна")
        env = Env(act, music={act.submission_id: ("uploads/a.mp3",)})
        program_id = env.program()
        env.service.fill_from_scope(program_id)

        archive = env.service.music_archive(program_id=program_id)
        assert archive.files[0].filename.count("/") == 1
        assert archive.files[0].filename == "01 — Иванова Анна — Зима Весна/a.mp3"

    def test_a_key_with_no_usable_name_falls_back_to_the_act_label(self) -> None:
        # Nothing recognisable at the tail of the key, so the act's own name stands in
        # rather than an extensionless mystery file.
        act = _act("Катюша", 200, performer="Иванова Анна")
        env = Env(act, music={act.submission_id: ("uploads/2026/abc123",)})
        program_id = env.program()
        env.service.fill_from_scope(program_id)

        archive = env.service.music_archive(program_id=program_id)
        assert archive.files[0].filename == "01 — Иванова Анна — Катюша/01 — Иванова Анна — Катюша"

    def test_an_unknown_programme_is_not_found(self) -> None:
        env = Env()
        with pytest.raises(ProgramNotFoundError):
            env.service.music_archive(program_id=str(uuid.uuid4()))


class TestExport:
    """The organizer's own cut of the programme, for printing or sending on."""

    def test_the_table_carries_the_chosen_columns_in_the_order_they_were_asked_for(self) -> None:
        """A printed page is laid out for one purpose by whoever prints it.

        Unlike a published edition, which keeps the canonical order so a column sits in the
        same place on every screen: here the organizer decides what the eye reaches first,
        and the cells follow their headers.
        """
        act = _act("Катюша", 200, comment="Выход с точки 3")
        env = Env(act)
        program_id = env.program()
        env.service.fill_from_scope(program_id)

        table = env.service.program_table(program_id=program_id, columns=("COMMENT", "TITLE", "TIME"))
        assert [column.key for column in table.columns] == ["COMMENT", "TITLE", "TIME"]
        assert table.rows == (("Выход с точки 3", "Катюша", "10:00"),)

    def test_a_table_is_timed_in_the_festivals_zone_not_in_utc(self) -> None:
        """The regression behind "в ссылке время не то, что в программе".

        The instant is stored in UTC and the organizer typed a wall clock, so formatting
        the stored value directly printed the act three hours early on every link and
        every PDF while the constructor, rendering in the browser, read it correctly.
        """
        env = Env(_act("Катюша", 200))
        # Exactly the same moment as TEN_AM, said in UTC.
        program_id = env.program(starts_at=datetime(2026, 8, 1, 7, 0, tzinfo=UTC))
        env.service.fill_from_scope(program_id)

        table = env.service.program_table(program_id=program_id, columns=("TIME",))
        assert table.rows == (("10:00",),)

    def test_a_column_named_twice_is_printed_once(self) -> None:
        # A table cannot carry the same column in two places, and refusing the export over
        # it would be rude — the selection still says plainly what was wanted.
        env = Env(_act("Катюша", 200))
        program_id = env.program()
        env.service.fill_from_scope(program_id)

        table = env.service.program_table(program_id=program_id, columns=("TITLE", "TIME", "TITLE"))
        assert [column.key for column in table.columns] == ["TITLE", "TIME"]

    def test_an_export_without_a_choice_carries_every_column(self) -> None:
        env = Env(_act("Катюша", 200))
        program_id = env.program()
        detail = env.service.fill_from_scope(program_id)

        table = env.service.program_table(program_id=program_id)
        assert len(table.columns) == len(detail.available_columns)

    def test_the_heading_names_the_programme_the_festival_and_the_nomination(self) -> None:
        env = Env(_act("Катюша", 200))
        program_id = env.program()
        env.service.fill_from_scope(program_id)

        table = env.service.program_table(program_id=program_id, columns=("TITLE",))
        assert table.title == "Вокал, 1 отделение"
        assert table.subtitle == "Весенний фестиваль · Вокал"
        assert table.total_seconds == 200

    def test_an_exported_cell_says_what_the_public_screen_says(self) -> None:
        # One cell renderer for both, so a printed programme and a screen cannot disagree.
        env = Env(_act("Катюша", 200), _act("Калинка", 200))
        program_id = env.program(buffer_seconds=40)
        env.service.fill_from_scope(program_id)
        _detail, share = env.service.create_share(CreateShareCommand(program_id=program_id, name="Экран", columns=("TIME", "TITLE")))

        table = env.service.program_table(program_id=program_id, columns=("TIME", "TITLE"))
        public = env.service.public_program(share.slug)
        assert public is not None
        assert table.rows == tuple(row.cells for row in public.rows)

    def test_a_custom_column_is_exportable(self) -> None:
        env = Env(_act("Катюша", 200))
        program_id = env.program()
        detail = env.service.fill_from_scope(program_id)
        key = env.service.add_column(AddColumnCommand(program_id=program_id, title="Микрофон")).available_columns[-1].key
        env.service.fill_cells(FillCellsCommand(program_id=program_id, item_id=detail.items[0].id, values=((key, "на стойке"),)))

        table = env.service.program_table(program_id=program_id, columns=("TITLE", key))
        assert [column.label for column in table.columns] == ["Номер", "Микрофон"]
        assert table.rows == (("Катюша", "на стойке"),)

    def test_an_unknown_column_is_refused(self) -> None:
        env = Env(_act("Катюша", 200))
        program_id = env.program()
        with pytest.raises(InvalidProgramDataError):
            env.service.program_table(program_id=program_id, columns=("NOT_A_COLUMN",))

    def test_exporting_without_a_renderer_says_so_rather_than_crashing(self) -> None:
        env = Env(_act("Катюша", 200))
        program_id = env.program()
        with pytest.raises(ExportUnavailableError):
            env.service.export_pdf(program_id=program_id)


class TestNumbersAndPublication:
    """Numbers are a draft until the programme is published, and a promise afterwards."""

    def test_an_unpublished_programme_renumbers_on_every_reorder(self) -> None:
        env = Env(_act("A", 100), _act("B", 100), _act("C", 100))
        program_id = env.program()
        program = env.service.fill_from_scope(program_id)
        assert program.numbers_frozen is False
        ids = [item.id for item in program.items]

        reordered = env.service.reorder_items(ReorderItemsCommand(program_id=program_id, item_ids=(ids[2], ids[0], ids[1])))
        assert [item.number for item in reordered.items] == [1, 2, 3]

    def test_publishing_freezes_the_numbers(self) -> None:
        env = Env(_act("A", 100))
        program_id = env.program()
        env.service.fill_from_scope(program_id)

        detail, _share = env.service.create_share(CreateShareCommand(program_id=program_id, name="Экран"))
        assert detail.numbers_frozen is True
        assert detail.numbers_frozen_at is not None

    def test_after_publication_a_reorder_keeps_the_numbers(self) -> None:
        env = Env(_act("A", 100), _act("B", 100), _act("C", 100))
        program_id = env.program()
        program = env.service.fill_from_scope(program_id)
        ids = [item.id for item in program.items]
        env.service.create_share(CreateShareCommand(program_id=program_id, name="Экран"))

        reordered = env.service.reorder_items(ReorderItemsCommand(program_id=program_id, item_ids=(ids[0], ids[2], ids[1])))
        assert [item.number for item in reordered.items] == [1, 3, 2]

    def test_after_publication_a_new_act_takes_the_next_free_number(self) -> None:
        first, second = _act("A", 100), _act("B", 100)
        env = Env(first, second)
        program_id = env.program()
        env.service.add_performance(AddPerformanceCommand(program_id=program_id, submission_id=str(first.submission_id)))
        env.service.create_share(CreateShareCommand(program_id=program_id, name="Экран"))

        program = env.service.add_performance(AddPerformanceCommand(program_id=program_id, submission_id=str(second.submission_id)))
        assert [item.number for item in program.items] == [1, 2]

    def test_renumbering_a_published_programme_is_an_explicit_call(self) -> None:
        env = Env(_act("A", 100), _act("B", 100))
        program_id = env.program()
        program = env.service.fill_from_scope(program_id)
        ids = [item.id for item in program.items]
        env.service.create_share(CreateShareCommand(program_id=program_id, name="Экран"))
        env.service.reorder_items(ReorderItemsCommand(program_id=program_id, item_ids=(ids[1], ids[0])))
        assert [item.number for item in env.service.get_program(program_id).items] == [2, 1]

        renumbered = env.service.renumber_items(program_id)
        assert [item.number for item in renumbered.items] == [1, 2]

    def test_the_public_screen_shows_the_frozen_numbers(self) -> None:
        env = Env(_act("A", 100), _act("B", 100), _act("C", 100))
        program_id = env.program()
        program = env.service.fill_from_scope(program_id)
        ids = [item.id for item in program.items]
        _detail, share = env.service.create_share(CreateShareCommand(program_id=program_id, name="Экран"))
        env.service.reorder_items(ReorderItemsCommand(program_id=program_id, item_ids=(ids[0], ids[2], ids[1])))

        public = env.service.public_program(share.slug)
        assert public is not None
        assert [row.cells[0] for row in public.rows] == ["1", "3", "2"]


class TestReorder:
    def test_the_order_is_replaced_and_re_timed(self) -> None:
        env = Env(_act("A", 100), _act("B", 200), _act("C", 300))
        program_id = env.program()
        program = env.service.fill_from_scope(program_id)
        ids = [item.id for item in program.items]
        reordered = env.service.reorder_items(ReorderItemsCommand(program_id=program_id, item_ids=(ids[2], ids[0], ids[1])))
        assert [item.id for item in reordered.items] == [ids[2], ids[0], ids[1]]
        assert [item.schedule.offset_seconds for item in reordered.items] == [0, 300, 400]

    def test_an_incomplete_order_is_refused(self) -> None:
        env = Env(_act("A", 100), _act("B", 200))
        program_id = env.program()
        program = env.service.fill_from_scope(program_id)
        with pytest.raises(ReorderMismatchError):
            env.service.reorder_items(ReorderItemsCommand(program_id=program_id, item_ids=(program.items[0].id,)))


class TestPublicEditions:
    def test_an_edition_is_published_with_a_link(self) -> None:
        env = Env(_act("A", 200), _act("B", 200))
        program_id = env.program()
        program = env.service.fill_from_scope(program_id)
        _detail, share = env.service.create_share(
            CreateShareCommand(program_id=program_id, name="Программа звукорежиссёра", item_ids=(program.items[0].id,))
        )
        assert share.name == "Программа звукорежиссёра"
        assert share.slug == "Sound2345"
        assert share.path == "/program/Sound2345"
        assert share.item_count == 1
        assert share.covers_whole_program is False

    def test_an_edition_without_a_selection_covers_the_whole_program(self) -> None:
        env = Env(_act("A", 200))
        program_id = env.program()
        env.service.fill_from_scope(program_id)
        _detail, share = env.service.create_share(CreateShareCommand(program_id=program_id, name="Экран у сцены"))
        assert share.covers_whole_program is True
        assert share.item_count == 1

    def test_a_taken_slug_is_re_rolled(self) -> None:
        env = Env(_act("A", 200), slugs=("Collide23", "Collide23", "Fresh2345"))
        env.repository.claimed_slugs.add("Collide23")
        program_id = env.program()
        _detail, share = env.service.create_share(CreateShareCommand(program_id=program_id, name="Вторая"))
        assert share.slug == "Fresh2345"
        assert env.slugs.calls == 3

    def test_giving_up_on_slugs_is_an_explicit_error(self) -> None:
        env = Env(slugs=("Collide23",))
        env.repository.claimed_slugs.add("Collide23")
        with pytest.raises(SlugUnavailableError):
            env.service.create_share(CreateShareCommand(program_id=env.program(), name="Не выйдет"))

    def test_many_editions_of_one_program_are_allowed(self) -> None:
        env = Env(_act("A", 200), slugs=("Sound2345", "Host23456", "Jury23456"))
        program_id = env.program()
        env.service.fill_from_scope(program_id)
        for name in ("Звукорежиссёр", "Ведущий", "Жюри"):
            env.service.create_share(CreateShareCommand(program_id=program_id, name=name))
        assert len(env.service.get_program(program_id).shares) == 3

    def test_an_edition_can_be_revoked(self) -> None:
        env = Env(_act("A", 200))
        program_id = env.program()
        env.service.fill_from_scope(program_id)
        _detail, share = env.service.create_share(CreateShareCommand(program_id=program_id, name="Временная"))
        program = env.service.remove_share(program_id=program_id, share_id=share.id)
        assert program.shares == ()
        assert env.service.public_program(share.slug) is None


class TestPublicRead:
    def test_a_link_renders_the_default_columns_with_their_times(self) -> None:
        first, second = _act("Катюша", 200, performer="Иванов Иван"), _act("Калинка", 200, performer="Петров Пётр")
        env = Env(first, second)
        program_id = env.program(buffer_seconds=40)
        program = env.service.fill_from_scope(program_id)
        _detail, share = env.service.create_share(CreateShareCommand(program_id=program_id, name="Для ведущего"))

        public = env.service.public_program(share.slug)
        assert public is not None
        assert public.name == "Для ведущего"
        assert public.competition_title == "Весенний фестиваль"
        assert public.nomination == "Вокал"
        assert [column.key for column in public.columns] == ["POSITION", "TIME", "PARTICIPANT", "TITLE"]
        assert [column.label for column in public.columns] == ["№", "Время", "Участник", "Номер"]
        assert [row.cells for row in public.rows] == [
            ("1", "10:00", "Иванов Иван", "Катюша"),
            ("2", "10:04", "Петров Пётр", "Калинка"),
        ]
        # The organizer's own table says the same time for the same slot.
        assert program.items[0].schedule.starts_at == TEN_AM

    def test_a_partial_edition_keeps_the_real_numbers_and_the_real_times(self) -> None:
        # A cut of the programme is still the programme: the participant published here
        # as номер 2 is номер 2 on every other copy too.
        env = Env(_act("A", 200), _act("B", 200), _act("C", 200))
        program_id = env.program(buffer_seconds=0)
        program = env.service.fill_from_scope(program_id)
        _detail, share = env.service.create_share(
            CreateShareCommand(program_id=program_id, name="Только второй и третий", item_ids=(program.items[1].id, program.items[2].id))
        )
        public = env.service.public_program(share.slug)
        assert public is not None
        assert [row.cells[0] for row in public.rows] == ["2", "3"]
        # The times are the program's, not the edition's: the second act still starts
        # when the first one has finished.
        assert public.rows[0].cells[1] == "10:03"

    def test_breaks_appear_on_a_public_screen(self) -> None:
        env = Env(_act("A", 200))
        program_id = env.program()
        env.service.fill_from_scope(program_id)
        env.service.add_block(AddBlockCommand(program_id=program_id, title="Перерыв", duration_seconds=900))
        _detail, share = env.service.create_share(CreateShareCommand(program_id=program_id, name="Экран"))
        public = env.service.public_program(share.slug)
        assert public is not None
        assert [row.kind for row in public.rows] == ["PERFORMANCE", "BREAK"]
        # A break has no participant and no number, so both cells are blank rather than
        # placeholders - and the next act keeps the number it was promised.
        assert public.rows[1].cells == ("", "10:03", "", "Перерыв")

    def test_an_edition_shows_exactly_the_columns_it_was_published_with(self) -> None:
        # The sound engineer's cut: when, what, how long, and the applicant's notes.
        act = _act("Катюша", 200, comment="Фонограмма начинается не с начала", performer="Иванов Иван")
        env = Env(act)
        program_id = env.program()
        env.service.fill_from_scope(program_id)
        _detail, share = env.service.create_share(
            CreateShareCommand(
                program_id=program_id,
                name="Программа звукорежиссёра",
                columns=("TIME", "TITLE", "DURATION", "COMMENT"),
            )
        )

        public = env.service.public_program(share.slug)
        assert public is not None
        assert [column.key for column in public.columns] == ["TIME", "TITLE", "DURATION", "COMMENT"]
        assert public.rows[0].cells == ("10:00", "Катюша", "3:20", "Фонограмма начинается не с начала")

    def test_a_column_left_out_never_reaches_the_response(self) -> None:
        # The confidentiality property of the whole design: an unpublished column cannot
        # be read off the wire by whoever holds the link.
        act = _act("Катюша", 200, comment="Выход с точки 3", performer="Иванов Иван")
        env = Env(act)
        program_id = env.program()
        env.service.fill_from_scope(program_id)
        _detail, share = env.service.create_share(CreateShareCommand(program_id=program_id, name="Экран у сцены", columns=("TIME", "TITLE")))

        public = env.service.public_program(share.slug)
        assert public is not None
        assert [column.key for column in public.columns] == ["TIME", "TITLE"]
        flattened = [cell for row in public.rows for cell in row.cells]
        assert "Выход с точки 3" not in flattened
        assert "Иванов Иван" not in flattened

    def test_columns_are_published_in_the_order_they_were_sent(self) -> None:
        # The organizer arranges the link for whoever reads it, and a public screen shows
        # exactly that: no scrolling to reach the column the job depends on.
        env = Env(_act("Катюша", 200))
        program_id = env.program()
        env.service.fill_from_scope(program_id)
        _detail, share = env.service.create_share(CreateShareCommand(program_id=program_id, name="Жюри", columns=("TEACHERS", "TITLE", "TIME")))
        public = env.service.public_program(share.slug)
        assert public is not None
        assert [column.key for column in public.columns] == ["TEACHERS", "TITLE", "TIME"]

    def test_every_available_column_can_be_published(self) -> None:
        act = _act("Катюша", 200, comment="Нужен микрофон")
        env = Env(act)
        program_id = env.program(buffer_seconds=30)
        detail = env.service.fill_from_scope(program_id)
        all_columns = tuple(column.key for column in detail.available_columns)
        _detail, share = env.service.create_share(CreateShareCommand(program_id=program_id, name="Всё", columns=all_columns))

        public = env.service.public_program(share.slug)
        assert public is not None
        assert len(public.columns) == len(all_columns)
        cells = dict(zip((column.key for column in public.columns), public.rows[0].cells, strict=True))
        assert cells["POSITION"] == "1"
        assert cells["TIME"] == "10:00"
        assert cells["PARTICIPANT"] == "Иванов Иван"
        assert cells["TITLE"] == "Катюша"
        assert cells["DURATION"] == "3:20"
        assert cells["NOMINATION"] == "Вокал"
        assert cells["DISCIPLINE"] == "Эстрадный вокал"
        assert cells["PARTICIPANT_GROUP"] == "Соло"
        assert cells["AGE_CATEGORY"] == "10-12 лет"
        assert cells["PARTICIPATION_FORMAT"] == "Очно"
        assert cells["TEACHERS"] == "Петрова Мария"
        assert cells["ORGANIZATION"] == "Школа №1"
        assert cells["COMMENT"] == "Нужен микрофон"

    def test_every_performer_of_an_entry_is_named_in_the_participant_column(self) -> None:
        # An entry with two performers is a duet, and a programme that names only the
        # first of them tells the hall the wrong thing about who is on stage.
        duet = replace(_act("Катюша", 200), participants=("Иванова Анна", "Петров Пётр"))
        env = Env(duet)
        program_id = env.program()
        env.service.fill_from_scope(program_id)
        _detail, share = env.service.create_share(CreateShareCommand(program_id=program_id, name="Сцена", columns=("PARTICIPANT",)))

        public = env.service.public_program(share.slug)
        assert public is not None
        assert public.rows[0].cells == ("Иванова Анна, Петров Пётр",)

    def test_an_unknown_column_is_refused(self) -> None:
        env = Env(_act("Катюша", 200))
        with pytest.raises(InvalidProgramDataError):
            env.service.create_share(CreateShareCommand(program_id=env.program(), name="Нет", columns=("SOMETHING",)))

    def test_the_columns_of_a_published_edition_can_be_changed_without_a_new_link(self) -> None:
        env = Env(_act("Катюша", 200))
        program_id = env.program()
        env.service.fill_from_scope(program_id)
        _detail, share = env.service.create_share(CreateShareCommand(program_id=program_id, name="Ведущий", columns=("TIME", "TITLE")))

        _updated_program, updated = env.service.update_share(
            UpdateShareCommand(program_id=program_id, share_id=share.id, columns=("TIME", "PARTICIPANT", "TITLE"))
        )
        assert updated.slug == share.slug
        assert [column.key for column in updated.columns] == ["TIME", "PARTICIPANT", "TITLE"]
        public = env.service.public_program(share.slug)
        assert public is not None
        assert [column.key for column in public.columns] == ["TIME", "PARTICIPANT", "TITLE"]

    def test_an_edition_can_be_renamed_without_touching_its_columns(self) -> None:
        env = Env(_act("Катюша", 200))
        program_id = env.program()
        env.service.fill_from_scope(program_id)
        _detail, share = env.service.create_share(CreateShareCommand(program_id=program_id, name="Черновик", columns=("TIME", "TITLE")))

        _program, updated = env.service.update_share(UpdateShareCommand(program_id=program_id, share_id=share.id, name="Сцена №2"))
        assert updated.name == "Сцена №2"
        assert [column.key for column in updated.columns] == ["TIME", "TITLE"]

    def test_an_unknown_link_resolves_to_nothing(self) -> None:
        assert Env().service.public_program("NoSuchSlug") is None

    def test_a_published_program_refuses_to_be_deleted(self) -> None:
        """A link out is somebody reading, and they are not told when it goes away."""
        env = Env(_act("A", 200))
        program_id = env.program()
        env.service.fill_from_scope(program_id)
        _detail, share = env.service.create_share(CreateShareCommand(program_id=program_id, name="Экран"))

        with pytest.raises(ProgramHasSharesError):
            env.service.delete_program(program_id)
        assert env.service.public_program(share.slug) is not None

    def test_deleting_after_the_links_are_revoked_takes_them_down_for_good(self) -> None:
        env = Env(_act("A", 200))
        program_id = env.program()
        env.service.fill_from_scope(program_id)
        _detail, share = env.service.create_share(CreateShareCommand(program_id=program_id, name="Экран"))
        env.service.remove_share(program_id=program_id, share_id=share.id)
        env.service.delete_program(program_id)
        assert env.service.public_program(share.slug) is None

    def test_an_act_withdrawn_from_the_catalog_still_holds_its_place(self) -> None:
        act = _act("A", 200)
        env = Env(act)
        program_id = env.program()
        env.service.fill_from_scope(program_id)
        env.catalog.performances.clear()
        program = env.service.get_program(program_id)
        assert program.items[0].missing_performance is True
        assert program.items[0].schedule.starts_at == TEN_AM


class TestMediaArchive:
    """The screen operator's archive: the same shape as the sound desk's, other files."""

    def test_collects_video_and_photographs_in_running_order(self) -> None:
        act = _act("Катюша", 200, performer="Иванова Анна")
        env = Env(act, media={act.submission_id: ("uploads/clip.mp4", "uploads/photo.jpg")})
        program_id = env.program()
        env.service.fill_from_scope(program_id)

        archive = env.service.media_archive(program_id=program_id)

        assert [file.filename for file in archive.files] == [
            "01 — Иванова Анна — Катюша/clip.mp4",
            "01 — Иванова Анна — Катюша/photo.jpg",
        ]

    def test_an_act_with_no_media_is_listed_rather_than_omitted(self) -> None:
        # The person collecting the material has to know which numbers to chase; an
        # archive that silently skips them looks complete when it is not.
        act = _act("Живой номер", 180, performer="Петров Иван")
        env = Env(act, media={})
        program_id = env.program()
        env.service.fill_from_scope(program_id)

        archive = env.service.media_archive(program_id=program_id)

        assert archive.files == ()
        assert archive.missing == ("01 — Петров Иван — Живой номер",)

    def test_the_two_archives_do_not_borrow_each_other_s_files(self) -> None:
        # One archive per desk: the sound desk searching through video, or the screen
        # operator through phonograms, is the thing separate downloads exist to avoid.
        act = _act("Катюша", 200, performer="Иванова Анна")
        env = Env(
            act,
            music={act.submission_id: ("uploads/track.mp3",)},
            media={act.submission_id: ("uploads/clip.mp4",)},
        )
        program_id = env.program()
        env.service.fill_from_scope(program_id)

        assert [f.filename for f in env.service.music_archive(program_id=program_id).files] == ["01 — Иванова Анна — Катюша/track.mp3"]
        assert [f.filename for f in env.service.media_archive(program_id=program_id).files] == ["01 — Иванова Анна — Катюша/clip.mp4"]


def _candidate(
    title: str,
    seconds: int,
    *,
    discipline: str = "Эстрадный вокал",
    age_category: str = "10-12 лет",
    age_order: int = 1,
    performer: str = "Иванов Иван",
) -> CatalogPerformance:
    """One competing act, varied along the axes the generator reads."""
    return CatalogPerformance(
        submission_id=uuid.uuid4(),
        title=title,
        duration_seconds=seconds,
        nomination_id=NOMINATION_ID,
        nomination="Вокал",
        discipline=discipline,
        age_category=age_category,
        age_order=age_order,
        participant_group="Соло",
        participation_format="Очно",
        participants=(performer,),
        teachers=("Петрова Мария",),
        organization="Школа №1",
        status="ACCEPTED",
    )


class TestArrangingAProgramme:
    """Generating a whole running order from rules (VT-86)."""

    def test_an_empty_programme_fills_itself_from_its_own_scope(self) -> None:
        env = Env(_candidate("Катюша", 200), _candidate("Калинка", 180))
        program_id = env.program()

        program = env.service.arrange_program(ArrangeProgramCommand(program_id=program_id))

        assert len(program.items) == 2
        assert [item.number for item in program.items] == [1, 2]

    def test_the_rules_decide_the_order(self) -> None:
        env = Env(
            _candidate("старший", 200, age_category="13-15 лет", age_order=2),
            _candidate("младший", 180, age_category="7-9 лет", age_order=0),
        )
        program_id = env.program()

        program = env.service.arrange_program(
            ArrangeProgramCommand(
                program_id=program_id,
                settings=ArrangementPayload(grouping=(), order_within_group="AGE_ASC"),
            )
        )

        assert [item.title for item in program.items] == ["младший", "старший"]

    def test_generating_replaces_whatever_stood_there(self) -> None:
        # The organizer asked for the day the rules describe; a programme half made by
        # hand and half by rule is one neither of them can explain.
        env = Env(_candidate("Катюша", 200))
        program_id = env.program()
        env.service.add_block(AddBlockCommand(program_id=program_id, title="Старый перерыв", duration_seconds=600))

        program = env.service.arrange_program(ArrangeProgramCommand(program_id=program_id))

        assert [item.title for item in program.items] == ["Катюша"]

    def test_a_break_rule_puts_breaks_into_the_running_order(self) -> None:
        env = Env(*(_candidate(name, 180) for name in ("А", "Б", "В")))
        program_id = env.program()

        program = env.service.arrange_program(
            ArrangeProgramCommand(
                program_id=program_id,
                settings=ArrangementPayload(grouping=(), order_within_group="TITLE", break_rule="EVERY_COUNT", break_after_items=2),
            )
        )

        assert [item.title for item in program.items] == ["А", "Б", "Перерыв", "В"]
        assert [item.kind for item in program.items] == ["PERFORMANCE", "PERFORMANCE", "BREAK", "PERFORMANCE"]

    def test_choosing_a_rule_is_itself_the_request_for_a_break(self) -> None:
        # A rule that fires needs something to insert, so the title and the length are
        # the optional part - one knob on the form, not three.
        env = Env(*(_candidate(name, 180) for name in ("А", "Б")))
        program_id = env.program()

        program = env.service.arrange_program(
            ArrangeProgramCommand(
                program_id=program_id,
                settings=ArrangementPayload(grouping=(), break_rule="EVERY_COUNT", break_after_items=1),
            )
        )

        assert [item.title for item in program.items][1] == "Перерыв"
        assert program.arrangement is not None
        assert program.arrangement.break_duration_seconds == 600

    def test_naming_a_service_block_is_how_it_is_switched_on(self) -> None:
        env = Env(_candidate("Катюша", 200))
        program_id = env.program()

        program = env.service.arrange_program(
            ArrangeProgramCommand(
                program_id=program_id,
                settings=ArrangementPayload(opening_title="Открытие фестиваля", award_duration_seconds=1800),
            )
        )

        assert [item.title for item in program.items] == ["Открытие фестиваля", "Катюша", "Награждение"]
        assert [item.duration_seconds for item in program.items] == [900, 200, 1800]

    def test_the_rules_are_kept_so_the_next_rebuild_needs_no_form(self) -> None:
        env = Env(*(_candidate(name, 180) for name in ("А", "Б", "В")))
        program_id = env.program()
        env.service.arrange_program(
            ArrangeProgramCommand(
                program_id=program_id,
                settings=ArrangementPayload(grouping=(), order_within_group="TITLE", break_rule="EVERY_COUNT", break_after_items=2),
            )
        )

        rebuilt = env.service.arrange_program(ArrangeProgramCommand(program_id=program_id))

        assert [item.title for item in rebuilt.items] == ["А", "Б", "Перерыв", "В"]
        assert rebuilt.arrangement is not None
        assert rebuilt.arrangement.break_rule == "EVERY_COUNT"
        assert rebuilt.arrangement.break_after_items == 2

    def test_a_programme_that_was_never_generated_has_no_rules_to_show(self) -> None:
        env = Env(_candidate("Катюша", 200))
        program = env.service.get_program(env.program())
        assert program.arrangement is None

    def test_a_payload_that_is_present_is_read_as_complete(self) -> None:
        # What the organizer sees on the form is what they get: an omitted field takes
        # the default, not the value saved from a run they can no longer see.
        env = Env(*(_candidate(name, 180) for name in ("А", "Б", "В")))
        program_id = env.program()
        env.service.arrange_program(
            ArrangeProgramCommand(
                program_id=program_id,
                settings=ArrangementPayload(grouping=(), break_rule="EVERY_COUNT", break_after_items=2),
            )
        )

        program = env.service.arrange_program(ArrangeProgramCommand(program_id=program_id, settings=ArrangementPayload(grouping=())))

        assert all(item.kind == "PERFORMANCE" for item in program.items)
        assert program.arrangement is not None
        assert program.arrangement.break_rule == "NONE"

    def test_a_published_programme_refuses_to_regenerate(self) -> None:
        # Its numbers are out in the world: a participant has been told "вы номер 12".
        env = Env(*(_candidate(name, 180) for name in ("А", "Б")))
        program_id = env.program()
        env.service.arrange_program(ArrangeProgramCommand(program_id=program_id))
        env.service.create_share(CreateShareCommand(program_id=program_id, name="Для зала"))

        with pytest.raises(ProgramNumbersFrozenError):
            env.service.arrange_program(ArrangeProgramCommand(program_id=program_id))

    def test_an_unknown_rule_is_a_rejected_request_rather_than_a_silent_default(self) -> None:
        env = Env(_candidate("Катюша", 200))
        program_id = env.program()

        with pytest.raises(InvalidProgramDataError):
            env.service.arrange_program(ArrangeProgramCommand(program_id=program_id, settings=ArrangementPayload(order_within_group="BY_AGE")))

    def test_generating_never_reaches_outside_the_programme_s_nomination(self) -> None:
        mine = _candidate("Катюша", 200)
        theirs = CatalogPerformance(
            submission_id=uuid.uuid4(),
            title="Чужой номер",
            duration_seconds=180,
            nomination_id=uuid.uuid4(),
            nomination="Хореография",
            status="ACCEPTED",
        )
        env = Env(mine, theirs)
        program_id = env.program()

        program = env.service.arrange_program(ArrangeProgramCommand(program_id=program_id))

        assert [item.title for item in program.items] == ["Катюша"]


class TestUndoingARebuild:
    """«Отменить» after a regeneration that was not meant (VT-86).

    Regeneration warns before it replaces, but understanding a warning and meaning to
    press the button are different things. One step back, offered once.
    """

    def test_the_hand_built_order_comes_back(self) -> None:
        env = Env(_candidate("Катюша", 200), _candidate("Калинка", 180))
        program_id = env.program()
        env.service.fill_from_scope(program_id)
        before = env.service.arrange_program(ArrangeProgramCommand(program_id=program_id))
        env.service.add_block(AddBlockCommand(program_id=program_id, kind="BREAK", title="Обед", duration_seconds=900))
        arranged_by_hand = env.service.get_program(program_id)

        env.service.arrange_program(ArrangeProgramCommand(program_id=program_id))
        restored = env.service.undo_arrange(program_id)

        assert [item.id for item in restored.items] == [item.id for item in arranged_by_hand.items]
        assert len(restored.items) == len(before.items) + 1

    def test_the_undo_is_offered_only_between_a_rebuild_and_itself(self) -> None:
        env = Env(_candidate("Катюша", 200))
        program_id = env.program()

        assert not env.service.get_program(program_id).can_undo_arrange

        arranged = env.service.arrange_program(ArrangeProgramCommand(program_id=program_id))
        assert arranged.can_undo_arrange

        assert not env.service.undo_arrange(program_id).can_undo_arrange

    def test_undoing_twice_is_refused_rather_than_silently_doing_nothing(self) -> None:
        env = Env(_candidate("Катюша", 200))
        program_id = env.program()
        env.service.arrange_program(ArrangeProgramCommand(program_id=program_id))
        env.service.undo_arrange(program_id)

        with pytest.raises(NoRestorePointError):
            env.service.undo_arrange(program_id)

    def test_a_programme_that_was_never_rebuilt_has_nothing_to_undo(self) -> None:
        env = Env(_candidate("Катюша", 200))
        program_id = env.program()
        env.service.fill_from_scope(program_id)

        with pytest.raises(NoRestorePointError):
            env.service.undo_arrange(program_id)

    def test_undoing_an_empty_programmes_first_build_empties_it_again(self) -> None:
        """«Собрать программу» on a blank programme is as undoable as any other rebuild."""
        env = Env(_candidate("Катюша", 200))
        program_id = env.program()
        env.service.arrange_program(ArrangeProgramCommand(program_id=program_id))

        restored = env.service.undo_arrange(program_id)

        assert restored.items == ()
