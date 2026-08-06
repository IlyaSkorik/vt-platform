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
from apps.identity.infrastructure.models import UserConsentModel, UserModel
from apps.identity.infrastructure.models.consent import ConsentStatus

__all__ = ["DjangoConsentDirectory", "DjangoUserDirectory"]


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
        rows = UserModel.objects.filter(id__in=ids, deleted_at__isnull=True).values(*self._CARD_COLUMNS).iterator()
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


class DjangoConsentDirectory:
    """Answers one question for other contexts: is this consent real, and theirs?

    **Why it exists.** Other contexts store a consent *reference* — the Participants
    registry keeps one against a child, the Teacher directory against an adult — and a
    reference that nobody checks is not evidence of anything. Without this seam a client
    could send any UUID, or somebody else's consent, or one it had already withdrawn, and
    the row would look just as compliant as a real one.

    Consent stays owned by Identity: this publishes a verdict, never the record, so no
    other context learns the shape of the journal (ARCH-001 §7.3, §9.2).
    """

    #: The statuses that mean "in force right now".
    _ACTIVE = (ConsentStatus.GRANTED, ConsentStatus.ACTIVE)

    def is_in_force(self, consent_id: str, *, user_id: str, consent_type: str) -> bool:
        """Whether ``consent_id`` is an active consent of that type held by that account.

        All three conditions matter, and for different reasons: the type, because a
        marketing opt-in must not pass as permission to hold a child's data; the account,
        because one user must not be able to lean on another's consent; the status,
        because a withdrawn consent is precisely the case the whole journal exists to
        make visible. A malformed id is simply not in force — the caller gets the same
        answer as for an unknown one, and learns nothing from the difference.
        """
        try:
            parsed = uuid.UUID(str(consent_id))
            owner = uuid.UUID(str(user_id))
        except (TypeError, ValueError):
            return False
        return UserConsentModel.objects.filter(
            id=parsed,
            user_id=owner,
            consent_type=consent_type,
            status__in=self._ACTIVE,
            deleted_at__isnull=True,
        ).exists()
