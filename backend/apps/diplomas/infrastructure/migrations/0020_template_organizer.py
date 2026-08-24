"""Give every document template an owning organization.

Templates were global: one library shared by every organization on the platform,
because the column that says whose library it is did not exist. With a second
organization connected that stopped being a modelling detail and became a hole —
an organizer could read, edit and re-upload anyone's diploma design.

The backfill files every existing template under the seeded organization
("Взлёт талантов", slug ``vzlyot-talantov``). That is correct while it is the only
organization that has authored anything, which is the situation this migration is
written for; it is *not* a general answer, so it refuses to guess rather than
scattering rows when the assumption does not hold — see ``_backfill``.

Three operations rather than one, because a NOT NULL column cannot be added to a
table that already has rows: add it nullable, fill it, then tighten it. The tighten
is what makes "a template always has an owner" an invariant the database keeps,
instead of a convention the application remembers.
"""

from __future__ import annotations

from django.db import migrations, models

_SEEDED_ORGANIZATION_SLUG = "vzlyot-talantov"


def _backfill(apps, schema_editor):
    """Assign every ownerless template to the seeded organization."""
    TemplateModel = apps.get_model("diplomas", "TemplateModel")
    OrganizationModel = apps.get_model("organization", "OrganizationModel")

    orphans = TemplateModel.objects.filter(organizer_id__isnull=True)
    if not orphans.exists():
        return

    organization = OrganizationModel.objects.filter(slug=_SEEDED_ORGANIZATION_SLUG, deleted_at__isnull=True).values("id").first()
    if organization is None:
        # Loud rather than lenient. Without the seeded organization there is no
        # defensible owner for these rows, and the alternatives are both worse than
        # stopping: picking some other organization hands one tenant another's
        # designs, and leaving them NULL fails the AlterField below with an
        # integrity error that names a constraint instead of the actual problem.
        raise RuntimeError(
            f"{orphans.count()} template(s) have no organization and the seeded one "
            f"(slug {_SEEDED_ORGANIZATION_SLUG!r}) is absent. Assign them deliberately "
            "before migrating — see apps/diplomas/infrastructure/migrations/0020."
        )

    orphans.update(organizer_id=organization["id"])


def _unbackfill(apps, schema_editor):
    """No-op: the column is dropped on reverse, so there is nothing to unset."""


class Migration(migrations.Migration):
    dependencies = [
        ("diplomas", "0019_individual_diplomas"),
        # The backfill reads the seeded organization, so the row has to exist.
        ("organization", "0002_seed_organization"),
    ]

    operations = [
        migrations.AddField(
            model_name="templatemodel",
            name="organizer_id",
            field=models.UUIDField(null=True),
        ),
        migrations.RunPython(_backfill, _unbackfill),
        migrations.AlterField(
            model_name="templatemodel",
            name="organizer_id",
            field=models.UUIDField(),
        ),
        migrations.AddIndex(
            model_name="templatemodel",
            index=models.Index(fields=["organizer_id"], name="diplomas_te_organiz_7a2051_idx"),
        ),
        migrations.AddIndex(
            model_name="templatemodel",
            index=models.Index(fields=["organizer_id", "type"], name="diplomas_te_organiz_88e998_idx"),
        ),
    ]
