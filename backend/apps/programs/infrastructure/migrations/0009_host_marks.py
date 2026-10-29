"""The host's own two columns: who is standing backstage, and what she wrote to herself.

Both default to the empty answer for every row that already exists, which is the
truthful one — nothing had been marked before there was anywhere to mark it.

They sit on the item rather than on the share because they are the host's own, not an
edition's: an organizer who re-cuts her link must not thereby lose her notes. What keeps
them private is the application layer, which renders them into no other edition's
payload at all.
"""

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("programs", "0008_cancelled_act"),
    ]

    operations = [
        migrations.AddField(
            model_name="programitemmodel",
            name="backstage",
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name="programitemmodel",
            name="host_note",
            field=models.CharField(blank=True, default="", max_length=500),
        ),
    ]
