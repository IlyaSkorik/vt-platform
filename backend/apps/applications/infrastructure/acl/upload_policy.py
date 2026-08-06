"""``DjangoCompetitionUploadPolicy`` - the ACL projecting upload constraints.

Implements the ``CompetitionUploadPolicy`` port. Music **and** video project the
competition's configured per-format requirements — the organizer's allowed extensions
and maximum size in MB — when a participation format is known, falling back to the
platform defaults otherwise. Images and documents use fixed platform limits, because
nothing about a festival changes what a scan of a receipt should weigh.

Video is configurable for the same reason music is, and it is not only a remote-entry
concern: an in-person festival wants the file to play on the hall's screen, and how large
that file may be is a decision about the venue's equipment and the organizer's storage,
not something this module can guess.
"""

from __future__ import annotations

from typing import Final

from apps.applications.application.interfaces import UploadConstraints
from apps.applications.domain.value_objects import AttachmentType, CompetitionId
from apps.competitions.domain.value_objects import CompetitionId as CompCompetitionId
from apps.competitions.domain.value_objects import (
    MusicRequirements,
    ParticipationFormatRequirements,
    VideoRequirements,
)
from apps.competitions.domain.value_objects import ParticipationFormatId as CompParticipationFormatId
from apps.competitions.infrastructure.repositories.django_competition_repository import DjangoCompetitionRepository

__all__ = ["DjangoCompetitionUploadPolicy"]

_MB: Final = 1024 * 1024

_DOCUMENT_EXTENSIONS: Final = frozenset({"pdf", "jpg", "jpeg", "png"})
_IMAGE_EXTENSIONS: Final = frozenset({"jpg", "jpeg", "png", "webp"})


class DjangoCompetitionUploadPolicy:
    """Competition ACL implementing the ``CompetitionUploadPolicy`` port."""

    def __init__(self) -> None:
        self._repo = DjangoCompetitionRepository()

    def limits_for(self, *, competition_id: CompetitionId, attachment_kind: str, participation_format_id: str | None = None) -> UploadConstraints:
        kind = AttachmentType(attachment_kind)
        if kind is AttachmentType.MUSIC:
            music = self._music(competition_id, participation_format_id)
            return UploadConstraints(max_bytes=music.max_upload_size_mb * _MB, allowed_extensions=frozenset(music.allowed_formats))
        if kind is AttachmentType.VIDEO:
            video = self._video(competition_id, participation_format_id)
            return UploadConstraints(max_bytes=video.max_upload_size_mb * _MB, allowed_extensions=frozenset(video.allowed_formats))
        if kind is AttachmentType.IMAGE:
            return UploadConstraints(max_bytes=10 * _MB, allowed_extensions=_IMAGE_EXTENSIONS)
        return UploadConstraints(max_bytes=25 * _MB, allowed_extensions=_DOCUMENT_EXTENSIONS)

    def _music(self, competition_id: CompetitionId, participation_format_id: str | None) -> MusicRequirements:
        """The configured music requirements for the format, or the defaults."""
        requirements = self._requirements(competition_id, participation_format_id)
        return MusicRequirements.default() if requirements is None else requirements.music

    def _video(self, competition_id: CompetitionId, participation_format_id: str | None) -> VideoRequirements:
        """The configured video requirements for the format, or the defaults."""
        requirements = self._requirements(competition_id, participation_format_id)
        return VideoRequirements.default() if requirements is None else requirements.video

    def _requirements(self, competition_id: CompetitionId, participation_format_id: str | None) -> ParticipationFormatRequirements | None:
        """The competition's requirements for one format; ``None`` when unresolvable.

        A missing format or a competition that cannot be loaded both mean "no configured
        rule", and the caller answers with the platform default rather than refusing the
        upload: a limit nobody set should not become a limit of zero.
        """
        if participation_format_id is None:
            return None
        competition = self._repo.get(CompCompetitionId.from_uuid(competition_id.value))
        if competition is None:
            return None
        return competition.settings.requirements_for(CompParticipationFormatId.from_string(participation_format_id))
