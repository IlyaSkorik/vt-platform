"""``OrganizationMapper`` — ACL between the ``Organization`` aggregate and its row."""

from __future__ import annotations

from apps.organization.domain.entities import Organization
from apps.organization.domain.value_objects import (
    BillingModel,
    CommissionRate,
    OrganizationId,
    OrganizationName,
    OrganizationProfile,
    OrganizationSlug,
    OrganizationStatus,
    PerformanceFeeSchedule,
    SupportingOrganization,
)
from apps.organization.infrastructure.models import OrganizationModel

__all__ = ["OrganizationMapper", "fee_schedule_from_json", "supporter_from_json"]


def fee_schedule_from_json(rows: object) -> PerformanceFeeSchedule | None:
    """Rebuild the fee schedule from its JSON column, or ``None`` when there is none.

    A row that is not a well-formed list of bands reads as "no schedule" rather than
    raising: rehydration re-validates nothing by contract, and an organization billed
    a percentage has an empty column here.
    """
    if not isinstance(rows, list) or not rows:
        return None
    return PerformanceFeeSchedule.of((row["min_participants"], row["max_participants"], row["amount"]) for row in rows if isinstance(row, dict))


_SUPPORTER_FIELDS: tuple[str, ...] = (
    "phone",
    "email",
    "website",
    "address",
    "vk",
    "instagram",
    "telegram",
    "legal_information",
)


def supporter_from_json(document: object) -> SupportingOrganization | None:
    """Rebuild the supporting entity from its JSON column, or ``None`` when there is none.

    A column that is not a document with a name reads as "no supporting entity"
    rather than raising: rehydration re-validates nothing by contract, and the
    column is NULL for every organization that is its own executor. Unknown keys
    are ignored, so a column written by a later shape does not break rehydration.
    """
    if not isinstance(document, dict):
        return None
    name = document.get("name")
    if not isinstance(name, str) or not name.strip():
        return None
    fields = {key: value for key in _SUPPORTER_FIELDS if isinstance(value := document.get(key), str)}
    return SupportingOrganization(name=name, **fields)


def _supporter_to_json(supporter: SupportingOrganization | None) -> dict[str, object] | None:
    """Flatten the supporting entity into its JSON column (``None`` when unset)."""
    if supporter is None:
        return None
    return {"name": supporter.name, **{key: getattr(supporter, key) for key in _SUPPORTER_FIELDS}}


def _schedule_to_json(schedule: PerformanceFeeSchedule | None) -> list[dict[str, object]]:
    """Flatten the fee schedule into its JSON column (an empty list when unset)."""
    if schedule is None:
        return []
    return [
        {
            "min_participants": tier.min_participants,
            "max_participants": tier.max_participants,
            "amount": str(tier.amount),
        }
        for tier in schedule.tiers
    ]


class OrganizationMapper:
    """Bidirectional translator between ``Organization`` and ``OrganizationModel``."""

    @staticmethod
    def to_domain(model: OrganizationModel) -> Organization:
        """Reconstruct the aggregate from a persisted row (no re-validation, no events)."""
        return Organization.rehydrate(
            organization_id=OrganizationId.from_uuid(model.id),
            name=OrganizationName(model.name),
            slug=OrganizationSlug(model.slug),
            status=OrganizationStatus(model.status),
            created_at=model.created_at,
            updated_at=model.updated_at,
            profile=OrganizationProfile(
                phone=model.phone,
                email=model.email,
                website=model.website,
                address=model.address,
                logo=model.logo,
                vk=model.vk,
                instagram=model.instagram,
                telegram=model.telegram,
                legal_information=model.legal_information,
            ),
            supporter=supporter_from_json(model.supporter),
            billing_model=BillingModel(model.billing_model),
            commission_rate=CommissionRate(model.commission_percent),
            fee_schedule=fee_schedule_from_json(model.performance_fee_tiers),
            deleted_at=model.deleted_at,
            version=model.version,
        )

    @staticmethod
    def to_model(entity: Organization) -> OrganizationModel:
        """Build a brand-new, unsaved ``OrganizationModel`` from an aggregate."""
        return OrganizationModel(**OrganizationMapper._to_columns(entity))

    @staticmethod
    def _to_columns(entity: Organization) -> dict[str, object]:
        """Flatten an aggregate into ``OrganizationModel`` column values."""
        profile = entity.profile
        return {
            "id": entity.id.value,
            "name": entity.name.value,
            "slug": entity.slug.value,
            "status": entity.status.value,
            "phone": profile.phone,
            "email": profile.email,
            "website": profile.website,
            "address": profile.address,
            "logo": profile.logo,
            "vk": profile.vk,
            "instagram": profile.instagram,
            "telegram": profile.telegram,
            "legal_information": profile.legal_information,
            "supporter": _supporter_to_json(entity.supporter),
            "billing_model": entity.billing_model.value,
            "commission_percent": entity.commission_rate.percent,
            "performance_fee_tiers": _schedule_to_json(entity.fee_schedule),
            "created_at": entity.created_at,
            "updated_at": entity.updated_at,
            "deleted_at": entity.deleted_at,
            "version": entity.version,
        }
