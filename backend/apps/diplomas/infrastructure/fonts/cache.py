"""A local copy of an uploaded font file, for a renderer that can only open paths.

reportlab embeds a font by opening a file, so a font living in object storage has to exist on
the local disk before it can be drawn. On a filesystem backend that is already true and this
module is a no-op passthrough; on S3 it is what makes an organizer's uploaded font work at all
instead of being silently skipped in favour of a bundled family.

Three properties matter, and each one is a decision rather than a detail:

* **Cached by row id, not by content or by key.** A row id is minted per upload and its file
  never changes, so ``vtu-<id>.ttf`` is a name that can be trusted forever. The storage *key*
  would not do: it is derived from family and variant, so deleting a face and uploading a
  different file for the same family and variant reuses the key while the bytes change — a
  cache keyed on it would serve the old font indefinitely.
* **Written atomically.** Two Celery workers can render the same nomination at the same moment
  and both miss the cache. Writing to a temporary file and renaming means the loser of that
  race replaces a complete file with a complete file, and no reader ever opens a half-written
  font — which reportlab would reject, failing a render for a reason nobody could reproduce.
* **A miss is not an error.** If storage is unreachable the caller falls back to a bundled
  family: a diploma in the wrong typeface is a bad diploma, and no diploma at all is worse.

Each host caches independently, under a directory that survives a process restart but is not
expected to survive the machine. Losing it costs one download per face.
"""

from __future__ import annotations

import logging
import os
import tempfile
from pathlib import Path

from django.conf import settings
from django.core.files.storage import default_storage

__all__ = ["FontFileCache", "font_cache_dir"]

logger = logging.getLogger(__name__)

_MEDIA_PREFIX = "/media/"
_DEFAULT_DIR_NAME = "vt-diploma-fonts"


def font_cache_dir() -> Path:
    """Where local copies live.

    Configurable because the right answer depends on the deployment: a container wants a
    mounted volume shared by its workers, a single host is happy with the system temp
    directory. The default is deliberately temp rather than ``MEDIA_ROOT`` — on S3 there is no
    local media root to speak of, and a cache in the media tree would look like content.
    """
    configured = getattr(settings, "DIPLOMA_FONT_CACHE_DIR", "")
    return Path(configured) if configured else Path(tempfile.gettempdir()) / _DEFAULT_DIR_NAME


def _storage_key(reference: str) -> str:
    return reference[len(_MEDIA_PREFIX) :] if reference.startswith(_MEDIA_PREFIX) else reference


class FontFileCache:
    """Turns a stored font reference into a path reportlab can open."""

    def __init__(self, *, directory: Path | None = None) -> None:
        self._directory = directory or font_cache_dir()

    def local_path(self, *, reference: str, name: str) -> str | None:
        """A readable local path for ``reference``, or ``None`` if it cannot be produced.

        ``name`` is the cache filename — the face's registered name, which is unique per
        uploaded row. Fetches from storage only on a miss, so a warm host does one ``stat``
        per face and a cold one downloads each face once.
        """
        key = _storage_key(reference)

        # A filesystem backend already has the file where reportlab can reach it; copying it
        # would double every font on disk for no gain.
        try:
            return str(default_storage.path(key))
        except NotImplementedError:
            pass

        target = self._directory / f"{name}.ttf"
        if target.exists() and target.stat().st_size > 0:
            return str(target)

        try:
            self._directory.mkdir(parents=True, exist_ok=True)
            with default_storage.open(key, "rb") as source:
                data = source.read()
        except Exception:
            # Unreachable storage, a deleted object, a permission problem: all the same
            # outcome for the caller, which is to draw with a bundled family instead.
            logger.warning("Could not fetch font %s from storage; falling back.", key, exc_info=True)
            return None

        if not data:
            logger.warning("Font %s is empty in storage; falling back.", key)
            return None

        try:
            # Same directory as the target, so the rename is atomic rather than a cross-device
            # copy that a reader could catch halfway through.
            handle, temporary = tempfile.mkstemp(dir=str(self._directory), suffix=".part")
            try:
                with os.fdopen(handle, "wb") as buffer:
                    buffer.write(data)
                os.replace(temporary, target)
            except BaseException:
                Path(temporary).unlink(missing_ok=True)
                raise
        except Exception:
            logger.warning("Could not cache font %s locally; falling back.", key, exc_info=True)
            return None

        return str(target)
