"""``DjangoAccountDirectory`` — the address behind the account accepting an invitation.

Reads Identity by id, one value, no aggregate crossing the boundary (ARCH-001 §13.3).

It exists because the access token is stateless: it carries the subject and nothing
else, so the edge cannot tell whether the person clicking an invitation link is the
person it was addressed to. That question has to be answered against the account
record, and this is the narrowest way to ask it.
"""

from __future__ import annotations

import uuid

from apps.identity.infrastructure.models import UserModel

__all__ = ["DjangoAccountDirectory"]


class DjangoAccountDirectory:
    """Concrete :class:`~apps.judging.application.interfaces.AccountDirectory`."""

    def email_for(self, user_id: uuid.UUID) -> str | None:
        """The account's address, or ``None`` when there is no such account."""
        email = UserModel.objects.filter(id=user_id, deleted_at__isnull=True).values_list("email", flat=True).first()
        text = str(email or "").strip().lower()
        return text or None
