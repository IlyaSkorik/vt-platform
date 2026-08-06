"""``DjangoCompetitionUploadPolicy`` - the ACL projecting upload constraints.

Implements the ``CompetitionUploadPolicy`` port. Music and media project the
competition's configured per-format requirements — the organizer's allowed extensions and
size ceiling — when a participation format is known, falling back to the platform defaults
otherwise. Documents use a fixed platform limit, because nothing about a festival changes
what a scan of a receipt should weigh.

Media covers video **and** photographs under one ceiling, and that ceiling is on their
total: several photographs and a video are an ordinary submission, so limiting each file
separately would either wave ten of them through or refuse a single legitimate one. What
the organizer has to protect is their storage and the applicant's connection, and both
care about the sum.
"""

from __future__ import annotations

from typing import Final

from apps.applications.application.interfaces import UploadConstraints
from apps.applications.domain.value_objects import AttachmentType, CompetitionId
from apps.competitions.domain.value_objects import CompetitionId as CompCompetitionId
from apps.competitions.domain.value_objects import (
    MediaRequirements,
    MusicRequirements,
    ParticipationFormatRequirements,
)
from apps.competitions.domain.value_objects import ParticipationFormatId as CompParticipationFormatId
from apps.competitions.infrastructure.repositories.django_competition_repository import DjangoCompetitionRepository

__all__ = ["DjangoCompetitionUploadPolicy"]

_MB: Final = 1024 * 1024

_DOCUMENT_EXTENSIONS: Final = frozenset({"pdf", "jpg", "jpeg", "png"})

#: The attachment kinds the media ceiling is shared across.
_MEDIA_KINDS: Final = frozenset({AttachmentType.VIDEO.value, AttachmentType.IMAGE.value})


class DjangoCompetitionUploadPolicy:
    """Competition ACL implementing the ``CompetitionUploadPolicy`` port."""

    def __init__(self) -> None:
        self._repo = DjangoCompetitionRepository()

    def limits_for(self, *, competition_id: CompetitionId, attachment_kind: str, participation_format_id: str | None = None) -> UploadConstraints:
        kind = AttachmentType(attachment_kind)
        if kind is AttachmentType.MUSIC:
            music = self._music(competition_id, participation_format_id)
            return UploadConstraints(max_bytes=music.max_upload_size_mb * _MB, allowed_extensions=frozenset(music.allowed_formats))
        if kind in {AttachmentType.VIDEO, AttachmentType.IMAGE}:
            media = self._media(competition_id, participation_format_id)
            return UploadConstraints(
                max_bytes=media.max_total_size_mb * _MB,
                allowed_extensions=frozenset(media.allowed_formats),
                shared_budget_kinds=_MEDIA_KINDS,
            )
        return UploadConstraints(max_bytes=25 * _MB, allowed_extensions=_DOCUMENT_EXTENSIONS)

    def _music(self, competition_id: CompetitionId, participation_format_id: str | None) -> MusicRequirements:
        """The configured music requirements for the format, or the defaults."""
        requirements = self._requirements(competition_id, participation_format_id)
        return MusicRequirements.default() if requirements is None else requirements.music

    def _media(self, competition_id: CompetitionId, participation_format_id: str | None) -> MediaRequirements:
        """The configured media requirements for the format, or the defaults."""
        requirements = self._requirements(competition_id, participation_format_id)
        return MediaRequirements.default() if requirements is None else requirements.media

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
