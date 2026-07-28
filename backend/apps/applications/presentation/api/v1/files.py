"""Turning a stored attachment key into something a browser can open.

An attachment's ``file_reference`` is an opaque storage key by design - the aggregate is
not supposed to know whether its bytes sit on a disk or in a bucket (see
``infrastructure/storage/django_file_storage.py``). That leaves somebody having to answer
"where do I download this from", and the edge is the right place: it is the only layer
allowed to know about HTTP and about the storage backend at the same time.

Before object storage this worked by accident - the client prefixed ``/media/`` and the
filesystem happened to serve exactly that. Asking the storage instead is what makes a
receipt uploaded today keep opening after the platform moves to a bucket.
"""

from __future__ import annotations

from django.core.files.storage import default_storage

__all__ = ["file_url"]


def file_url(reference: str | None) -> str | None:
    """The URL an attachment is reachable at, or ``None`` when there is no file.

    Idempotent for anything already absolute: references minted before the move, and any
    the storage hands back whole, pass through untouched rather than being nested inside a
    second URL.
    """
    key = (reference or "").strip()
    if not key:
        return None
    if key.startswith(("http://", "https://", "/")):
        return key
    return default_storage.url(key)
