"""Unit tests for the Applications (Competition Submission) domain value objects."""

from __future__ import annotations

from datetime import UTC, date, datetime
from decimal import Decimal

import pytest

from apps.applications.domain.exceptions import (
    InvalidBirthDateError,
    InvalidDurationError,
    InvalidMoneyError,
    InvalidParticipantCountRangeError,
    InvalidPerformanceCommentError,
    InvalidPerformanceTitleError,
    InvalidPersonNameError,
    InvalidPriceSnapshotError,
    InvalidReviewCommentError,
    InvalidSubmissionIdError,
    InvalidTeacherRoleError,
)
from apps.applications.domain.value_objects import (
    AgeCategoryId,
    AttachmentType,
    BirthDate,
    Currency,
    DisciplineId,
    Duration,
    Gender,
    Money,
    NominationId,
    ParticipantCountRange,
    ParticipantGroupId,
    ParticipationFormatId,
    Performance,
    PerformanceTitle,
    PersonName,
    PriceSnapshot,
    ReviewComment,
    SubmissionId,
    SubmissionParticipationPolicy,
    SubmissionStatus,
    TeacherRole,
    UserId,
)

NOW = datetime(2026, 7, 10, tzinfo=UTC)


class TestIdentifiers:
    def test_generate_is_uuid_v7(self) -> None:
        assert SubmissionId.generate().value.version == 7

    def test_round_trip_string(self) -> None:
        sid = SubmissionId.generate()
        assert SubmissionId.from_string(sid.json()) == sid

    def test_rejects_non_uuid(self) -> None:
        with pytest.raises(InvalidSubmissionIdError):
            SubmissionId.from_string("not-a-uuid")

    def test_distinct_reference_type(self) -> None:
        # Foreign references are distinct types even though both wrap a UUID v7.
        raw = SubmissionId.generate().value
        assert UserId.from_uuid(raw).value == raw


class TestPerformanceTitle:
    def test_trims(self) -> None:
        assert PerformanceTitle("  Swan Lake  ").value == "Swan Lake"

    def test_empty_rejected(self) -> None:
        with pytest.raises(InvalidPerformanceTitleError):
            PerformanceTitle("   ")


_REFERENCES = {
    "nomination_id": NominationId.from_uuid(SubmissionId.generate().value),
    "discipline_id": DisciplineId.from_uuid(SubmissionId.generate().value),
    "age_category_id": AgeCategoryId.from_uuid(SubmissionId.generate().value),
    "participant_group_id": ParticipantGroupId.from_uuid(SubmissionId.generate().value),
    "participation_format_id": ParticipationFormatId.from_uuid(SubmissionId.generate().value),
}


def _performance(comment: str | None = None) -> Performance:
    """A valid performance; ``comment`` omitted means "the applicant added no note"."""
    return Performance(
        title=PerformanceTitle("Swan Lake"),
        duration=Duration.of(minutes=3, seconds=30),
        **_REFERENCES,
        **({} if comment is None else {"comment": comment}),
    )


class TestPerformanceComment:
    """The applicant's optional note to the organizers about this act."""

    def test_defaults_to_blank(self) -> None:
        assert _performance().comment == ""

    def test_trims(self) -> None:
        assert _performance("  выход с точки 3  ").comment == "выход с точки 3"

    def test_blank_stays_blank(self) -> None:
        assert _performance("   ").comment == ""

    def test_at_the_limit_accepted(self) -> None:
        assert len(_performance("я" * 1_000).comment) == 1_000

    def test_over_the_limit_rejected(self) -> None:
        with pytest.raises(InvalidPerformanceCommentError):
            _performance("я" * 1_001)

    def test_is_part_of_value_equality(self) -> None:
        # Editing only the note still replaces the whole value object.
        assert _performance("нужен микрофон") != _performance()
        assert _performance("нужен микрофон") == _performance("нужен микрофон")


class TestDuration:
    def test_seconds_and_timedelta(self) -> None:
        d = Duration.of(minutes=3, seconds=30)
        assert d.seconds == 210
        assert d.as_timedelta.total_seconds() == 210

    def test_str_is_mm_ss(self) -> None:
        assert str(Duration.of_seconds(65)) == "1:05"

    def test_non_positive_rejected(self) -> None:
        with pytest.raises(InvalidDurationError):
            Duration.of_seconds(0)

    def test_too_long_rejected(self) -> None:
        with pytest.raises(InvalidDurationError):
            Duration.of_seconds(24 * 60 * 60 + 1)

    def test_bool_rejected(self) -> None:
        with pytest.raises(InvalidDurationError):
            Duration(seconds=True)


class TestPersonName:
    def test_full_name_with_middle(self) -> None:
        name = PersonName(first_name="Anna", last_name="Ivanova", middle_name="Petrovna")
        assert name.full_name == "Ivanova Anna Petrovna"

    def test_full_name_without_middle(self) -> None:
        assert PersonName(first_name="Anna", last_name="Ivanova").full_name == "Ivanova Anna"

    def test_blank_middle_becomes_none(self) -> None:
        assert PersonName(first_name="A", last_name="B", middle_name="   ").middle_name is None

    def test_empty_first_rejected(self) -> None:
        with pytest.raises(InvalidPersonNameError):
            PersonName(first_name="  ", last_name="Ivanova")

    def test_value_equality(self) -> None:
        assert PersonName(first_name="A", last_name="B") == PersonName(first_name="A", last_name="B")


class TestBirthDate:
    def test_age_at_before_birthday(self) -> None:
        bd = BirthDate(date(2010, 12, 31))
        assert bd.age_at(date(2026, 7, 10)) == 15

    def test_age_at_after_birthday(self) -> None:
        bd = BirthDate(date(2010, 1, 1))
        assert bd.age_at(date(2026, 7, 10)) == 16

    def test_datetime_rejected(self) -> None:
        with pytest.raises(InvalidBirthDateError):
            BirthDate(datetime(2010, 1, 1, tzinfo=UTC))

    def test_ancient_year_rejected(self) -> None:
        with pytest.raises(InvalidBirthDateError):
            BirthDate(date(1899, 1, 1))


class TestTeacherRole:
    def test_configurable_label(self) -> None:
        assert TeacherRole("  Concertmaster  ").value == "Concertmaster"

    def test_empty_rejected(self) -> None:
        with pytest.raises(InvalidTeacherRoleError):
            TeacherRole("")


class TestReviewComment:
    def test_trims(self) -> None:
        assert ReviewComment("  fix the music  ").value == "fix the music"

    def test_empty_rejected(self) -> None:
        with pytest.raises(InvalidReviewCommentError):
            ReviewComment("   ")


class TestMoney:
    def test_quantized(self) -> None:
        assert Money.of("1500").amount == Decimal("1500.00")

    def test_default_currency_is_rub(self) -> None:
        assert Money.of("10").currency is Currency.BYN

    def test_negative_rejected(self) -> None:
        with pytest.raises(InvalidMoneyError):
            Money.of("-1")

    def test_float_rejected(self) -> None:
        with pytest.raises(InvalidMoneyError):
            Money.of(1500.0)  # type: ignore[arg-type]


class TestPriceSnapshot:
    def test_exposes_amount_and_currency(self) -> None:
        snap = PriceSnapshot(price=Money.of("1500"), calculated_at=NOW)
        assert snap.amount == Decimal("1500.00")
        assert snap.currency is Currency.BYN
        assert snap.calculated_at == NOW

    def test_requires_money(self) -> None:
        with pytest.raises(InvalidPriceSnapshotError):
            PriceSnapshot(price="1500", calculated_at=NOW)  # type: ignore[arg-type]

    def test_requires_datetime(self) -> None:
        with pytest.raises(InvalidPriceSnapshotError):
            PriceSnapshot(price=Money.of("1500"), calculated_at="soon")  # type: ignore[arg-type]

    def test_is_immutable(self) -> None:
        snap = PriceSnapshot(price=Money.of("1500"), calculated_at=NOW)
        with pytest.raises(AttributeError):
            snap.price = Money.of("1")  # type: ignore[misc]


class TestParticipantCountRange:
    def test_fixed_size(self) -> None:
        solo = ParticipantCountRange(1, 1)
        assert solo.contains(1)
        assert not solo.contains(2)

    def test_open_ended(self) -> None:
        choir = ParticipantCountRange(6, None)
        assert choir.is_open_ended
        assert choir.contains(100)
        assert not choir.contains(5)

    def test_min_below_one_rejected(self) -> None:
        with pytest.raises(InvalidParticipantCountRangeError):
            ParticipantCountRange(0, 3)

    def test_inverted_rejected(self) -> None:
        with pytest.raises(InvalidParticipantCountRangeError):
            ParticipantCountRange(5, 3)


class TestSubmissionParticipationPolicy:
    def test_allows_matching_count(self) -> None:
        policy = SubmissionParticipationPolicy(participant_count_range=ParticipantCountRange(2, 2))
        assert policy.allows_participant_count(2)
        assert not policy.allows_participant_count(1)

    def test_admissible_by_default(self) -> None:
        assert SubmissionParticipationPolicy(participant_count_range=ParticipantCountRange(1, 1)).is_admissible


class TestEnums:
    def test_status_members(self) -> None:
        assert {s.value for s in SubmissionStatus} == {
            "DRAFT",
            "SUBMITTED",
            "UNDER_REVIEW",
            "REQUIRES_CORRECTION",
            "APPROVED",
            "WAITING_PAYMENT",
            "PAID",
            "ACCEPTED",
            "SCHEDULED",
            "COMPLETED",
            "CANCELLED",
        }

    def test_attachment_type_members(self) -> None:
        assert {a.value for a in AttachmentType} == {"MUSIC", "VIDEO", "IMAGE", "DOCUMENT"}

    def test_gender_members(self) -> None:
        assert {g.value for g in Gender} == {"MALE", "FEMALE", "OTHER"}
