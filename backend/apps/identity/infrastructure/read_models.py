"""Concrete read-model adapters for the Identity bounded context.

Read side only (CQRS): query the ``identity_user`` table directly and project
rows into the flat, primitive-only views published by
:mod:`apps.identity.application.read_models`. No aggregate is rehydrated and no
invariant enforced — a projection is a fast, denormalized read path
(ARCH-001 §7.2, §14). Mirrors ``DjangoOrganizationDirectory`` in shape.
"""

from __future__ import annotations

import uuid
from collections.abc import Iterable
from typing import Any

from apps.identity.application.read_models import UserCardView
from apps.identity.infrastructure.models import UserModel

__all__ = ["DjangoUserDirectory"]


class DjangoUserDirectory:
    """Concrete :class:`UserDirectory` over the ``identity_user`` table.

    Structurally satisfies the port (no inheritance — the seam is structural by
    design). One indexed query resolves the whole id set; soft-deleted rows are
    excluded.
    """

    _CARD_COLUMNS = (
        "id",
        "email",
        "first_name",
        "last_name",
        "middle_name",
        "email_verified_at",
    )

    def resolve(self, user_ids: Iterable[uuid.UUID]) -> dict[uuid.UUID, UserCardView]:
        ids = {uid for uid in user_ids if uid is not None}
        if not ids:
            return {}
        rows = (
            UserModel.objects.filter(id__in=ids, deleted_at__isnull=True)
            .values(*self._CARD_COLUMNS)
            .iterator()
        )
        return {row["id"]: self._card(row) for row in rows}

    @staticmethod
    def _card(row: dict[str, Any]) -> UserCardView:
        # given / middle / family, matching FullName.full ordering.
        parts = [row["first_name"], row["middle_name"], row["last_name"]]
        display_name = " ".join(part for part in parts if part)
        status = "active" if row["email_verified_at"] is not None else "registered"
        return UserCardView(
            id=str(row["id"]),
            email=row["email"],
            display_name=display_name,
            status=status,
        )
