"""Drop the settings keys that never changed how the platform behaved.

An audit of the settings JSON found that most of its switches had no reader
outside the Competition context — the organizer toggled them and nothing
happened. Five were not worth wiring up at all, so they leave rather than stay
as decoration:

* ``allow_copying_previous_applications`` — no copying feature exists anywhere.
* ``email_notifications`` / ``cabinet_notifications`` — the Applications context
  sends e-mail unconditionally through its own gateway; the toggle only ever
  described a capability, never gated one.
* ``sms_notifications`` / ``push_notifications`` — no provider is integrated, and
  the UI already showed them permanently disabled.

Stripping the keys keeps the stored bag honest: what remains in the column is
what the code still reads. The reader tolerates their absence (defaults apply)
and schema 2 rows are read fine either way, so this migration is about not
leaving a decade of dead keys behind for the next person to puzzle over.

Irreversible by design in the data sense — the values carried no meaning, so
there is nothing to restore. Going backwards simply relabels the schema.
"""

from __future__ import annotations

from django.db import migrations

_DROPPED_KEYS = (
    "allow_copying_previous_applications",
    "email_notifications",
    "cabinet_notifications",
    "sms_notifications",
    "push_notifications",
)


def drop_decorative_keys(apps, schema_editor):
    CompetitionModel = apps.get_model("competitions", "CompetitionModel")

    for competition in CompetitionModel.objects.all().iterator():
        settings = competition.settings
        if not isinstance(settings, dict):
            continue
        touched = False
        for key in _DROPPED_KEYS:
            if key in settings:
                del settings[key]
                touched = True
        # Rows written before the settings module was extracted carry the flat
        # legacy bag and no version marker. Leave those to the mapper's legacy
        # path rather than half-promoting them here.
        if settings.get("schema_version") == 2:
            settings["schema_version"] = 3
            touched = True
        if touched:
            competition.settings = settings
            competition.save(update_fields=["settings"])


def restore_schema_marker(apps, schema_editor):
    """Relabel schema 3 back to 2; the dropped values are not recoverable."""
    CompetitionModel = apps.get_model("competitions", "CompetitionModel")

    for competition in CompetitionModel.objects.all().iterator():
        settings = competition.settings
        if isinstance(settings, dict) and settings.get("schema_version") == 3:
            settings["schema_version"] = 2
            competition.settings = settings
            competition.save(update_fields=["settings"])


class Migration(migrations.Migration):
    dependencies = [
        ("competitions", "0018_backfill_competition_slugs"),
    ]

    operations = [
        migrations.RunPython(drop_decorative_keys, restore_schema_marker),
    ]
