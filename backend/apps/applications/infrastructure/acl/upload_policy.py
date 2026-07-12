"""``DjangoCompetitionUploadPolicy`` - the ACL projecting upload constraints.

Implements the ``CompetitionUploadPolicy`` port. The per-kind limits reuse the
Competition context's own media-policy defaults - for music, the platform's
:class:`MusicRequirements` defaults (allowed audio formats + maximum size in MB) -
rather than inventing numbers at the edge. Non-audio kinds use the platform's
standard limits. When the Competition settings later expose per-format media
requirements through a read API, this adapter is the one place that changes.
"""

from __future__ import annotations

from typing import Final

from apps.applications.application.interfaces import UploadConstraints
from apps.applications.domain.value_objects import AttachmentType, CompetitionId
from apps.competitions.domain.value_objects import MusicRequirements

__all__ = ["DjangoCompetitionUploadPolicy"]

_MB: Final = 1024 * 1024

_DOCUMENT_EXTENSIONS: Final = frozenset({"pdf", "jpg", "jpeg", "png"})
_IMAGE_EXTENSIONS: Final = frozenset({"jpg", "jpeg", "png", "webp"})
_VIDEO_EXTENSIONS: Final = frozenset({"mp4", "mov", "webm", "mkv"})


class DjangoCompetitionUploadPolicy:
    """Competition ACL implementing the ``CompetitionUploadPolicy`` port."""

    def limits_for(self, *, competition_id: CompetitionId, attachment_kind: str) -> UploadConstraints:
        kind = AttachmentType(attachment_kind)
        if kind is AttachmentType.MUSIC:
            music = MusicRequirements.default()
            return UploadConstraints(max_bytes=music.max_upload_size_mb * _MB, allowed_extensions=frozenset(music.allowed_formats))
        if kind is AttachmentType.VIDEO:
            return UploadConstraints(max_bytes=200 * _MB, allowed_extensions=_VIDEO_EXTENSIONS)
        if kind is AttachmentType.IMAGE:
            return UploadConstraints(max_bytes=10 * _MB, allowed_extensions=_IMAGE_EXTENSIONS)
        return UploadConstraints(max_bytes=25 * _MB, allowed_extensions=_DOCUMENT_EXTENSIONS)
