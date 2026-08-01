"""Point every existing competition at the organization that actually runs it.

``organizer_id`` used to be whatever id the browser had cached — the client
invented one when it had none — because there was a single organization and the
column was a label rather than a boundary. Now it is the boundary: the organizer
workspace shows a caller the competitions of *their* organization, and the
platform console reports fees and commission per organization.

So the festivals that pre-date that rule are attached to the platform's own
seeded organization, which is the one that has in fact been running them. A
competition already pointing at a real organization is left alone.
"""

from __future__ import annotations

from django.db import migrations


def attach_to_seeded_organization(apps, schema_editor):
    CompetitionModel = apps.get_model("competitions", "CompetitionModel")
    OrganizationModel = apps.get_model("organization", "OrganizationModel")

    seeded = OrganizationModel.objects.filter(deleted_at__isnull=True).order_by("created_at").first()
    if seeded is None:
        return

    known = set(OrganizationModel.objects.filter(deleted_at__isnull=True).values_list("id", flat=True))
    CompetitionModel.objects.exclude(organizer_id__in=known).update(organizer_id=seeded.id)


def unattach(apps, schema_editor):
    """Irreversible in substance: the ids it replaced were client-invented junk."""


class Migration(migrations.Migration):
    dependencies = [
        ("competitions", "0015_remove_registration_and_archived_statuses"),
        ("organization", "0004_organizationmodel_commission_percent_and_more"),
    ]

    operations = [
        migrations.RunPython(attach_to_seeded_organization, unattach),
    ]
