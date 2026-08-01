"""Turn the order's single payment receipt into a list of them.

An order's fee is regularly settled by more than one transfer — a school pays for
part of a group and a parent for the rest, or the sum goes out in instalments — and
each transfer produces its own slip. The old column held one document, so a second
upload silently overwrote the first.

The existing receipt is carried over as the first entry of the new list, keeping
its file reference and upload time; it gains the id the list form needs.
"""

from __future__ import annotations

import os
import time
import uuid

from django.db import migrations, models

_UUID_V7_VERSION = 7


def _uuid7() -> str:
    """A UUID v7 (RFC 9562 §5.7), self-contained so the migration imports no domain code."""
    unix_ms = time.time_ns() // 1_000_000
    rand = int.from_bytes(os.urandom(10), "big")
    rand_a = rand >> 68 & 0x0FFF
    rand_b = rand & ((1 << 62) - 1)
    value = (unix_ms & ((1 << 48) - 1)) << 80 | _UUID_V7_VERSION << 76 | rand_a << 64 | 0b10 << 62 | rand_b
    return str(uuid.UUID(int=value))


def carry_receipts_forward(apps, schema_editor):
    ApplicationModel = apps.get_model("applications", "ApplicationModel")
    for application in ApplicationModel.objects.exclude(payment_receipt=None).iterator():
        receipt = application.payment_receipt or {}
        reference = str(receipt.get("file_reference") or "").strip()
        if not reference:
            continue
        application.payment_receipts = [
            {
                "id": str(receipt.get("id") or "") or _uuid7(),
                "file_reference": reference,
                "uploaded_at": receipt.get("uploaded_at"),
            }
        ]
        application.save(update_fields=["payment_receipts"])


def carry_receipts_back(apps, schema_editor):
    """Reverse: keep the earliest receipt, which is the one the old column could hold."""
    ApplicationModel = apps.get_model("applications", "ApplicationModel")
    for application in ApplicationModel.objects.exclude(payment_receipts=[]).iterator():
        receipts = application.payment_receipts or []
        if not receipts:
            continue
        application.payment_receipt = receipts[0]
        application.save(update_fields=["payment_receipt"])


class Migration(migrations.Migration):
    dependencies = [
        ("applications", "0004_application_submitted_at"),
    ]

    operations = [
        migrations.AddField(
            model_name="applicationmodel",
            name="payment_receipts",
            field=models.JSONField(blank=True, default=list),
        ),
        migrations.RunPython(carry_receipts_forward, carry_receipts_back),
        migrations.RemoveField(
            model_name="applicationmodel",
            name="payment_receipt",
        ),
    ]
