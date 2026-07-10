"""Use cases: general information, branding, settings and deadlines."""

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
    RegistrationDeadlines,
    Season,
    Venue,
)

from ._support import CompetitionCommandHandler

__all__ = [
    "UpdateBrandingHandler",
    "UpdateDeadlinesHandler",
    "UpdateGeneralInformationHandler",
    "UpdateSettingsHandler",
]


def _file(value: str | None) -> FileReference | None:
    return FileReference(value) if value else None


def _period(start: date | None, end: date | None) -> DateRange | None:
    if start is None or end is None:
        return None
    return DateRange(start=start, end=end)


class UpdateGeneralInformationHandler(CompetitionCommandHandler):
    """Replace the competition's general information (allowed unless ARCHIVED)."""

    def handle(self, command: UpdateGeneralInformationCommand) -> CompetitionDetailView:
        competition = self._require(command.competition_id)
        venue = Venue(name=command.venue_name, address=command.venue_address) if command.venue_name else None
        events = competition.update_general_information(
            now=self._clock.utcnow(),
            title=CompetitionTitle(command.title),
            season=Season(command.season),
            description=CompetitionDescription(command.description) if command.description else None,
            logo=_file(command.logo),
            banner=_file(command.banner),
            venue=venue,
            registration_period=_period(command.registration_start, command.registration_end),
            competition_period=_period(command.competition_start, command.competition_end),
        )
        return self._persist(competition, events)


class UpdateBrandingHandler(CompetitionCommandHandler):
    """Replace the competition's branding assets (logo, banner, poster)."""

    def handle(self, command: UpdateBrandingCommand) -> CompetitionDetailView:
        competition = self._require(command.competition_id)
        events = competition.update_branding(
            logo=_file(command.logo),
            banner=_file(command.banner),
            poster=_file(command.poster),
            now=self._clock.utcnow(),
        )
        return self._persist(competition, events)


class UpdateSettingsHandler(CompetitionCommandHandler):
    """Replace the competition's behaviour settings wholesale."""

    def handle(self, command: UpdateSettingsCommand) -> CompetitionDetailView:
        competition = self._require(command.competition_id)
        settings = CompetitionSettings(
            allow_multiple_applications=command.allow_multiple_applications,
            allow_application_editing=command.allow_application_editing,
            allow_music_replacement=command.allow_music_replacement,
            allow_video_replacement=command.allow_video_replacement,
            allow_participant_changes=command.allow_participant_changes,
            require_music_upload=command.require_music_upload,
            require_video_upload=command.require_video_upload,
            require_photo_upload=command.require_photo_upload,
            require_identity_document=command.require_identity_document,
            require_parent_consent=command.require_parent_consent,
            require_teacher=command.require_teacher,
            require_comment_for_application=command.require_comment_for_application,
        )
        events = competition.update_settings(settings=settings, now=self._clock.utcnow())
        return self._persist(competition, events)


class UpdateDeadlinesHandler(CompetitionCommandHandler):
    """Replace the competition's registration deadlines wholesale."""

    def handle(self, command: UpdateDeadlinesCommand) -> CompetitionDetailView:
        competition = self._require(command.competition_id)
        deadlines = RegistrationDeadlines(
            application=command.application,
            payment=command.payment,
            music_upload=command.music_upload,
            document_upload=command.document_upload,
            correction=command.correction,
        )
        events = competition.update_deadlines(deadlines=deadlines, now=self._clock.utcnow())
        return self._persist(competition, events)
