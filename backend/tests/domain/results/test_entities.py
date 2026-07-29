"""Domain tests for the ``Protocol`` aggregate (no Django, no database).

Two behaviours carry most of the weight here and get most of the tests:

* **an award is always editable** - set, changed, cleared, before and after publication.
  It is the rule the jury tab is built on, and the one a status machine would quietly
  break;
* **publication is repeatable and keeps its link** - a corrected protocol is the same
  document at a higher revision, never a second URL.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

import pytest

from apps.results.domain.entities import Protocol
from apps.results.domain.exceptions import (
    AwardsIncompleteError,
    InvalidProtocolDataError,
    PerformanceAlreadyInProtocolError,
    ProtocolRowNotFoundError,
    ReorderMismatchError,
)
from apps.results.domain.value_objects import (
    DEFAULT_PUBLIC_COLUMNS,
    AwardKind,
    ProtocolColumn,
    ProtocolName,
    ProtocolStatus,
    PublicSlug,
    PublishedSnapshot,
    parse_award,
    parse_columns,
)

COMPETITION_ID = uuid.uuid4()
NOMINATION_ID = uuid.uuid4()
NOW = datetime(2026, 8, 1, 18, 0, tzinfo=UTC)
LATER = NOW + timedelta(hours=2)
SLUG = PublicSlug("Vokas2345")


def _protocol(*, rows: int = 0) -> Protocol:
    protocol = Protocol.create(
        protocol_id=uuid.uuid4(),
        competition_id=COMPETITION_ID,
        nomination_id=NOMINATION_ID,
        name=ProtocolName("Вокал"),
        now=NOW,
    )
    for index in range(rows):
        protocol.add_row(row_id=uuid.uuid4(), submission_id=uuid.uuid4(), now=NOW, number=index + 1)
    return protocol


class TestCreation:
    def test_create_starts_as_an_empty_draft(self) -> None:
        protocol = _protocol()
        assert protocol.status is ProtocolStatus.DRAFT
        assert protocol.rows == ()
        assert protocol.revision == 0
        assert protocol.slug is None
        assert protocol.published_at is None

    def test_direct_construction_is_refused(self) -> None:
        with pytest.raises(InvalidProtocolDataError):
            Protocol(
                _token=object(),
                _id=uuid.uuid4(),
                _competition_id=COMPETITION_ID,
                _nomination_id=NOMINATION_ID,
                _name=ProtocolName("Вокал"),
                _created_at=NOW,
                _updated_at=NOW,
            )

    def test_columns_fall_back_to_the_narrow_default(self) -> None:
        # "Nothing chosen" must never mean "show everything": the public page would then
        # widen by accident to a child's school and teacher.
        assert _protocol().public_columns == DEFAULT_PUBLIC_COLUMNS


class TestRows:
    def test_numbers_are_taken_from_the_seed_and_kept(self) -> None:
        protocol = _protocol()
        first = protocol.add_row(row_id=uuid.uuid4(), submission_id=uuid.uuid4(), now=NOW, number=7)
        assert first.number == 7

    def test_a_row_without_a_number_takes_the_next_free_one(self) -> None:
        protocol = _protocol()
        protocol.add_row(row_id=uuid.uuid4(), submission_id=uuid.uuid4(), now=NOW, number=4)
        second = protocol.add_row(row_id=uuid.uuid4(), submission_id=uuid.uuid4(), now=NOW)
        assert second.number == 5

    def test_one_act_cannot_have_two_rows(self) -> None:
        protocol = _protocol()
        submission_id = uuid.uuid4()
        protocol.add_row(row_id=uuid.uuid4(), submission_id=submission_id, now=NOW)
        with pytest.raises(PerformanceAlreadyInProtocolError):
            protocol.add_row(row_id=uuid.uuid4(), submission_id=submission_id, now=NOW)

    def test_a_row_can_be_inserted_where_the_act_actually_performed(self) -> None:
        protocol = _protocol(rows=3)
        inserted = protocol.add_row(row_id=uuid.uuid4(), submission_id=uuid.uuid4(), now=NOW, position=2)
        assert protocol.rows[1] is inserted

    def test_reorder_moves_rows_and_leaves_numbers_with_them(self) -> None:
        protocol = _protocol(rows=3)
        first, second, third = protocol.rows
        protocol.reorder([first.id, third.id, second.id], now=LATER)
        # 1, 3, 2 - which is what happened, and номер 2 is still that participant's.
        assert [row.number for row in protocol.rows] == [1, 3, 2]

    def test_reorder_must_be_a_permutation(self) -> None:
        protocol = _protocol(rows=3)
        with pytest.raises(ReorderMismatchError):
            protocol.reorder([protocol.rows[0].id], now=LATER)

    def test_a_removed_number_is_not_handed_to_anybody_else(self) -> None:
        protocol = _protocol(rows=3)
        protocol.remove_row(protocol.rows[1].id, now=LATER)
        added = protocol.add_row(row_id=uuid.uuid4(), submission_id=uuid.uuid4(), now=LATER)
        assert added.number == 4
        assert [row.number for row in protocol.rows] == [1, 3, 4]

    def test_renumbering_is_explicit(self) -> None:
        protocol = _protocol(rows=3)
        first, second, third = protocol.rows
        protocol.reorder([third.id, first.id, second.id], now=LATER)
        protocol.renumber_sequentially(now=LATER)
        assert [row.number for row in protocol.rows] == [1, 2, 3]

    def test_an_unknown_row_is_refused(self) -> None:
        with pytest.raises(ProtocolRowNotFoundError):
            _protocol(rows=1).row(uuid.uuid4())


class TestAwards:
    def test_a_result_can_be_set_changed_and_cleared(self) -> None:
        protocol = _protocol(rows=1)
        row_id = protocol.rows[0].id
        protocol.award_row(row_id, AwardKind.LAUREATE_II, now=NOW)
        assert protocol.row(row_id).award is AwardKind.LAUREATE_II
        protocol.award_row(row_id, AwardKind.LAUREATE_I, now=LATER)
        assert protocol.row(row_id).award is AwardKind.LAUREATE_I
        protocol.award_row(row_id, None, now=LATER)
        assert protocol.row(row_id).award is None
        assert protocol.decided_rows == ()

    def test_a_batch_is_applied_as_a_unit(self) -> None:
        protocol = _protocol(rows=3)
        first, second, _third = protocol.rows
        with pytest.raises(ProtocolRowNotFoundError):
            protocol.award_rows([(first.id, AwardKind.GRAND_PRIX), (uuid.uuid4(), AwardKind.PARTICIPANT)], now=NOW)
        # Nothing was written: half a nomination's results is worse than none.
        assert protocol.decided_rows == ()
        protocol.award_rows([(first.id, AwardKind.GRAND_PRIX), (second.id, AwardKind.PARTICIPANT)], now=NOW)
        assert len(protocol.decided_rows) == 2

    def test_awards_survive_a_reorder(self) -> None:
        protocol = _protocol(rows=2)
        first, second = protocol.rows
        protocol.award_row(first.id, AwardKind.GRAND_PRIX, now=NOW)
        protocol.reorder([second.id, first.id], now=LATER)
        assert protocol.row(first.id).award is AwardKind.GRAND_PRIX

    def test_clearing_every_award_leaves_the_rows(self) -> None:
        protocol = _protocol(rows=2)
        protocol.award_rows([(row.id, AwardKind.PARTICIPANT) for row in protocol.rows], now=NOW)
        protocol.clear_awards(now=LATER)
        assert len(protocol.rows) == 2
        assert protocol.decided_rows == ()


class TestPublication:
    def test_publishing_stamps_a_revision_and_a_slug(self) -> None:
        protocol = _protocol(rows=1)
        protocol.award_row(protocol.rows[0].id, AwardKind.LAUREATE_I, now=NOW)
        protocol.publish(slug=SLUG, now=LATER)
        assert protocol.status is ProtocolStatus.PUBLISHED
        assert protocol.revision == 1
        assert protocol.slug == SLUG
        assert protocol.published_at == LATER
        assert protocol.has_unpublished_changes is False

    def test_a_protocol_with_no_results_at_all_cannot_be_published(self) -> None:
        protocol = _protocol(rows=2)
        with pytest.raises(AwardsIncompleteError):
            protocol.publish(slug=SLUG, now=LATER)

    def test_individual_blanks_are_publishable(self) -> None:
        # An act that did not appear is a blank line, not a reason to hold the results.
        protocol = _protocol(rows=3)
        protocol.award_row(protocol.rows[0].id, AwardKind.LAUREATE_I, now=NOW)
        protocol.publish(slug=SLUG, now=LATER)
        assert protocol.is_published

    def test_editing_after_publication_is_flagged_rather_than_refused(self) -> None:
        protocol = _protocol(rows=2)
        first, second = protocol.rows
        protocol.award_row(first.id, AwardKind.LAUREATE_II, now=NOW)
        protocol.publish(slug=SLUG, now=LATER)
        protocol.award_row(first.id, AwardKind.LAUREATE_I, now=LATER)
        assert protocol.has_unpublished_changes is True
        assert protocol.revision == 1
        protocol.award_row(second.id, AwardKind.PARTICIPANT, now=LATER)
        assert protocol.has_unpublished_changes is True

    def test_a_correction_stays_out_of_the_published_snapshot(self) -> None:
        # The leak this prevents: a jury re-reading its own decision at midnight must not be
        # broadcasting. The live row changes; what is public does not.
        protocol = _protocol(rows=1)
        row_id = protocol.rows[0].id
        protocol.award_row(row_id, AwardKind.LAUREATE_II, now=NOW)
        protocol.publish(slug=SLUG, now=LATER)
        protocol.award_row(row_id, AwardKind.GRAND_PRIX, now=LATER)
        snapshot = protocol.published_snapshot
        assert snapshot is not None
        assert snapshot.results[0].award is AwardKind.LAUREATE_II
        assert protocol.row(row_id).award is AwardKind.GRAND_PRIX

    def test_publishing_again_replaces_the_snapshot(self) -> None:
        protocol = _protocol(rows=1)
        row_id = protocol.rows[0].id
        protocol.award_row(row_id, AwardKind.LAUREATE_II, now=NOW)
        protocol.publish(slug=SLUG, now=NOW)
        protocol.award_row(row_id, AwardKind.GRAND_PRIX, now=LATER)
        protocol.publish(slug=SLUG, now=LATER)
        snapshot = protocol.published_snapshot
        assert snapshot is not None
        assert snapshot.results[0].award is AwardKind.GRAND_PRIX

    def test_the_snapshot_records_the_columns_it_was_cut_to(self) -> None:
        protocol = _protocol(rows=1)
        protocol.award_row(protocol.rows[0].id, AwardKind.LAUREATE_I, now=NOW)
        protocol.show_columns([ProtocolColumn.PARTICIPANT, ProtocolColumn.AWARD], now=NOW)
        protocol.publish(slug=SLUG, now=LATER)
        snapshot = protocol.published_snapshot
        assert snapshot is not None
        assert snapshot.columns == (ProtocolColumn.PARTICIPANT, ProtocolColumn.AWARD)
        # Narrowing further is staged like any other edit: it reaches the page on publish.
        protocol.show_columns([ProtocolColumn.AWARD], now=LATER)
        assert protocol.published_snapshot is not None
        assert protocol.published_snapshot.columns == (ProtocolColumn.PARTICIPANT, ProtocolColumn.AWARD)

    def test_republishing_raises_the_revision_and_keeps_the_link(self) -> None:
        protocol = _protocol(rows=1)
        protocol.award_row(protocol.rows[0].id, AwardKind.LAUREATE_II, now=NOW)
        protocol.publish(slug=SLUG, now=NOW)
        protocol.award_row(protocol.rows[0].id, AwardKind.LAUREATE_I, now=LATER)
        protocol.publish(slug=PublicSlug("Uther2345"), now=LATER)
        assert protocol.revision == 2
        # A link that changed on correction would be a link nobody could keep.
        assert protocol.slug == SLUG
        assert protocol.has_unpublished_changes is False

    def test_unpublishing_keeps_the_slug_and_the_revision_count(self) -> None:
        protocol = _protocol(rows=1)
        protocol.award_row(protocol.rows[0].id, AwardKind.LAUREATE_I, now=NOW)
        protocol.publish(slug=SLUG, now=NOW)
        protocol.unpublish(now=LATER)
        assert protocol.status is ProtocolStatus.DRAFT
        assert protocol.published_at is None
        assert protocol.published_snapshot is None
        assert protocol.slug == SLUG
        assert protocol.revision == 1

    def test_a_draft_never_reports_unpublished_changes(self) -> None:
        protocol = _protocol(rows=1)
        protocol.award_row(protocol.rows[0].id, AwardKind.GRAND_PRIX, now=NOW)
        assert protocol.has_unpublished_changes is False

    def test_column_choice_is_normalized_to_canonical_order(self) -> None:
        protocol = _protocol()
        protocol.show_columns([ProtocolColumn.AWARD, ProtocolColumn.POSITION], now=NOW)
        assert protocol.public_columns == (ProtocolColumn.POSITION, ProtocolColumn.AWARD)


class TestValueObjects:
    def test_award_seniority_follows_declaration_order(self) -> None:
        assert AwardKind.GRAND_PRIX.seniority < AwardKind.LAUREATE_I.seniority
        assert AwardKind.LAUREATE_III.seniority < AwardKind.DIPLOMANT_I.seniority
        assert AwardKind.PARTICIPANT.seniority == len(AwardKind) - 1

    def test_every_award_has_wording(self) -> None:
        assert all(kind.label for kind in AwardKind)
        assert AwardKind.LAUREATE_II.label == "Лауреат II степени"

    @pytest.mark.parametrize("blank", [None, "", "   "])
    def test_a_blank_award_parses_as_undecided(self, blank: object) -> None:
        assert parse_award(blank) is None

    def test_an_unknown_award_is_refused(self) -> None:
        with pytest.raises(InvalidProtocolDataError):
            parse_award("LAUREATE_IV")

    def test_columns_parse_in_canonical_order_without_duplicates(self) -> None:
        assert parse_columns(["AWARD", "position", "AWARD"]) == (ProtocolColumn.POSITION, ProtocolColumn.AWARD)

    def test_a_bare_string_is_not_a_column_list(self) -> None:
        with pytest.raises(InvalidProtocolDataError):
            parse_columns("AWARD")

    def test_a_name_must_not_be_blank(self) -> None:
        with pytest.raises(InvalidProtocolDataError):
            ProtocolName("   ")

    def test_a_generated_slug_is_valid_and_unguessable_enough(self) -> None:
        slug = PublicSlug.generate()
        assert len(slug.value) == 10
        assert PublicSlug(slug.value) == slug

    @pytest.mark.parametrize("bad", ["short", "has space!", "O0Il" * 3])
    def test_a_confusable_or_short_slug_is_refused(self, bad: str) -> None:
        with pytest.raises(InvalidProtocolDataError):
            PublicSlug(bad)


class TestRehydration:
    def test_a_reloaded_published_protocol_is_not_reported_as_stale(self) -> None:
        # The regression this guards: ``published_version`` has to be persisted, or every
        # reload of a published protocol claims to have unpublished changes.
        protocol = _protocol(rows=1)
        protocol.award_row(protocol.rows[0].id, AwardKind.LAUREATE_I, now=NOW)
        protocol.publish(slug=SLUG, now=LATER)
        reloaded = Protocol.rehydrate(
            protocol_id=protocol.id,
            competition_id=protocol.competition_id,
            nomination_id=protocol.nomination_id,
            name=protocol.name,
            created_at=protocol.created_at,
            updated_at=protocol.updated_at,
            status=protocol.status,
            rows=protocol.rows,
            public_columns=protocol.public_columns,
            slug=protocol.slug,
            revision=protocol.revision,
            published_at=protocol.published_at,
            published_version=protocol.published_version,
            published_snapshot=protocol.published_snapshot,
            version=protocol.version,
        )
        assert reloaded.has_unpublished_changes is False
        assert reloaded.initial_version == protocol.version

    def test_a_snapshot_round_trips_through_its_json_shape(self) -> None:
        protocol = _protocol(rows=2)
        first, second = protocol.rows
        protocol.award_row(first.id, AwardKind.GRAND_PRIX, now=NOW)
        protocol.show_columns([ProtocolColumn.PARTICIPANT, ProtocolColumn.AWARD], now=NOW)
        protocol.publish(slug=SLUG, now=LATER)
        original = protocol.published_snapshot
        assert original is not None
        assert PublishedSnapshot.from_dict(original.to_dict()) == original
        # The undecided line survives the round trip as undecided, not as a missing row.
        assert PublishedSnapshot.from_dict(original.to_dict()).results[1].award is None
        assert original.results[1].submission_id == second.submission_id
