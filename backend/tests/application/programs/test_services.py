"""Use-case tests for the Programs bounded context (in-memory ports, no database).

Covers the flows an organizer actually performs: build a program from a nomination,
insert and remove a break, change the buffer, reorder, publish a public edition, and
read one back through its link.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

import pytest

from apps.programs.application.commands import (
    AddBlockCommand,
    AddColumnCommand,
    AddPerformanceCommand,
    CreateProgramCommand,
    CreateShareCommand,
    EditItemCommand,
    FillCellsCommand,
    ReorderItemsCommand,
    UpdateProgramCommand,
    UpdateShareCommand,
)
from apps.programs.application.interfaces import CatalogPerformance
from apps.programs.application.services import ProgramService
from apps.programs.domain.exceptions import (
    ExportUnavailableError,
    InvalidProgramDataError,
    PerformanceAlreadyInProgramError,
    PerformanceNotAvailableError,
    ProgramNotFoundError,
    ReorderMismatchError,
    SlugUnavailableError,
)

from .fakes import FixedClock, InMemoryProgramRepository, ScriptedSlugFactory, StubPerformanceCatalog

COMPETITION_ID = uuid.uuid4()
NOMINATION_ID = uuid.uuid4()
TEN_AM = datetime(2026, 8, 1, 10, 0, tzinfo=UTC)


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
        assert program.items[2].schedule.starts_at == datetime(2026, 8, 1, 10, 18, tzinfo=UTC)

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
            datetime(2026, 8, 1, 10, 0, tzinfo=UTC),
            datetime(2026, 8, 1, 10, 4, tzinfo=UTC),
            datetime(2026, 8, 1, 10, 8, tzinfo=UTC),
        ]

    def test_changing_the_buffer_shifts_the_timetable_but_not_the_acts(self) -> None:
        env = Env(_act("A", 180), _act("B", 180))
        program_id = env.program()
        env.service.fill_from_scope(program_id)
        program = env.service.update_program(UpdateProgramCommand(program_id=program_id, buffer_seconds=60))
        assert program.buffer_seconds == 60
        assert program.items[0].duration_seconds == 180
        assert program.items[0].schedule.slot_seconds == 240
        assert program.items[1].schedule.starts_at == datetime(2026, 8, 1, 10, 4, tzinfo=UTC)

    def test_the_end_of_the_program_is_reported(self) -> None:
        env = Env(_act("A", 600))
        program = env.service.fill_from_scope(env.program(buffer_seconds=60))
        assert program.total_seconds == 660
        assert program.ends_at == datetime(2026, 8, 1, 10, 11, tzinfo=UTC)

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
        assert program.items[0].schedule.starts_at == datetime(2026, 8, 1, 10, 0, tzinfo=UTC)

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
        # A break has no participant, so that cell is blank rather than a placeholder.
        assert public.rows[1].cells == ("2", "10:03", "", "Перерыв")

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

    def test_columns_are_published_in_canonical_order_whatever_order_was_sent(self) -> None:
        env = Env(_act("Катюша", 200))
        program_id = env.program()
        env.service.fill_from_scope(program_id)
        _detail, share = env.service.create_share(CreateShareCommand(program_id=program_id, name="Жюри", columns=("TEACHERS", "TITLE", "TIME")))
        public = env.service.public_program(share.slug)
        assert public is not None
        assert [column.key for column in public.columns] == ["TIME", "TITLE", "TEACHERS"]

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

    def test_a_deleted_program_takes_its_links_down(self) -> None:
        env = Env(_act("A", 200))
        program_id = env.program()
        env.service.fill_from_scope(program_id)
        _detail, share = env.service.create_share(CreateShareCommand(program_id=program_id, name="Экран"))
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
        assert program.items[0].schedule.starts_at == datetime(2026, 8, 1, 10, 0, tzinfo=UTC)


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
