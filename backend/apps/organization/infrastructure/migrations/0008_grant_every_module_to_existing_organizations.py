"""Grant every module to every organization that already exists.

The entitlement table arrives empty, and an empty table means "holds nothing".
Without this migration the deploy that introduces modules silently closes half of
the panel to every current customer — festivals, applications, diplomas, money —
because nobody had yet ticked a box that did not exist yesterday.

So the rule is: whatever an organization could do the day before this migration,
it can do the day after. New organizations connected from here on are a different
matter and get whichever preset the operator picks in the console.

Forward-only and idempotent: rows already present are left untouched, so re-running
cannot resurrect a module an operator has since withdrawn.
"""

from __future__ import annotations

import os
import time
import uuid

from django.db import migrations
from django.utils import timezone

_UUID_V7_VERSION = 7

#: Every switchable module, mirroring ``OrganizationModule`` at the time of writing.
#:
#: Spelled out here rather than imported: a data migration must keep meaning what it
#: meant when it ran, and a module added next year must not retroactively be granted
#: to organizations this migration already passed over.
_MODULES = (
    "COMPETITIONS",
    "APPLICATIONS",
    "PARTICIPANTS",
    "JURY",
    "PROGRAMS",
    "DIPLOMAS",
    "VOTING",
    "FINANCE",
    "ANALYTICS",
)


def _uuid7() -> uuid.UUID:
    """Generate a UUID v7 (matches the persistence base model's generator)."""
    unix_ms = time.time_ns() // 1_000_000
    rand = int.from_bytes(os.urandom(10), "big")
    rand_a = (rand >> 68) & 0x0FFF
    rand_b = rand & ((1 << 62) - 1)
    value = (unix_ms & ((1 << 48) - 1)) << 80 | _UUID_V7_VERSION << 76 | rand_a << 64 | 0b10 << 62 | rand_b
    return uuid.UUID(int=value)


def grant_every_module(apps, schema_editor):
    """Enable every module for every organization that exists right now."""
    OrganizationModel = apps.get_model("organization", "OrganizationModel")
    OrganizationModuleModel = apps.get_model("organization", "OrganizationModuleModel")

    now = timezone.now()
    organization_ids = list(OrganizationModel.objects.filter(deleted_at__isnull=True).values_list("id", flat=True))
    if not organization_ids:
        return

    already_decided = set(
        OrganizationModuleModel.objects.filter(
            organization_id__in=organization_ids,
            deleted_at__isnull=True,
        ).values_list("organization_id", "module")
    )

    rows = [
        OrganizationModuleModel(
            id=_uuid7(),
            organization_id=organization_id,
            module=module,
            enabled=True,
            enabled_at=now,
            # No operator to credit: this is the platform grandfathering what the
            # organization already had, not a person granting it.
            enabled_by=None,
            created_at=now,
            updated_at=now,
        )
        for organization_id in organization_ids
        for module in _MODULES
        if (organization_id, module) not in already_decided
    ]
    if rows:
        OrganizationModuleModel.objects.bulk_create(rows)


def revoke_every_module(apps, schema_editor):
    """Reverse: drop the grandfathered rows (the table goes back to empty)."""
    OrganizationModuleModel = apps.get_model("organization", "OrganizationModuleModel")
    OrganizationModuleModel.objects.filter(module__in=_MODULES, enabled_by__isnull=True).delete()


class Migration(migrations.Migration):
    dependencies = [
        ("organization", "0007_module_entitlements"),
    ]

    operations = [
        migrations.RunPython(grant_every_module, revoke_every_module),
    ]
