"""``actor_label`` — how the generation archive names the person who ran a batch.

Reads the Identity context by id to render a staff member as the organizer would
recognise them ("Петрова Ольга", falling back to the account's email). Same shape
of cross-context read as :mod:`.snapshot_source`: by id, values only, no aggregate
crossing the boundary.

The result is **snapshotted** by the caller into the archive row, not resolved on
every read — the archive records who generated a package at the time, which stays
true after that person is renamed or their account is erased.
"""

from __future__ import annotations

import uuid

from apps.identity.infrastructure.models import UserModel

__all__ = ["actor_label"]


def actor_label(user_id: uuid.UUID | None) -> str:
    """A display name for the acting user, or ``""`` when unresolvable.

    An empty label is not an error: a run started by a system process or by an
    account that no longer exists simply has nobody to name, and the archive says
    so instead of inventing a placeholder.
    """
    if user_id is None:
        return ""
    row = UserModel.objects.filter(id=user_id, deleted_at__isnull=True).values("first_name", "last_name", "email").first()
    if row is None:
        return ""
    name = " ".join(part for part in (row["last_name"], row["first_name"]) if str(part or "").strip())
    return name or str(row["email"] or "")
