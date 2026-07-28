"""Round-trip tests for the Programs persistence adapter (real PostgreSQL).

Build an aggregate through the domain, persist it, reload it, and assert the whole
graph survives - order above all, because the running order *is* the program. Also
covers what soft-deleting a child means for a public link.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

import pytest

from apps.programs.domain.entities import Program
from apps.programs.domain.value_objects import (
    DEFAULT_PUBLIC_COLUMNS,
    ItemDuration,
    ItemTitle,
    ProgramColumn,
    ProgramItemKind,
    ProgramName,
    PublicSlug,
    ShareName,
    TimeBuffer,
)
from apps.programs.infrastructure.models import ProgramItemModel, ProgramShareModel
from apps.programs.infrastructure.repositories import DjangoProgramRepository

pytestmark = pytest.mark.django_db

NOW = datetime(2026, 8, 1, 9, 0, tzinfo=UTC)
TEN_AM = datetime(2026, 8, 1, 10, 0, tzinfo=UTC)
COMPETITION_ID = uuid.uuid4()
NOMINATION_ID = uuid.uuid4()


def _program() -> Program:
    return Program.create(
        program_id=uuid.uuid4(),
        competition_id=COMPETITION_ID,
        name=ProgramName("Вокал, 1 отделение"),
        now=NOW,
        nomination_id=NOMINATION_ID,
        starts_at=TEN_AM,
        buffer=TimeBuffer(seconds=30),
    )


def _act(program: Program, seconds: int = 200) -> uuid.UUID:
    return program.add_performance(
        item_id=uuid.uuid4(),
        submission_id=uuid.uuid4(),
        duration=ItemDuration(seconds),
        now=NOW,
    ).id


def _publish(program: Program, slug: str = "Screen234") -> None:
    """Publish an edition - the act that freezes the numbers."""
    program.add_share(share_id=uuid.uuid4(), name=ShareName("Экран"), slug=PublicSlug(slug), now=NOW)


def _break(program: Program, title: str = "Перерыв", seconds: int = 900) -> uuid.UUID:
    return program.add_block(
        item_id=uuid.uuid4(),
        kind=ProgramItemKind.BREAK,
        title=ItemTitle(title),
        duration=ItemDuration(seconds),
        now=NOW,
    ).id


class TestRoundTrip:
    def test_the_whole_aggregate_survives(self) -> None:
        repository = DjangoProgramRepository()
        program = _program()
        first = _act(program)
        pause = _break(program)
        second = _act(program, 240)
        share = program.add_share(
            share_id=uuid.uuid4(),
            name=ShareName("Программа звукорежиссёра"),
            slug=PublicSlug("Sound2345"),
            now=NOW,
            columns=[ProgramColumn.TIME, ProgramColumn.TITLE, ProgramColumn.COMMENT],
            item_ids=[first, second],
        )
        repository.save(program)

        loaded = repository.get(program.id)
        assert loaded is not None
        assert str(loaded.name) == "Вокал, 1 отделение"
        assert loaded.competition_id == COMPETITION_ID
        assert loaded.nomination_id == NOMINATION_ID
        assert loaded.starts_at == TEN_AM
        assert loaded.buffer.seconds == 30
        assert [item.id for item in loaded.items] == [first, pause, second]
        assert [item.kind for item in loaded.items] == [
            ProgramItemKind.PERFORMANCE,
            ProgramItemKind.BREAK,
            ProgramItemKind.PERFORMANCE,
        ]
        assert str(loaded.item(pause).title) == "Перерыв"
        assert loaded.item(second).duration.seconds == 240
        assert [s.id for s in loaded.shares] == [share.id]
        assert loaded.shares[0].item_ids == (first, second)
        assert [ref.key for ref in loaded.shares[0].columns] == ["TIME", "TITLE", "COMMENT"]

    def test_the_order_is_the_order_that_comes_back(self) -> None:
        repository = DjangoProgramRepository()
        program = _program()
        first, second, third = _act(program), _act(program), _act(program)
        repository.save(program)

        reloaded = repository.get(program.id)
        assert reloaded is not None
        reloaded.reorder([third, first, second], now=NOW)
        repository.save(reloaded)

        assert [item.id for item in repository.get(program.id).items] == [third, first, second]  # type: ignore[union-attr]
        assert list(
            ProgramItemModel.objects.filter(program_id=program.id, deleted_at__isnull=True).order_by("position").values_list("id", flat=True)
        ) == [third, first, second]

    def test_the_frozen_flag_and_the_numbers_survive_a_reorder_across_a_reload(self) -> None:
        repository = DjangoProgramRepository()
        program = _program()
        first, second, third = _act(program), _act(program), _act(program)
        _publish(program)
        repository.save(program)

        reloaded = repository.get(program.id)
        assert reloaded is not None
        assert reloaded.numbers_frozen is True
        assert reloaded.numbers_frozen_at == NOW
        reloaded.reorder([first, third, second], now=NOW)
        repository.save(reloaded)

        again = repository.get(program.id)
        assert again is not None
        assert [item.id for item in again.items] == [first, third, second]
        assert [item.number for item in again.items] == [1, 3, 2]

    def test_an_unpublished_programme_reloads_unfrozen_and_still_renumbers(self) -> None:
        repository = DjangoProgramRepository()
        program = _program()
        first, second = _act(program), _act(program)
        repository.save(program)

        reloaded = repository.get(program.id)
        assert reloaded is not None
        assert reloaded.numbers_frozen is False
        reloaded.reorder([second, first], now=NOW)
        repository.save(reloaded)

        again = repository.get(program.id)
        assert again is not None
        assert [item.id for item in again.items] == [second, first]
        assert [item.number for item in again.items] == [1, 2]

    def test_a_retired_number_is_not_reissued_after_a_reload(self) -> None:
        repository = DjangoProgramRepository()
        program = _program()
        _first, second = _act(program), _act(program)
        _publish(program)
        program.remove_item(second, now=NOW)
        repository.save(program)

        reloaded = repository.get(program.id)
        assert reloaded is not None
        assert (
            reloaded.add_performance(
                item_id=uuid.uuid4(),
                submission_id=uuid.uuid4(),
                duration=ItemDuration(200),
                now=NOW,
            ).number
            == 3
        )

    def test_a_row_written_before_numbers_existed_falls_back_to_its_ordinal(self) -> None:
        repository = DjangoProgramRepository()
        program = _program()
        first, second = _act(program), _act(program)
        repository.save(program)
        ProgramItemModel.objects.filter(program_id=program.id).update(number=0)

        loaded = repository.get(program.id)
        assert loaded is not None
        assert [item.number for item in loaded.items] == [1, 2]
        assert [item.id for item in loaded.items] == [first, second]

    def test_a_performance_slot_stores_no_title(self) -> None:
        repository = DjangoProgramRepository()
        program = _program()
        item_id = _act(program)
        repository.save(program)
        assert ProgramItemModel.objects.get(id=item_id).title == ""

    def test_a_removed_item_is_soft_deleted_not_dropped(self) -> None:
        repository = DjangoProgramRepository()
        program = _program()
        item_id = _break(program)
        repository.save(program)
        program.remove_item(item_id, now=NOW)
        repository.save(program)

        assert repository.get(program.id).items == ()  # type: ignore[union-attr]
        assert ProgramItemModel.objects.get(id=item_id).deleted_at is not None

    def test_an_empty_program_persists(self) -> None:
        repository = DjangoProgramRepository()
        program = _program()
        repository.save(program)
        loaded = repository.get(program.id)
        assert loaded is not None
        assert loaded.items == ()


class TestListing:
    def test_programs_are_listed_per_competition_and_nomination(self) -> None:
        repository = DjangoProgramRepository()
        vocals = _program()
        repository.save(vocals)
        other_nomination = Program.create(
            program_id=uuid.uuid4(),
            competition_id=COMPETITION_ID,
            name=ProgramName("Хореография"),
            now=NOW,
            nomination_id=uuid.uuid4(),
        )
        repository.save(other_nomination)
        elsewhere = Program.create(
            program_id=uuid.uuid4(),
            competition_id=uuid.uuid4(),
            name=ProgramName("Другой фестиваль"),
            now=NOW,
        )
        repository.save(elsewhere)

        assert len(repository.list_for_competition(competition_id=COMPETITION_ID)) == 2
        scoped = repository.list_for_competition(competition_id=COMPETITION_ID, nomination_id=NOMINATION_ID)
        assert [p.id for p in scoped] == [vocals.id]

    def test_a_deleted_program_disappears_from_reads(self) -> None:
        repository = DjangoProgramRepository()
        program = _program()
        repository.save(program)
        program.delete(now=NOW)
        repository.save(program)

        assert repository.get(program.id) is None
        assert repository.list_for_competition(competition_id=COMPETITION_ID) == ()


class TestPublicLinks:
    def test_a_slug_resolves_to_its_program_and_edition(self) -> None:
        repository = DjangoProgramRepository()
        program = _program()
        _act(program)
        share = program.add_share(share_id=uuid.uuid4(), name=ShareName("Экран"), slug=PublicSlug("Screen234"), now=NOW)
        repository.save(program)

        found = repository.get_by_slug("Screen234")
        assert found is not None
        loaded, share_id = found
        assert loaded.id == program.id
        assert share_id == share.id

    def test_an_unknown_slug_resolves_to_nothing(self) -> None:
        assert DjangoProgramRepository().get_by_slug("Nobody234") is None

    def test_a_revoked_edition_stops_resolving_but_keeps_its_slug_claimed(self) -> None:
        # A slug must never be handed out twice, or an old printed link would start
        # pointing at somebody else's programme.
        repository = DjangoProgramRepository()
        program = _program()
        share = program.add_share(share_id=uuid.uuid4(), name=ShareName("Временная"), slug=PublicSlug("Temp23456"), now=NOW)
        repository.save(program)
        program.remove_share(share.id, now=NOW)
        repository.save(program)

        assert repository.get_by_slug("Temp23456") is None
        assert repository.slug_taken("Temp23456") is True
        assert ProgramShareModel.objects.get(id=share.id).deleted_at is not None

    def test_deleting_the_program_takes_its_links_down(self) -> None:
        repository = DjangoProgramRepository()
        program = _program()
        program.add_share(share_id=uuid.uuid4(), name=ShareName("Экран"), slug=PublicSlug("Screen234"), now=NOW)
        repository.save(program)
        program.delete(now=NOW)
        repository.save(program)

        assert repository.get_by_slug("Screen234") is None

    def test_a_free_slug_is_not_reported_as_taken(self) -> None:
        assert DjangoProgramRepository().slug_taken("Nobody234") is False

    def test_a_row_written_before_columns_existed_loads_with_the_defaults(self) -> None:
        """The columns field is JSON, so an older row simply has an empty list."""
        repository = DjangoProgramRepository()
        program = _program()
        share = program.add_share(
            share_id=uuid.uuid4(),
            name=ShareName("Старая ссылка"),
            slug=PublicSlug("Legacy234"),
            now=NOW,
            columns=[ProgramColumn.TIME],
        )
        repository.save(program)
        ProgramShareModel.objects.filter(id=share.id).update(columns=[])

        loaded = repository.get(program.id)
        assert loaded is not None
        assert [ref.key for ref in loaded.shares[0].columns] == [column.value for column in DEFAULT_PUBLIC_COLUMNS]
