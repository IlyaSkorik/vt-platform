"""Re-joins the two branches that each added a column to ``categorymodel``.

`0021_nomination_held_at` gave a nomination the date it is performed;
`0022_editing_lock_per_nomination` gave it the organizer's freeze. They were
written in parallel on two branches and landed as two leaves, which Django
refuses to run. Nothing to do beyond saying they are compatible: the fields are
independent and neither touches the other's table.
"""

from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("competitions", "0021_nomination_held_at"),
        ("competitions", "0022_editing_lock_per_nomination"),
    ]

    operations: list[migrations.operations.base.Operation] = []
