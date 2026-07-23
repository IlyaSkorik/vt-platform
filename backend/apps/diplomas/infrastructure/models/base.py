"""Abstract base persistence model for the Diplomas bounded context.

A **persistence model only** (ARCH-001 §7.2, §14): it declares the columns every
Diplomas table shares and carries **no business logic**.

Timestamps are plain columns (not ``auto_now``/``auto_now_add``): the domain owns
these instants and the mapper persists them verbatim.
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
    """Generate a time-ordered UUID version 7 (RFC 9562 §5.7) for primary keys."""
    unix_ms = time.time_ns() // 1_000_000
    rand = int.from_bytes(os.urandom(10), "big")
    rand_a = (rand >> 68) & 0x0FFF
    rand_b = rand & ((1 << 62) - 1)
    value = (unix_ms & ((1 << 48) - 1)) << 80 | _UUID_V7_VERSION << 76 | rand_a << 64 | 0b10 << 62 | rand_b
    return uuid.UUID(int=value)


class BasePersistenceModel(models.Model):
    """Abstract base carrying the columns every Diplomas table shares."""

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
