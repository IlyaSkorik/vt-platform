"""Unit tests for the Competitions domain value objects."""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

import pytest

from apps.competitions.domain.exceptions import (
    InvalidAgeRangeError,
    InvalidContactValueError,
    InvalidMoneyError,
    InvalidParticipantCountRangeError,
    InvalidRegistrationDeadlinesError,
    InvalidRichTextError,
    InvalidServiceNameError,
    InvalidTemplateNameError,
)
from apps.competitions.domain.value_objects import (
    AgeRange,
    CompetitionBranding,
    CompetitionPublicationReport,
    CompetitionSettings,
    CompetitionStatus,
    ContactValue,
    Currency,
    DeadlineKind,
    DocumentCategory,
    DocumentVisibility,
    Money,
    ParticipantCountRange,
    ParticipationFormat,
    PublicationIssue,
    PublicationIssueCode,
    RegistrationDeadlines,
    RichText,
    RichTextFormat,
    ServiceName,
    TemplateName,
)


class TestAgeRange:
    def test_valid_and_membership(self) -> None:
        band = AgeRange(6, 8)
        assert band.contains(7)
        assert not band.contains(9)

    def test_overlaps(self) -> None:
        assert AgeRange(6, 8).overlaps(AgeRange(8, 10))
        assert not AgeRange(6, 8).overlaps(AgeRange(9, 11))

    def test_inverted_rejected(self) -> None:
        with pytest.raises(InvalidAgeRangeError):
            AgeRange(9, 6)

    def test_out_of_bounds_rejected(self) -> None:
        with pytest.raises(InvalidAgeRangeError):
            AgeRange(-1, 5)


class TestParticipantCountRange:
    def test_open_ended(self) -> None:
        choir = ParticipantCountRange(6, None)
        assert choir.is_open_ended
        assert choir.contains(100)
        assert not choir.contains(5)

    def test_overlaps_open_ended(self) -> None:
        assert ParticipantCountRange(6, None).overlaps(ParticipantCountRange(1, 6))
        assert not ParticipantCountRange(6, None).overlaps(ParticipantCountRange(1, 5))

    def test_min_below_one_rejected(self) -> None:
        with pytest.raises(InvalidParticipantCountRangeError):
            ParticipantCountRange(0, 3)

    def test_inverted_rejected(self) -> None:
        with pytest.raises(InvalidParticipantCountRangeError):
            ParticipantCountRange(5, 3)


class TestMoney:
    def test_quantized(self) -> None:
        assert Money.of("1500").amount == Decimal("1500.00")

    def test_default_currency_is_rub(self) -> None:
        assert Money.of("10").currency is Currency.RUB

    def test_negative_rejected(self) -> None:
        with pytest.raises(InvalidMoneyError):
            Money.of("-1")

    def test_float_rejected(self) -> None:
        with pytest.raises(InvalidMoneyError):
            Money.of(1500.0)  # type: ignore[arg-type]

    def test_value_equality(self) -> None:
        assert Money.of("900") == Money(amount=Decimal("900.00"), currency=Currency.RUB)


class TestBoundedNames:
    def test_template_name_empty_rejected(self) -> None:
        with pytest.raises(InvalidTemplateNameError):
            TemplateName("   ")

    def test_service_name_empty_rejected(self) -> None:
        with pytest.raises(InvalidServiceNameError):
            ServiceName("")


class TestEnums:
    def test_status_members(self) -> None:
        assert {s.value for s in CompetitionStatus} == {
            "DRAFT",
            "CONFIGURED",
            "READY",
            "PUBLISHED",
            "REGISTRATION_OPEN",
            "REGISTRATION_CLOSED",
            "RUNNING",
            "COMPLETED",
            "ARCHIVED",
        }

    def test_document_category_members(self) -> None:
        assert {c.value for c in DocumentCategory} == {
            "REGULATION",
            "PROGRAM",
            "SCHEDULE",
            "REQUISITES",
            "MEMO",
            "ACCOMMODATION",
            "OTHER",
        }

    def test_document_visibility_members(self) -> None:
        assert {v.value for v in DocumentVisibility} == {"ALL", "PUBLIC", "PARTICIPANTS", "STAFF"}

    def test_participation_format_members(self) -> None:
        assert {f.value for f in ParticipationFormat} == {"OFFLINE", "ONLINE"}


class TestPublicationReport:
    def test_publishable_when_no_errors(self) -> None:
        report = CompetitionPublicationReport()
        assert report.is_publishable
        assert report.errors == ()

    def test_not_publishable_with_errors_regardless_of_warnings(self) -> None:
        report = CompetitionPublicationReport(
            errors=(PublicationIssue(PublicationIssueCode.NO_CATEGORIES, "x"),),
            warnings=(PublicationIssue(PublicationIssueCode.MISSING_REGULATION, "y"),),
        )
        assert not report.is_publishable
        assert "x" in report.error_summary()

    def test_warnings_do_not_block(self) -> None:
        report = CompetitionPublicationReport(warnings=(PublicationIssue(PublicationIssueCode.UNUSED_PARTICIPATION_FORMAT, "y"),))
        assert report.is_publishable


class TestRichText:
    def test_stores_value_and_format(self) -> None:
        rt = RichText("<p>hi</p>", RichTextFormat.HTML)
        assert str(rt) == "<p>hi</p>"
        assert rt.format is RichTextFormat.HTML

    def test_defaults_to_plain(self) -> None:
        assert RichText("hi").format is RichTextFormat.PLAIN

    def test_empty_detection(self) -> None:
        assert RichText("   ").is_empty
        assert not RichText("x").is_empty

    def test_too_long_rejected(self) -> None:
        with pytest.raises(InvalidRichTextError):
            RichText("x" * 50_001)


class TestContactValue:
    def test_empty_rejected(self) -> None:
        with pytest.raises(InvalidContactValueError):
            ContactValue("  ")

    def test_trimmed(self) -> None:
        assert ContactValue("  +7 900  ").value == "+7 900"


class TestCompetitionSettings:
    def test_defaults(self) -> None:
        s = CompetitionSettings.default()
        assert s.allow_application_editing is True
        assert s.allow_multiple_applications is False
        assert s.require_parent_consent is False

    def test_with_changes_is_immutable_copy(self) -> None:
        base = CompetitionSettings.default()
        changed = base.with_changes(allow_multiple_applications=True, require_teacher=True)
        assert changed.allow_multiple_applications is True
        assert changed.require_teacher is True
        assert base.allow_multiple_applications is False  # original untouched

    def test_with_changes_rejects_unknown_flag(self) -> None:
        with pytest.raises(TypeError):
            CompetitionSettings.default().with_changes(nonexistent_flag=True)


class TestRegistrationDeadlines:
    def test_empty_is_always_open(self) -> None:
        d = RegistrationDeadlines()
        now = datetime(2026, 7, 10, tzinfo=UTC)
        assert d.is_open(DeadlineKind.APPLICATION, now)
        assert d.is_open(DeadlineKind.PAYMENT, now)

    def test_open_before_deadline_closed_after(self) -> None:
        deadline = datetime(2026, 7, 10, tzinfo=UTC)
        d = RegistrationDeadlines(application=deadline)
        assert d.is_open(DeadlineKind.APPLICATION, datetime(2026, 7, 9, tzinfo=UTC))
        assert d.is_open(DeadlineKind.APPLICATION, deadline)
        assert not d.is_open(DeadlineKind.APPLICATION, datetime(2026, 7, 11, tzinfo=UTC))

    def test_correction_before_application_is_contradiction(self) -> None:
        with pytest.raises(InvalidRegistrationDeadlinesError):
            RegistrationDeadlines(
                application=datetime(2026, 7, 10, tzinfo=UTC),
                correction=datetime(2026, 7, 5, tzinfo=UTC),
            )

    def test_correction_after_application_ok(self) -> None:
        RegistrationDeadlines(
            application=datetime(2026, 7, 10, tzinfo=UTC),
            correction=datetime(2026, 7, 20, tzinfo=UTC),
        )


class TestCompetitionBranding:
    def test_empty(self) -> None:
        b = CompetitionBranding.empty()
        assert b.logo is None and b.banner is None and b.poster is None
