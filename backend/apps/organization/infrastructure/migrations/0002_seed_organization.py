"""Seed the singleton organization ("Взлёт талантов").

The platform runs exactly one organization; there is no public way to create one.
This forward-only, idempotent data migration inserts it if absent (guarded by an
existence check so re-running is safe). The row is written with a fresh UUID v7
primary key and the fixed slug ``vzlyot-talantov``.

The insert goes through the ORM model directly (not the domain aggregate): a data
migration must use the historical model Django hands it, and this is pure
persistence seeding — no invariant is at stake beyond the columns written here.
"""

from __future__ import annotations

import os
import time
import uuid

from django.db import migrations

_ORGANIZATION_NAME = "Взлёт талантов"
_ORGANIZATION_SLUG = "vzlyot-talantov"
_UUID_V7_VERSION = 7


def _uuid7() -> uuid.UUID:
    """Generate a UUID v7 (matches the persistence base model's generator)."""
    unix_ms = time.time_ns() // 1_000_000
    rand = int.from_bytes(os.urandom(10), "big")
    rand_a = (rand >> 68) & 0x0FFF
    rand_b = rand & ((1 << 62) - 1)
    value = (
        (unix_ms & ((1 << 48) - 1)) << 80
        | _UUID_V7_VERSION << 76
        | rand_a << 64
        | 0b10 << 62
        | rand_b
    )
    return uuid.UUID(int=value)


def seed_organization(apps, schema_editor):
    """Insert the singleton organization if it does not already exist."""
    OrganizationModel = apps.get_model("organization", "OrganizationModel")
    if OrganizationModel.objects.filter(deleted_at__isnull=True).exists():
        return
    OrganizationModel.objects.create(
        id=_uuid7(),
        name=_ORGANIZATION_NAME,
        slug=_ORGANIZATION_SLUG,
        status="ACTIVE",
    )


def unseed_organization(apps, schema_editor):
    """Remove the seeded organization (reverse), matched by its fixed slug."""
    OrganizationModel = apps.get_model("organization", "OrganizationModel")
    OrganizationModel.objects.filter(slug=_ORGANIZATION_SLUG).delete()


class Migration(migrations.Migration):
    dependencies = [
        ("organization", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(seed_organization, unseed_organization),
    ]
