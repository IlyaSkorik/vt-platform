"""``DjangoCompetitionUploadPolicy`` - the ACL projecting upload constraints.

Implements the ``CompetitionUploadPolicy`` port. For music it projects the
competition's **configured** per-format :class:`MusicRequirements` (the organizer's
allowed audio formats + maximum size in MB) when a participation format is known,
falling back to the platform defaults otherwise. Non-audio kinds use the platform's
standard limits.
"""

from __future__ import annotations

from typing import Final

from apps.applications.application.interfaces import UploadConstraints
from apps.applications.domain.value_objects import AttachmentType, CompetitionId
from apps.competitions.domain.value_objects import CompetitionId as CompCompetitionId
from apps.competitions.domain.value_objects import MusicRequirements
from apps.competitions.domain.value_objects import ParticipationFormatId as CompParticipationFormatId
from apps.competitions.infrastructure.repositories.django_competition_repository import DjangoCompetitionRepository

__all__ = ["DjangoCompetitionUploadPolicy"]

_MB: Final = 1024 * 1024

_DOCUMENT_EXTENSIONS: Final = frozenset({"pdf", "jpg", "jpeg", "png"})
_IMAGE_EXTENSIONS: Final = frozenset({"jpg", "jpeg", "png", "webp"})
_VIDEO_EXTENSIONS: Final = frozenset({"mp4", "mov", "webm", "mkv"})


class DjangoCompetitionUploadPolicy:
    """Competition ACL implementing the ``CompetitionUploadPolicy`` port."""

    def __init__(self) -> None:
        self._repo = DjangoCompetitionRepository()

    def limits_for(self, *, competition_id: CompetitionId, attachment_kind: str, participation_format_id: str | None = None) -> UploadConstraints:
        kind = AttachmentType(attachment_kind)
        if kind is AttachmentType.MUSIC:
            music = self._music_requirements(competition_id, participation_format_id)
            return UploadConstraints(max_bytes=music.max_upload_size_mb * _MB, allowed_extensions=frozenset(music.allowed_formats))
        if kind is AttachmentType.VIDEO:
            return UploadConstraints(max_bytes=200 * _MB, allowed_extensions=_VIDEO_EXTENSIONS)
        if kind is AttachmentType.IMAGE:
            return UploadConstraints(max_bytes=10 * _MB, allowed_extensions=_IMAGE_EXTENSIONS)
        return UploadConstraints(max_bytes=25 * _MB, allowed_extensions=_DOCUMENT_EXTENSIONS)

    def _music_requirements(self, competition_id: CompetitionId, participation_format_id: str | None) -> MusicRequirements:
        """The competition's configured music requirements for the format, or defaults."""
        if participation_format_id is None:
            return MusicRequirements.default()
        competition = self._repo.get(CompCompetitionId.from_uuid(competition_id.value))
        if competition is None:
            return MusicRequirements.default()
        return competition.settings.requirements_for(CompParticipationFormatId.from_string(participation_format_id)).music
