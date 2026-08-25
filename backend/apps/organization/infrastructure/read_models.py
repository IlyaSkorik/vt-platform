"""Concrete read-model adapters for the Organization bounded context.

Read side only (CQRS): these query the ``organization_*`` tables directly and
project rows into the flat, primitive-only views published by
:mod:`apps.organization.application.read_models`. They rehydrate no aggregate and
enforce no invariant — a projection is a fast, denormalized read path, not a
write path (ARCH-001 §7.2, §14).
"""

from __future__ import annotations

import uuid
from collections.abc import Iterable
from typing import Any

from apps.organization.application.read_models import OrganizerCardView, SupportingOrganizationCardView
from apps.organization.infrastructure.mappers.organization_mapper import supporter_from_json
from apps.organization.infrastructure.models import OrganizationModel

__all__ = ["DjangoOrganizationDirectory"]


class DjangoOrganizationDirectory:
    """Concrete :class:`OrganizationDirectory` over the organization table.

    Structurally satisfies the port (no inheritance — the seam is structural by
    design, mirroring :class:`StaffMembershipReader`). One indexed query resolves
    the whole id set; soft-deleted rows are excluded.
    """

    _CARD_COLUMNS = (
        "id",
        "name",
        "logo",
        "phone",
        "email",
        "website",
        "address",
        "vk",
        "instagram",
        "telegram",
        "legal_information",
        "supporter",
    )

    def resolve(self, organizer_ids: Iterable[uuid.UUID]) -> dict[uuid.UUID, OrganizerCardView]:
        ids = {oid for oid in organizer_ids if oid is not None}
        if not ids:
            return {}
        rows = OrganizationModel.objects.filter(id__in=ids, deleted_at__isnull=True).values(*self._CARD_COLUMNS).iterator()
        return {row["id"]: self._card(row) for row in rows}

    def default_organizer(self) -> OrganizerCardView | None:
        # Mirrors DjangoOrganizationRepository.get_default: the earliest-created
        # active row is the authoritative singleton organization.
        row = OrganizationModel.objects.filter(deleted_at__isnull=True).order_by("created_at").values(*self._CARD_COLUMNS).first()
        return self._card(row) if row is not None else None

    @staticmethod
    def _card(row: dict[str, Any]) -> OrganizerCardView:
        return OrganizerCardView(
            id=str(row["id"]),
            name=row["name"],
            logo=row["logo"],
            phone=row["phone"],
            email=row["email"],
            website=row["website"],
            address=row["address"],
            vk=row["vk"],
            instagram=row["instagram"],
            telegram=row["telegram"],
            legal_information=row["legal_information"],
            supporter=_supporter_card(row["supporter"]),
        )


def _supporter_card(document: object) -> SupportingOrganizationCardView | None:
    """Project the supporter JSON column into its published card view.

    Reuses the mapper's reader rather than re-parsing the column here: the write
    side and this read side would otherwise disagree about what a malformed
    document means, and that disagreement is invisible until one of them is wrong.
    """
    supporter = supporter_from_json(document)
    if supporter is None:
        return None
    return SupportingOrganizationCardView(
        name=supporter.name,
        phone=supporter.phone,
        email=supporter.email,
        website=supporter.website,
        address=supporter.address,
        vk=supporter.vk,
        instagram=supporter.instagram,
        telegram=supporter.telegram,
        legal_information=supporter.legal_information,
    )
