"""Abstract base persistence model for the Organization bounded context.

A **persistence model only** (ARCH-001 §7.2, §14): shared columns, **no business
logic** — no validation, no state transitions, no overridden ``save``/``clean``,
no signals. The domain aggregate is the single source of truth; these models are
a faithful database representation the mapper/repository reads and writes.

Deliberately a **local copy** of the shared column set (UUID v7 keys, soft-delete
+ audit columns, optimistic-concurrency version) rather than importing Identity's
base: the two bounded contexts stay independent, with no import edge between them
(ARCH-001 §14). If a third context needs it, this is the moment to extract a
``shared`` kernel — not before.
"""

from __future__ import annotations

import os
import time
import uuid

from django.db import models
from django.utils import timezone

__all__ = ["BasePersistenceModel", "uuid7"]

_UUID_V7_VERSION = 7


def uuid7() -> uuid.UUID:
    """Generate a time-ordered UUID version 7 (RFC 9562 §5.7) for primary keys.

    Implemented directly (rather than via ``uuid.uuid7``, added only in Python
    3.14) so it works on any supported interpreter. Time-ordered keys stay roughly
    monotonic, avoiding the index fragmentation random UUID v4 keys cause at scale.
    """
    unix_ms = time.time_ns() // 1_000_000
    rand = int.from_bytes(os.urandom(10), "big")  # 80 random bits
    rand_a = (rand >> 68) & 0x0FFF  # 12 bits
    rand_b = rand & ((1 << 62) - 1)  # 62 bits
    value = (
        (unix_ms & ((1 << 48) - 1)) << 80
        | _UUID_V7_VERSION << 76
        | rand_a << 64
        | 0b10 << 62
        | rand_b
    )
    return uuid.UUID(int=value)


class BasePersistenceModel(models.Model):
    """Abstract base carrying the columns every Organization table shares.

    Concrete models subclass this and declare their own ``Meta`` (subclassing
    :class:`BasePersistenceModel.Meta` to inherit the shared indexes and the
    ``version`` check constraint). No behaviour lives here by design.
    """

    id = models.UUIDField(primary_key=True, default=uuid7, editable=False)
    created_at = models.DateTimeField(default=timezone.now, editable=False)
    updated_at = models.DateTimeField(default=timezone.now, editable=False)
    deleted_at = models.DateTimeField(null=True, blank=True, default=None, editable=False)
    version = models.PositiveIntegerField(default=1, editable=False)

    class Meta:
        abstract = True
        indexes = [
            models.Index(fields=["created_at"]),
            models.Index(fields=["updated_at"]),
            models.Index(fields=["deleted_at"]),
        ]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(version__gte=1),
                name="%(app_label)s_%(class)s_version_positive",
            ),
        ]
