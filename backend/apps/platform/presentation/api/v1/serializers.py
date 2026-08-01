"""Serializers for the platform operator's console — request validation and contract shape."""

from __future__ import annotations

from decimal import Decimal

from drf_spectacular.utils import inline_serializer
from rest_framework import serializers

__all__ = [
    "ConnectOrganizationRequestSerializer",
    "DashboardResponseSerializer",
    "OrganizationListResponseSerializer",
    "OrganizationResponseSerializer",
    "UpdateOrganizationRequestSerializer",
]


class ConnectOrganizationRequestSerializer(serializers.Serializer[dict[str, object]]):
    """Connect a new organization: its name, its address, its owner and the terms."""

    name = serializers.CharField(max_length=200)
    # Optional: derived from the name when the operator does not care to pick one.
    slug = serializers.SlugField(max_length=100, required=False, allow_blank=True)
    ownerEmail = serializers.EmailField()
    commissionPercent = serializers.DecimalField(
        max_digits=5,
        decimal_places=2,
        min_value=Decimal("0"),
        max_value=Decimal("100"),
        required=False,
        default=Decimal("0"),
    )


class UpdateOrganizationRequestSerializer(serializers.Serializer[dict[str, object]]):
    """Change an organization's commercial terms or suspend/reactivate it."""

    commissionPercent = serializers.DecimalField(
        max_digits=5,
        decimal_places=2,
        min_value=Decimal("0"),
        max_value=Decimal("100"),
        required=False,
    )
    status = serializers.ChoiceField(choices=["ACTIVE", "SUSPENDED"], required=False)

    def validate(self, attrs: dict[str, object]) -> dict[str, object]:
        if not attrs:
            raise serializers.ValidationError("Provide commissionPercent, status, or both.")
        return attrs


class _OrganizationSerializer(serializers.Serializer[dict[str, object]]):
    id = serializers.UUIDField()
    name = serializers.CharField()
    slug = serializers.CharField()
    status = serializers.CharField()
    commissionPercent = serializers.DecimalField(max_digits=5, decimal_places=2)
    createdAt = serializers.DateTimeField()


class _OrganizationBreakdownSerializer(serializers.Serializer[dict[str, object]]):
    organizationId = serializers.UUIDField(allow_null=True)
    name = serializers.CharField()
    status = serializers.CharField()
    commissionPercent = serializers.DecimalField(max_digits=5, decimal_places=2)
    competitions = serializers.IntegerField()
    applications = serializers.IntegerField()
    statusCounts = serializers.DictField(child=serializers.IntegerField())
    expectedFees = serializers.CharField()
    settledFees = serializers.CharField()
    expectedCommission = serializers.CharField()
    settledCommission = serializers.CharField()


class _CompetitionOptionSerializer(serializers.Serializer[dict[str, object]]):
    id = serializers.UUIDField()
    title = serializers.CharField()
    organizationId = serializers.UUIDField(allow_null=True)
    organizationName = serializers.CharField()


_meta = inline_serializer(name="PlatformMeta", fields={"requestId": serializers.CharField()})

OrganizationResponseSerializer = inline_serializer(
    name="PlatformOrganizationResponse",
    fields={"data": _OrganizationSerializer(), "meta": _meta},
)

OrganizationListResponseSerializer = inline_serializer(
    name="PlatformOrganizationListResponse",
    fields={"data": _OrganizationSerializer(many=True), "meta": _meta},
)

DashboardResponseSerializer = inline_serializer(
    name="PlatformDashboardResponse",
    fields={
        "data": inline_serializer(
            name="PlatformDashboard",
            fields={
                "statusCounts": serializers.DictField(child=serializers.IntegerField()),
                "applications": serializers.IntegerField(),
                "expectedFees": serializers.CharField(),
                "settledFees": serializers.CharField(),
                "expectedCommission": serializers.CharField(),
                "settledCommission": serializers.CharField(),
                "organizations": _OrganizationBreakdownSerializer(many=True),
                "competitions": _CompetitionOptionSerializer(many=True),
            },
        ),
        "meta": _meta,
    },
)
