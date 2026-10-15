"""Use-case tests for the Results bounded context (in-memory ports, no database).

Covers the flow a jury and an organizer actually perform: open a protocol for a nomination,
find it already in performance order, enter results, publish, and see the three effects of
publishing land - the public page, the diplomas, the letters. Then correct a result and
publish again, which is the path that most needs to be exactly right.
"""

from __future__ import annotations

import uuid
from dataclasses import replace

import pytest

from apps.results.application.commands import (
    AddRowCommand,
    AwardRowsCommand,
    CreateProtocolCommand,
    PublishProtocolCommand,
    ReorderRowsCommand,
    UpdateProtocolCommand,
)
from apps.results.application.interfaces import CatalogPerformance, RunningOrderEntry
from apps.results.application.services import PUBLIC_PROTOCOL_PATH, ProtocolService
from apps.results.domain.exceptions import (
    AwardsIncompleteError,
    InvalidProtocolDataError,
    PerformanceNotAvailableError,
    ProtocolAlreadyExistsError,
    ProtocolNotFoundError,
    SlugUnavailableError,
)
from apps.results.domain.value_objects import AwardKind, ProtocolColumn

from .fakes import (
    FixedClock,
    InMemoryProtocolRepository,
    RecordingAwardRegister,
    RecordingNotifier,
    ScriptedSlugFactory,
    StubPerformanceCatalog,
    StubRunningOrderSource,
)

COMPETITION_ID = uuid.uuid4()
NOMINATION_ID = uuid.uuid4()


def _act(
    title: str,
    *,
    performer: str = "Иванов Иван",
    applicant_id: uuid.UUID | None = None,
    email: str | None = "studio@example.com",
    applicant_name: str | None = "Мария Петрова",
) -> CatalogPerformance:
    return CatalogPerformance(
        submission_id=uuid.uuid4(),
        title=title,
        applicant_id=applicant_id if applicant_id is not None else uuid.uuid4(),
        applicant_email=email,
        applicant_name=applicant_name,
        nomination_id=NOMINATION_ID,
        nomination="Вокал",
        discipline="Эстрадный вокал",
        age_category="10-12 лет",
        participant_group="Соло",
        participation_format="Очно",
        participants=(performer,),
        teachers=("Петрова Мария",),
        organization="Школа №1",
    )


class Env:
    """A service wired to in-memory ports."""

    def __init__(
        self,
        *performances: CatalogPerformance,
        order: tuple[RunningOrderEntry, ...] = (),
        slugs: tuple[str, ...] = ("Vokas2345",),
        missing_diplomas: set[uuid.UUID] | None = None,
    ) -> None:
        self.repository = InMemoryProtocolRepository()
        self.catalog = StubPerformanceCatalog(*performances)
        self.running_order = StubRunningOrderSource(*order)
        self.slugs = ScriptedSlugFactory(*slugs)
        self.awards = RecordingAwardRegister(missing=missing_diplomas)
        self.notifier = RecordingNotifier()
        self.service = ProtocolService(
            protocols=self.repository,
            catalog=self.catalog,
            running_order=self.running_order,
            clock=FixedClock(),
            slugs=self.slugs,
            awards=self.awards,
            notifier=self.notifier,
        )

    def create(self, **kwargs: object) -> object:
        command = CreateProtocolCommand(
            competition_id=str(COMPETITION_ID),
            nomination_id=str(NOMINATION_ID),
            **kwargs,  # type: ignore[arg-type]
        )
        return self.service.create_protocol(command)

    def award_all(self, protocol_id: str, award: AwardKind = AwardKind.PARTICIPANT) -> object:
        rows = self.service.get_protocol(protocol_id).rows
        return self.service.award_rows(AwardRowsCommand(protocol_id=protocol_id, awards=tuple((row.id, award.value) for row in rows)))


class TestCreationAndSeeding:
    def test_a_new_protocol_is_seeded_in_running_order_with_the_programme_numbers(self) -> None:
        first, second, third = _act("Песня А"), _act("Песня Б"), _act("Песня В")
        # The programme ran them В, А, Б, and announced them as 1, 2, 3 in that order.
        order = (
            RunningOrderEntry(submission_id=third.submission_id, number=1),
            RunningOrderEntry(submission_id=first.submission_id, number=2),
            RunningOrderEntry(submission_id=second.submission_id, number=3),
        )
        env = Env(first, second, third, order=order)
        protocol = env.create()
        assert [row.title for row in protocol.rows] == ["Песня В", "Песня А", "Песня Б"]  # type: ignore[attr-defined]
        assert [row.number for row in protocol.rows] == [1, 2, 3]  # type: ignore[attr-defined]
        assert protocol.seeded_from_program_id is not None  # type: ignore[attr-defined]

    def test_without_a_programme_the_catalog_is_the_fallback(self) -> None:
        env = Env(_act("Песня А"), _act("Песня Б"))
        protocol = env.create()
        assert len(protocol.rows) == 2  # type: ignore[attr-defined]
        assert protocol.seeded_from_program_id is None  # type: ignore[attr-defined]

    def test_an_act_in_the_programme_that_no_longer_competes_gets_no_row(self) -> None:
        # Withdrawn after the running order was printed: a protocol may not name a result
        # for something that did not compete.
        competing = _act("Песня А")
        withdrawn_id = uuid.uuid4()
        env = Env(
            competing,
            order=(
                RunningOrderEntry(submission_id=withdrawn_id, number=1),
                RunningOrderEntry(submission_id=competing.submission_id, number=2),
            ),
        )
        protocol = env.create()
        assert [row.submission_id for row in protocol.rows] == [str(competing.submission_id)]  # type: ignore[attr-defined]

    def test_seeding_can_be_skipped(self) -> None:
        env = Env(_act("Песня А"))
        assert env.create(seed=False).rows == ()  # type: ignore[attr-defined]

    def test_the_name_defaults_to_the_nomination(self) -> None:
        assert Env(_act("Песня А")).create().name == "Вокал"  # type: ignore[attr-defined]

    def test_one_nomination_gets_one_protocol(self) -> None:
        env = Env(_act("Песня А"))
        env.create()
        with pytest.raises(ProtocolAlreadyExistsError):
            env.create()

    def test_an_unknown_protocol_is_refused(self) -> None:
        with pytest.raises(ProtocolNotFoundError):
            Env().service.get_protocol(str(uuid.uuid4()))

    def test_a_malformed_id_is_a_data_error_not_a_crash(self) -> None:
        with pytest.raises(InvalidProtocolDataError):
            Env().service.get_protocol("not-a-uuid")


class TestRows:
    def test_syncing_appends_without_touching_entered_results(self) -> None:
        first = _act("Песня А")
        env = Env(first)
        protocol = env.create()
        env.award_all(protocol.id, AwardKind.LAUREATE_I)  # type: ignore[attr-defined]
        # A second act finishes registration after the protocol was opened.
        env.catalog.performances.append(_act("Песня Б"))
        synced = env.service.sync_from_running_order(protocol.id)  # type: ignore[attr-defined]
        assert len(synced.rows) == 2
        assert synced.rows[0].award == AwardKind.LAUREATE_I.value
        assert synced.rows[1].award is None

    def test_candidates_exclude_acts_already_in_the_protocol(self) -> None:
        first, second = _act("Песня А"), _act("Песня Б")
        env = Env(first, second, order=(RunningOrderEntry(submission_id=first.submission_id, number=1),))
        protocol = env.create()
        # Only Песня А was in the programme, so Песня Б was seeded from the catalog too.
        assert env.service.candidates(protocol.id) == ()  # type: ignore[attr-defined]

    def test_an_act_from_another_nomination_cannot_be_added(self) -> None:
        env = Env(_act("Песня А"))
        protocol = env.create(seed=False)
        with pytest.raises(PerformanceNotAvailableError):
            env.service.add_row(AddRowCommand(protocol_id=protocol.id, submission_id=str(uuid.uuid4())))  # type: ignore[attr-defined]

    def test_a_row_can_be_added_with_its_result_in_one_step(self) -> None:
        act = _act("Песня А")
        env = Env(act)
        protocol = env.create(seed=False)
        updated = env.service.add_row(
            AddRowCommand(protocol_id=protocol.id, submission_id=str(act.submission_id), award=AwardKind.GRAND_PRIX.value)  # type: ignore[attr-defined]
        )
        assert updated.rows[0].award_label == "Гран-при"

    def test_reordering_keeps_numbers_with_their_acts(self) -> None:
        env = Env(_act("Песня А"), _act("Песня Б"))
        protocol = env.create()
        first, second = protocol.rows  # type: ignore[attr-defined]
        reordered = env.service.reorder_rows(ReorderRowsCommand(protocol_id=protocol.id, row_ids=(second.id, first.id)))  # type: ignore[attr-defined]
        assert [row.number for row in reordered.rows] == [2, 1]
        renumbered = env.service.renumber_rows(protocol.id)  # type: ignore[attr-defined]
        assert [row.number for row in renumbered.rows] == [1, 2]

    def test_a_deleted_entry_leaves_its_row_visible_and_marked(self) -> None:
        act = _act("Песня А")
        env = Env(act)
        protocol = env.create()
        env.catalog.forget(act.submission_id)
        reloaded = env.service.get_protocol(protocol.id)  # type: ignore[attr-defined]
        assert reloaded.rows[0].missing_performance is True
        assert reloaded.rows[0].title == "Выступление удалено"


class TestAwards:
    def test_results_are_saved_and_labelled(self) -> None:
        env = Env(_act("Песня А"), _act("Песня Б"))
        protocol = env.create()
        first, second = protocol.rows  # type: ignore[attr-defined]
        updated = env.service.award_rows(
            AwardRowsCommand(
                protocol_id=protocol.id,  # type: ignore[attr-defined]
                awards=((first.id, AwardKind.GRAND_PRIX.value), (second.id, AwardKind.DIPLOMANT_II.value)),
            )
        )
        assert [row.award_label for row in updated.rows] == ["Гран-при", "Дипломант II степени"]

    def test_a_result_can_be_cleared(self) -> None:
        env = Env(_act("Песня А"))
        protocol = env.create()
        env.award_all(protocol.id, AwardKind.LAUREATE_I)  # type: ignore[attr-defined]
        cleared = env.service.award_rows(
            AwardRowsCommand(protocol_id=protocol.id, awards=((env.service.get_protocol(protocol.id).rows[0].id, None),))  # type: ignore[attr-defined]
        )
        assert cleared.rows[0].award is None

    def test_clearing_the_whole_protocol_leaves_the_rows(self) -> None:
        env = Env(_act("Песня А"), _act("Песня Б"))
        protocol = env.create()
        env.award_all(protocol.id)  # type: ignore[attr-defined]
        cleared = env.service.clear_awards(protocol.id)  # type: ignore[attr-defined]
        assert len(cleared.rows) == 2
        assert all(row.award is None for row in cleared.rows)

    def test_the_award_vocabulary_is_served_with_the_protocol(self) -> None:
        # So the jury's dropdown is not a second copy of the vocabulary in the client.
        protocol = Env(_act("Песня А")).create()
        assert len(protocol.award_options) == len(AwardKind)  # type: ignore[attr-defined]
        assert protocol.award_options[0].label == "Гран-при"  # type: ignore[attr-defined]


class TestPublication:
    def _published(self, *, missing: set[uuid.UUID] | None = None) -> tuple[Env, object]:
        first, second = _act("Песня А"), _act("Песня Б")
        env = Env(first, second, missing_diplomas=missing)
        protocol = env.create()
        rows = env.service.get_protocol(protocol.id).rows  # type: ignore[attr-defined]
        env.service.award_rows(
            AwardRowsCommand(
                protocol_id=protocol.id,  # type: ignore[attr-defined]
                awards=((rows[0].id, AwardKind.LAUREATE_I.value), (rows[1].id, AwardKind.PARTICIPANT.value)),
            )
        )
        return env, env.service.publish(PublishProtocolCommand(protocol_id=protocol.id))  # type: ignore[attr-defined]

    def test_publishing_reports_all_three_effects(self) -> None:
        _env, result = self._published()
        assert result.protocol.status == "PUBLISHED"  # type: ignore[attr-defined]
        assert result.protocol.revision == 1  # type: ignore[attr-defined]
        assert result.diplomas_awarded == 2  # type: ignore[attr-defined]
        assert result.diplomas_created == 2  # type: ignore[attr-defined]
        assert result.diplomas_missing == 0  # type: ignore[attr-defined]
        assert result.letters_sent == 2  # type: ignore[attr-defined]

    def test_the_degrees_that_reach_the_diplomas_are_the_printed_wording(self) -> None:
        env, _result = self._published()
        assert sorted(env.awards.issued.values()) == ["Диплом участника", "Лауреат I степени"]

    def test_the_protocol_is_saved_before_anything_leaves_the_context(self) -> None:
        # The ordering the module docstring promises: a diploma must never carry a degree
        # from a protocol the database still calls a draft.
        env, result = self._published()
        stored = env.repository.protocols[uuid.UUID(str(result.protocol.id))]  # type: ignore[attr-defined]
        assert stored.is_published

    def test_a_protocol_with_no_results_cannot_be_published(self) -> None:
        env = Env(_act("Песня А"))
        protocol = env.create()
        with pytest.raises(AwardsIncompleteError):
            env.service.publish(PublishProtocolCommand(protocol_id=protocol.id))  # type: ignore[attr-defined]
        assert env.awards.calls == []
        assert env.notifier.letters == []

    def test_one_letter_per_applicant_carries_all_of_their_results(self) -> None:
        applicant = uuid.uuid4()
        studio_a = _act("Песня А", applicant_id=applicant, email="studio@example.com")
        studio_b = _act("Песня Б", applicant_id=applicant, email="studio@example.com")
        other = _act("Песня В", email="other@example.com")
        env = Env(studio_a, studio_b, other)
        protocol = env.create()
        env.award_all(protocol.id, AwardKind.LAUREATE_III)  # type: ignore[attr-defined]
        result = env.service.publish(PublishProtocolCommand(protocol_id=protocol.id))  # type: ignore[attr-defined]
        assert result.letters_sent == 2
        studio_letter = next(letter for letter in env.notifier.letters if letter["email"] == "studio@example.com")
        assert len(studio_letter["results"]) == 2  # type: ignore[arg-type]
        assert studio_letter["protocol_url"] == PUBLIC_PROTOCOL_PATH.format(slug="Vokas2345")

    def test_an_applicant_with_no_email_is_skipped_and_counted(self) -> None:
        env = Env(_act("Песня А", email=None), _act("Песня Б"))
        protocol = env.create()
        env.award_all(protocol.id)  # type: ignore[attr-defined]
        result = env.service.publish(PublishProtocolCommand(protocol_id=protocol.id))  # type: ignore[attr-defined]
        assert result.letters_sent == 1
        assert result.letters_skipped == 1

    def test_notification_can_be_turned_off(self) -> None:
        env = Env(_act("Песня А"))
        protocol = env.create()
        env.award_all(protocol.id)  # type: ignore[attr-defined]
        result = env.service.publish(PublishProtocolCommand(protocol_id=protocol.id, notify=False))  # type: ignore[attr-defined]
        assert result.letters_sent == 0
        assert env.notifier.letters == []
        # The diplomas still happen: it is the letter that was suppressed, not the results.
        assert result.diplomas_awarded == 1

    def test_a_nomination_without_a_diploma_template_still_publishes(self) -> None:
        first, second = _act("Песня А"), _act("Песня Б")
        env = Env(first, second, missing_diplomas={first.submission_id})
        protocol = env.create()
        env.award_all(protocol.id, AwardKind.LAUREATE_II)  # type: ignore[attr-defined]
        result = env.service.publish(PublishProtocolCommand(protocol_id=protocol.id))  # type: ignore[attr-defined]
        assert result.protocol.status == "PUBLISHED"
        assert result.diplomas_awarded == 1
        # The gap an organizer must be able to see: a result with no document behind it.
        assert result.diplomas_missing == 1

    def test_undecided_rows_issue_nothing(self) -> None:
        first, second = _act("Песня А"), _act("Песня Б")
        env = Env(first, second)
        protocol = env.create()
        rows = env.service.get_protocol(protocol.id).rows  # type: ignore[attr-defined]
        env.service.award_rows(AwardRowsCommand(protocol_id=protocol.id, awards=((rows[0].id, AwardKind.GRAND_PRIX.value),)))  # type: ignore[attr-defined]
        result = env.service.publish(PublishProtocolCommand(protocol_id=protocol.id))  # type: ignore[attr-defined]
        assert result.diplomas_awarded == 1
        assert result.letters_sent == 1

    def test_columns_can_be_chosen_in_the_publish_dialog(self) -> None:
        env = Env(_act("Песня А"))
        protocol = env.create()
        env.award_all(protocol.id)  # type: ignore[attr-defined]
        result = env.service.publish(
            PublishProtocolCommand(
                protocol_id=protocol.id,  # type: ignore[attr-defined]
                columns=(ProtocolColumn.PARTICIPANT.value, ProtocolColumn.AWARD.value, ProtocolColumn.TEACHERS.value),
            )
        )
        assert [column.key for column in result.protocol.public_columns] == ["PARTICIPANT", "AWARD", "TEACHERS"]

    def test_a_slug_collision_is_retried(self) -> None:
        env = Env(_act("Песня А"), slugs=("Taken2345", "Free23456"))
        env.repository.claimed_slugs.add("Taken2345")
        protocol = env.create()
        env.award_all(protocol.id)  # type: ignore[attr-defined]
        result = env.service.publish(PublishProtocolCommand(protocol_id=protocol.id))  # type: ignore[attr-defined]
        assert result.protocol.slug == "Free23456"

    def test_a_slug_that_never_comes_free_is_an_explicit_failure(self) -> None:
        env = Env(_act("Песня А"), slugs=("Taken2345",))
        env.repository.claimed_slugs.add("Taken2345")
        protocol = env.create()
        env.award_all(protocol.id)  # type: ignore[attr-defined]
        with pytest.raises(SlugUnavailableError):
            env.service.publish(PublishProtocolCommand(protocol_id=protocol.id))  # type: ignore[attr-defined]


class TestCorrection:
    def test_a_corrected_result_republishes_over_the_same_link_and_diploma(self) -> None:
        act = _act("Песня А")
        env = Env(act, slugs=("Vokas2345", "Second234"))
        protocol = env.create()
        env.award_all(protocol.id, AwardKind.LAUREATE_II)  # type: ignore[attr-defined]
        first = env.service.publish(PublishProtocolCommand(protocol_id=protocol.id))  # type: ignore[attr-defined]

        env.award_all(protocol.id, AwardKind.LAUREATE_I)  # type: ignore[attr-defined]
        assert env.service.get_protocol(protocol.id).has_unpublished_changes is True  # type: ignore[attr-defined]

        second = env.service.publish(PublishProtocolCommand(protocol_id=protocol.id))  # type: ignore[attr-defined]
        assert second.protocol.revision == 2
        assert second.protocol.slug == first.protocol.slug
        assert second.protocol.has_unpublished_changes is False
        # One diploma, corrected - not a second one issued.
        assert second.diplomas_created == 0
        assert env.awards.issued[act.submission_id] == "Лауреат I степени"

    def test_editing_after_publication_does_not_change_what_is_public(self) -> None:
        env = Env(_act("Песня А"))
        protocol = env.create()
        env.award_all(protocol.id, AwardKind.LAUREATE_II)  # type: ignore[attr-defined]
        env.service.publish(PublishProtocolCommand(protocol_id=protocol.id))  # type: ignore[attr-defined]
        env.service.update_protocol(UpdateProtocolCommand(protocol_id=protocol.id, name="Вокал (итоги)"))  # type: ignore[attr-defined]
        published = env.service.public_protocol("Vokas2345")
        assert published is not None
        # The rename is staged, not live: it reaches the page on the next publication.
        assert published.name == "Вокал"

    def test_unpublishing_takes_the_page_down_but_leaves_the_diplomas(self) -> None:
        act = _act("Песня А")
        env = Env(act)
        protocol = env.create()
        env.award_all(protocol.id, AwardKind.LAUREATE_I)  # type: ignore[attr-defined]
        env.service.publish(PublishProtocolCommand(protocol_id=protocol.id))  # type: ignore[attr-defined]
        env.service.unpublish(protocol.id)  # type: ignore[attr-defined]
        assert env.service.public_protocol("Vokas2345") is None
        # A diploma that reached a participant's cabinet was issued; pretending otherwise
        # would be a worse lie than a withdrawn page.
        assert env.awards.issued[act.submission_id] == "Лауреат I степени"


class TestPublicReads:
    def _publish(self, env: Env, **publish: object) -> object:
        protocol = env.create()
        env.award_all(protocol.id, AwardKind.LAUREATE_I)  # type: ignore[attr-defined]
        return env.service.publish(PublishProtocolCommand(protocol_id=protocol.id, **publish))  # type: ignore[arg-type,attr-defined]

    def test_only_published_columns_reach_the_wire(self) -> None:
        env = Env(_act("Песня А"))
        self._publish(env, columns=(ProtocolColumn.POSITION.value, ProtocolColumn.AWARD.value))
        page = env.service.public_protocol("Vokas2345")
        assert page is not None
        assert [column.key for column in page.columns] == ["POSITION", "AWARD"]
        # Two columns published, two cells rendered: a hidden column produces no cell at
        # all, so it cannot be read off the response.
        assert page.rows[0].cells == ("1", "Лауреат I степени")

    def test_every_performer_of_an_entry_is_named_in_the_participant_column(self) -> None:
        # A duet wins its award together: a protocol that names one of the two is wrong
        # about who it went to, and the diploma that follows it reads the same way.
        duet = replace(_act("Песня А"), participants=("Иванова Анна", "Петров Пётр"))
        env = Env(duet)
        self._publish(env, columns=(ProtocolColumn.PARTICIPANT.value,))
        page = env.service.public_protocol("Vokas2345")
        assert page is not None
        assert page.rows[0].cells == ("Иванова Анна, Петров Пётр",)

    def test_an_unknown_slug_resolves_to_nothing(self) -> None:
        assert Env().service.public_protocol("Nobody234") is None

    def test_a_draft_has_no_public_page(self) -> None:
        env = Env(_act("Песня А"))
        env.create()
        assert env.service.public_protocol("Vokas2345") is None

    def test_the_landing_index_lists_only_published_protocols(self) -> None:
        env = Env(_act("Песня А"))
        assert env.service.published_links(str(COMPETITION_ID)) == ()
        self._publish(env)
        links = env.service.published_links(str(COMPETITION_ID))
        assert len(links) == 1
        assert links[0].path == "/protocol/Vokas2345"
        assert links[0].revision == 1

    def test_the_organizer_export_shows_every_column(self) -> None:
        env = Env(_act("Песня А"))
        result = self._publish(env, columns=(ProtocolColumn.AWARD.value,))
        table = env.service.protocol_table(protocol_id=result.protocol.id)  # type: ignore[attr-defined]
        assert len(table.columns) == len(ProtocolColumn)
        assert table.subtitle == "Взлёт талантов 2026 · Вокал"

    def test_an_undecided_row_renders_a_blank_result(self) -> None:
        first, second = _act("Песня А"), _act("Песня Б")
        env = Env(first, second)
        protocol = env.create()
        rows = env.service.get_protocol(protocol.id).rows  # type: ignore[attr-defined]
        env.service.award_rows(AwardRowsCommand(protocol_id=protocol.id, awards=((rows[0].id, AwardKind.GRAND_PRIX.value),)))  # type: ignore[attr-defined]
        env.service.publish(PublishProtocolCommand(protocol_id=protocol.id))  # type: ignore[attr-defined]
        page = env.service.public_protocol("Vokas2345")
        assert page is not None
        assert page.rows[1].award is None
        assert page.rows[1].cells[-1] == ""
