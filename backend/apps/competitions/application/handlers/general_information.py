"""Use cases: update general information, branding, settings and deadlines."""

from __future__ import annotations

from datetime import date

from apps.competitions.application.dto.commands import (
    UpdateBrandingCommand,
    UpdateDeadlinesCommand,
    UpdateGeneralInformationCommand,
    UpdateSettingsCommand,
)
from apps.competitions.application.dto.views import CompetitionDetailView
from apps.competitions.domain.value_objects import (
    CompetitionDescription,
    CompetitionSettings,
    CompetitionTitle,
    DateRange,
    FileReference,
    MusicRequirements,
    ParticipationFormatId,
    ParticipationFormatRequirements,
    PaymentMethod,
    PaymentReceiptRequirements,
    PaymentTiming,
    RegistrationDeadlines,
    Season,
    Venue,
    VideoProvider,
    VideoRequirements,
    VideoSubmissionMode,
)
from shared.utils.json_values import as_int

from ._support import CompetitionCommandHandler

__all__ = [
    "UpdateCompetitionBrandingHandler",
    "UpdateCompetitionDeadlinesHandler",
    "UpdateCompetitionGeneralInformationHandler",
    "UpdateCompetitionSettingsHandler",
]


def _date_range(start: date | None, end: date | None) -> DateRange | None:
    if start is None or end is None:
        return None
    return DateRange(start=start, end=end)


def _file(value: str | None) -> FileReference | None:
    return FileReference(value) if value else None


def _format_requirements(raw_items: list[dict[str, object]]) -> tuple[ParticipationFormatRequirements, ...]:
    result: list[ParticipationFormatRequirements] = []
    for raw in raw_items:
        format_id = ParticipationFormatId.from_string(str(raw["participation_format_id"]))
        music_raw = raw.get("music") if isinstance(raw.get("music"), dict) else {}
        video_raw = raw.get("video") if isinstance(raw.get("video"), dict) else {}
        receipt_raw = raw.get("payment_receipt") if isinstance(raw.get("payment_receipt"), dict) else {}
        assert isinstance(music_raw, dict)
        assert isinstance(video_raw, dict)
        assert isinstance(receipt_raw, dict)

        providers_raw = video_raw.get("allowed_providers", [])
        providers = tuple(VideoProvider(str(item)) for item in providers_raw) if isinstance(providers_raw, list) else ()

        result.append(
            ParticipationFormatRequirements(
                participation_format_id=format_id,
                music=MusicRequirements(
                    require_upload=bool(music_raw.get("require_upload", False)),
                    allow_replacement=bool(music_raw.get("allow_replacement", True)),
                    allowed_formats=_extensions(music_raw.get("allowed_formats")),
                    max_upload_size_mb=as_int(music_raw.get("max_upload_size_mb"), default=25),
                ),
                video=VideoRequirements(
                    mode=VideoSubmissionMode(str(video_raw.get("mode", VideoSubmissionMode.NOT_REQUIRED.value))),
                    allowed_providers=providers,
                    allow_replacement=bool(video_raw.get("allow_replacement", True)),
                    require_upload=bool(video_raw.get("require_upload", False)),
                    allowed_formats=_extensions(video_raw.get("allowed_formats")),
                    max_upload_size_mb=as_int(video_raw.get("max_upload_size_mb"), default=200),
                ),
                payment_receipt=PaymentReceiptRequirements(
                    require_receipt=bool(receipt_raw.get("require_receipt", False)),
                    allow_upload_later=bool(receipt_raw.get("allow_upload_later", True)),
                    allow_replacement=bool(receipt_raw.get("allow_replacement", True)),
                ),
            )
        )
    return tuple(result)


def _extensions(raw: object) -> tuple[str, ...]:
    """The submitted extension list, or empty when the client omitted it.

    Empty is deliberate rather than a default: the value object substitutes its own
    default for an empty list, so omitting the field means "leave it as the platform has
    it" instead of silently pinning whatever this layer happens to think it should be.
    """
    return tuple(str(item) for item in raw) if isinstance(raw, list) else ()


def _settings_from_command(command: UpdateSettingsCommand) -> CompetitionSettings:
    return CompetitionSettings(
        allow_multiple_applications=command.allow_multiple_applications,
        allow_application_editing=command.allow_application_editing,
        allow_withdrawing_applications=command.allow_withdrawing_applications,
        require_teacher=command.require_teacher,
        require_parent_guardian=command.require_parent_guardian,
        participant_comment_enabled=command.participant_comment_enabled,
        require_document_upload=command.require_document_upload,
        allow_additional_documents_later=command.allow_additional_documents_later,
        allow_replacing_documents=command.allow_replacing_documents,
        payment_required=command.payment_required,
        payment_timing=PaymentTiming(command.payment_timing),
        payment_methods=tuple(PaymentMethod(item) for item in command.payment_methods),
        additional_performance_discount_percent=int(command.additional_performance_discount_percent),
        require_personal_data_consent=command.require_personal_data_consent,
        require_media_consent=command.require_media_consent,
        require_regulations_acceptance=command.require_regulations_acceptance,
        manual_application_approval=command.manual_application_approval,
        automatic_approval_after_payment=command.automatic_approval_after_payment,
        allow_returning_for_correction=command.allow_returning_for_correction,
        format_requirements=_format_requirements(command.format_requirements),
    )


class UpdateCompetitionGeneralInformationHandler(CompetitionCommandHandler):
    """Update competition title, description, season, venue and periods."""

    def handle(self, command: UpdateGeneralInformationCommand) -> CompetitionDetailView:
        competition = self._require(command.competition_id)

        events = competition.update_general_information(
            now=self._clock.utcnow(),
            title=CompetitionTitle(command.title),
            season=Season(command.season),
            description=CompetitionDescription(command.description) if command.description else None,
            logo=_file(command.logo),
            banner=_file(command.banner),
            venue=(
                Venue(
                    name=command.venue_name,
                    address=command.venue_address,
                )
                if command.venue_name
                else None
            ),
            registration_period=_date_range(
                command.registration_start,
                command.registration_end,
            ),
            competition_period=_date_range(
                command.competition_start,
                command.competition_end,
            ),
        )

        return self._persist(competition, events)


class UpdateCompetitionBrandingHandler(CompetitionCommandHandler):
    """Replace competition branding assets."""

    def handle(self, command: UpdateBrandingCommand) -> CompetitionDetailView:
        competition = self._require(command.competition_id)

        events = competition.update_branding(
            now=self._clock.utcnow(),
            logo=_file(command.logo),
            banner=_file(command.banner),
            poster=_file(command.poster),
        )

        return self._persist(competition, events)


class UpdateCompetitionSettingsHandler(CompetitionCommandHandler):
    """Replace competition behaviour settings."""

    def handle(self, command: UpdateSettingsCommand) -> CompetitionDetailView:
        competition = self._require(command.competition_id)
        events = competition.update_settings(
            settings=_settings_from_command(command),
            now=self._clock.utcnow(),
        )
        return self._persist(competition, events)


class UpdateCompetitionDeadlinesHandler(CompetitionCommandHandler):
    """Replace competition registration deadlines."""

    def handle(self, command: UpdateDeadlinesCommand) -> CompetitionDetailView:
        competition = self._require(command.competition_id)

        deadlines = RegistrationDeadlines(
            application=command.application,
            payment=command.payment,
            music_upload=command.music_upload,
            document_upload=command.document_upload,
            correction=command.correction,
        )

        events = competition.update_deadlines(
            deadlines=deadlines,
            now=self._clock.utcnow(),
        )

        return self._persist(competition, events)
