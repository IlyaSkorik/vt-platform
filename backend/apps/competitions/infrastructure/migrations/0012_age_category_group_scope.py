"""Re-scope AgeCategory to a participant group and make ParticipantGroup competition-wide.

Age bands now belong to a participant group (solo/duet/…) instead of a nomination,
and participant groups are shared across the whole competition rather than defined
per nomination. This is a schema reshape; existing taxonomy data is not preserved
(there is none in any live environment yet).
"""

import uuid

from django.db import migrations, models

_ZERO_UUID = uuid.UUID("00000000-0000-0000-0000-000000000000")


class Migration(migrations.Migration):

    dependencies = [
        ("competitions", "0011_landing_config"),
    ]

    operations = [
        # --- AgeCategory: category_id -> participant_group_id ---
        migrations.RemoveConstraint(
            model_name="agecategorymodel",
            name="competitions_unique_age_category_name",
        ),
        migrations.RemoveIndex(
            model_name="agecategorymodel",
            name="competition_categor_d3298d_idx",
        ),
        migrations.RemoveField(
            model_name="agecategorymodel",
            name="category_id",
        ),
        migrations.AddField(
            model_name="agecategorymodel",
            name="participant_group_id",
            field=models.UUIDField(default=_ZERO_UUID),
            preserve_default=False,
        ),
        migrations.AddIndex(
            model_name="agecategorymodel",
            index=models.Index(fields=["participant_group_id"], name="competition_partici_57696e_idx"),
        ),
        migrations.AddConstraint(
            model_name="agecategorymodel",
            constraint=models.UniqueConstraint(
                fields=["competition", "participant_group_id", "name"],
                name="competitions_unique_age_category_name",
            ),
        ),
        # --- ParticipantGroup: drop category_id (competition-wide) ---
        migrations.RemoveConstraint(
            model_name="participantgroupmodel",
            name="competitions_unique_group_name",
        ),
        migrations.RemoveIndex(
            model_name="participantgroupmodel",
            name="competition_categor_6ccfa1_idx",
        ),
        migrations.RemoveField(
            model_name="participantgroupmodel",
            name="category_id",
        ),
        migrations.AddConstraint(
            model_name="participantgroupmodel",
            constraint=models.UniqueConstraint(
                fields=["competition", "name"],
                name="competitions_unique_group_name",
            ),
        ),
    ]
