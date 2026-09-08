"""Unit tests for the Competitions domain value objects."""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

import pytest

from apps.competitions.domain.exceptions import (
    InvalidAgeRangeError,
    InvalidCompetitionSettingsError,
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
    MediaRequirements,
    MediaSubmissionMode,
    Money,
    ParticipantCountRange,
    ParticipationFormatId,
    ParticipationFormatName,
    PaymentTiming,
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
        assert Money.of("10").currency is Currency.BYN

    def test_negative_rejected(self) -> None:
        with pytest.raises(InvalidMoneyError):
            Money.of("-1")

    def test_float_rejected(self) -> None:
        with pytest.raises(InvalidMoneyError):
            Money.of(1500.0)  # type: ignore[arg-type]

    def test_value_equality(self) -> None:
        assert Money.of("900") == Money(amount=Decimal("900.00"), currency=Currency.BYN)


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
            "RUNNING",
            "COMPLETED",
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

    def test_participation_format_id_and_name(self) -> None:
        fmt_id = ParticipationFormatId.generate()
        assert fmt_id.value.version == 7
        assert ParticipationFormatName("Очно").value == "Очно"


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
        assert ContactValue("  +375 29  ").value == "+375 29"


class TestCompetitionSettings:
    def test_defaults(self) -> None:
        s = CompetitionSettings.default()
        assert s.allow_application_editing is True
        assert s.allow_multiple_applications is False
        # On by default: what nearly every festival wants, and what every application
        # entered before the flag existed assumed.
        assert s.allow_multiple_performances is True
        assert s.require_parent_guardian is False
        assert s.payment_timing is PaymentTiming.BEFORE_APPROVAL
        assert s.format_requirements == ()

    def test_with_changes_is_immutable_copy(self) -> None:
        base = CompetitionSettings.default()
        changed = base.with_changes(allow_multiple_applications=True, require_teacher=True)
        assert changed.allow_multiple_applications is True
        assert changed.require_teacher is True
        assert base.allow_multiple_applications is False  # original untouched

    def test_with_changes_rejects_unknown_flag(self) -> None:
        with pytest.raises(TypeError):
            CompetitionSettings.default().with_changes(nonexistent_flag=True)

    def test_payment_required_needs_methods(self) -> None:
        with pytest.raises(InvalidCompetitionSettingsError):
            CompetitionSettings(payment_required=True, payment_methods=())


class TestContactsConfiguration:
    def test_default(self) -> None:
        from apps.competitions.domain.contacts_configuration import ContactsConfiguration
        from apps.competitions.infrastructure.mappers.contacts_config_json import (
            contacts_config_from_json,
            contacts_config_to_json,
        )

        config = ContactsConfiguration.default()
        assert config.use_organization_contacts is True
        assert config.team_contacts == ()
        assert config.override.phone is None
        assert config.emergency.notes is None
        assert config.venue_details.city is None

        roundtrip = contacts_config_from_json(contacts_config_to_json(config))
        assert roundtrip == config

    def test_from_json_empty_uses_defaults(self) -> None:
        from apps.competitions.domain.contacts_configuration import ContactsConfiguration
        from apps.competitions.infrastructure.mappers.contacts_config_json import contacts_config_from_json

        assert contacts_config_from_json(None) == ContactsConfiguration.default()
        assert contacts_config_from_json({}) == ContactsConfiguration.default()

    def test_from_json_parses_team_and_overrides(self) -> None:
        from apps.competitions.infrastructure.mappers.contacts_config_json import contacts_config_from_json

        config = contacts_config_from_json(
            {
                "use_organization_contacts": False,
                "override": {"phone": "+375 29 000-00-00", "email": "org@example.com"},
                "team_contacts": [
                    {
                        "id": "01900000-0000-7000-8000-000000000001",
                        "name": "Anna",
                        "position": "Coordinator",
                        "sort_order": 1,
                    }
                ],
                "emergency": {"phone": "112"},
                "venue_details": {"city": "Minsk", "country": "BY"},
            }
        )
        assert config.use_organization_contacts is False
        assert config.override.phone == "+375 29 000-00-00"
        assert len(config.team_contacts) == 1
        assert config.team_contacts[0].name == "Anna"
        assert config.emergency.phone == "112"
        assert config.venue_details.city == "Minsk"


class TestLandingConfiguration:
    def test_default(self) -> None:
        from apps.competitions.domain.landing_configuration import (
            SYSTEM_BLOCK_HERO_ID,
            LandingBlockType,
            LandingConfiguration,
        )
        from apps.competitions.infrastructure.mappers.landing_config_json import (
            landing_config_from_json,
            landing_config_to_json,
        )

        config = LandingConfiguration.default()
        types = [b.type for b in config.blocks]
        assert types == [
            LandingBlockType.HERO,
            LandingBlockType.REGULATION,
            LandingBlockType.DOCUMENTS,
            LandingBlockType.VENUE,
            LandingBlockType.JURY,
            LandingBlockType.PARTNERS,
            LandingBlockType.GALLERY,
            LandingBlockType.FAQ,
        ]
        assert config.blocks[0].id == SYSTEM_BLOCK_HERO_ID
        # HERO, REGULATION, DOCUMENTS and VENUE ship enabled; the rest start disabled.
        assert [b.enabled for b in config.blocks] == [True] * 4 + [False] * 4
        assert LandingBlockType.CONTENT not in types

        roundtrip = landing_config_from_json(landing_config_to_json(config))
        assert roundtrip == config

    def test_from_json_empty_uses_defaults(self) -> None:
        from apps.competitions.domain.landing_configuration import LandingConfiguration
        from apps.competitions.infrastructure.mappers.landing_config_json import landing_config_from_json

        assert landing_config_from_json(None) == LandingConfiguration.default()
        assert landing_config_from_json({}) == LandingConfiguration.default()

    def test_requires_hero_and_venue(self) -> None:
        from apps.competitions.domain.exceptions import InvalidLandingConfigurationError
        from apps.competitions.domain.landing_configuration import (
            SYSTEM_BLOCK_HERO_ID,
            LandingBlock,
            LandingBlockType,
            LandingConfiguration,
        )

        with pytest.raises(InvalidLandingConfigurationError):
            LandingConfiguration(
                blocks=(
                    LandingBlock(
                        id=SYSTEM_BLOCK_HERO_ID,
                        type=LandingBlockType.HERO,
                        enabled=True,
                        sort_order=0,
                    ),
                )
            )

    def test_content_requires_title(self) -> None:
        from apps.competitions.domain.exceptions import InvalidLandingConfigurationError
        from apps.competitions.domain.landing_configuration import LandingBlock, LandingBlockType

        with pytest.raises(InvalidLandingConfigurationError):
            LandingBlock(
                id="01900000-0000-7000-8000-000000000099",
                type=LandingBlockType.CONTENT,
                enabled=True,
                sort_order=10,
                title="",
                body="",
            )

    def test_duplicate_card_ids_rejected(self) -> None:
        from apps.competitions.domain.exceptions import InvalidLandingConfigurationError
        from apps.competitions.domain.landing_configuration import (
            SYSTEM_BLOCK_JURY_ID,
            JuryCard,
            LandingBlock,
            LandingBlockType,
        )

        with pytest.raises(InvalidLandingConfigurationError):
            LandingBlock(
                id=SYSTEM_BLOCK_JURY_ID,
                type=LandingBlockType.JURY,
                enabled=True,
                sort_order=2,
                cards=(
                    JuryCard(id="01900000-0000-7000-8000-0000000000aa", name="A"),
                    JuryCard(id="01900000-0000-7000-8000-0000000000aa", name="B"),
                ),
            )

    def test_content_defaults_format_and_empty_body(self) -> None:
        from apps.competitions.domain.landing_configuration import LandingBlock, LandingBlockType

        block = LandingBlock(
            id="01900000-0000-7000-8000-000000000099",
            type=LandingBlockType.CONTENT,
            enabled=True,
            sort_order=10,
            title="About",
        )
        assert block.body == ""
        assert block.content_format == "PLAIN"


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


class TestMediaRequirements:
    """Media is uploadable now, on limits the organizer sets.

    Same two controls music has, for the same reason: a phone's three-minute clip weighs
    what it weighs, and only the organizer knows what their storage and their hall's
    screen can take.
    """

    def test_defaults_accept_a_file_of_ordinary_size(self) -> None:
        media = MediaRequirements.default()
        assert media.max_total_size_mb == 200
        assert "mp4" in media.allowed_formats

    def test_extensions_are_normalized_like_music(self) -> None:
        media = MediaRequirements(
            mode=MediaSubmissionMode.FILE_ONLY,
            allowed_formats=(".MP4", " mov ", ""),
        )
        assert media.allowed_formats == ("mp4", "mov")

    def test_a_file_only_format_needs_at_least_one_extension(self) -> None:
        # Otherwise the requirement says "upload a file" and rejects every file there is.
        with pytest.raises(InvalidCompetitionSettingsError):
            MediaRequirements(mode=MediaSubmissionMode.FILE_ONLY, allowed_formats=("",))

    def test_a_url_only_format_may_have_no_extensions(self) -> None:
        # Nothing is uploaded, so the extension list is nobody's business — and the
        # value object hands back the default rather than an empty tuple.
        media = MediaRequirements(mode=MediaSubmissionMode.URL_ONLY, allowed_formats=())
        assert media.allowed_formats

    @pytest.mark.parametrize("size", [0, -1, 513])
    def test_the_size_limit_stays_within_the_platform_ceiling(self, size: int) -> None:
        with pytest.raises(InvalidCompetitionSettingsError):
            MediaRequirements(max_total_size_mb=size)

    def test_the_size_limit_must_be_a_whole_number_of_megabytes(self) -> None:
        with pytest.raises(InvalidCompetitionSettingsError):
            MediaRequirements(max_total_size_mb=True)

    def test_a_video_may_be_collected_without_being_required(self) -> None:
        # The case that did not exist before: an in-person festival wants the file for the
        # hall's screen but will not turn an entry away for its absence.
        media = MediaRequirements(mode=MediaSubmissionMode.FILE_ONLY, require_upload=False)
        assert media.allows_file_upload
        assert not media.require_upload

    def test_requiring_a_video_nobody_collects_is_a_contradiction(self) -> None:
        with pytest.raises(InvalidCompetitionSettingsError):
            MediaRequirements(mode=MediaSubmissionMode.NOT_REQUIRED, require_upload=True)

    @pytest.mark.parametrize(
        ("mode", "expected"),
        [
            (MediaSubmissionMode.NOT_REQUIRED, False),
            (MediaSubmissionMode.URL_ONLY, False),
            (MediaSubmissionMode.FILE_ONLY, True),
            (MediaSubmissionMode.URL_OR_FILE, True),
        ],
    )
    def test_knows_when_a_file_may_be_uploaded(self, mode: MediaSubmissionMode, expected: bool) -> None:
        # What the upload policy branches on: an in-person festival collecting files for
        # the screen sets URL_OR_FILE, and that has to count as file upload.
        assert MediaRequirements(mode=mode).allows_file_upload is expected
