"""Serializers for the platform operator's console — request validation and contract shape."""

from __future__ import annotations

from decimal import Decimal

from drf_spectacular.utils import inline_serializer
from rest_framework import serializers

from apps.platform.presentation.api.v1.loadtest import MAX_COUNT

__all__ = [
    "ConnectOrganizationRequestSerializer",
    "DashboardResponseSerializer",
    "LoadTestCleanupResponseSerializer",
    "LoadTestOverviewResponseSerializer",
    "LoadTestRunResponseSerializer",
    "OrganizationListResponseSerializer",
    "OrganizationResponseSerializer",
    "StartLoadTestRequestSerializer",
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


class StartLoadTestRequestSerializer(serializers.Serializer[dict[str, object]]):
    """Parameters of one diploma-generation load test.

    ``count`` is bounded by :data:`~apps.platform.presentation.api.v1.loadtest.MAX_COUNT`:
    seeding is a bulk insert and would happily take more, but the generation it
    triggers is a single long task in a single worker, and past that the honest
    thing to change is the worker rather than the tirage.
    """

    count = serializers.IntegerField(min_value=1, max_value=MAX_COUNT, default=500)
    nominations = serializers.IntegerField(min_value=1, max_value=100, default=5)
    # Optional: any diploma template with an uploaded PDF will do.
    templateId = serializers.UUIDField(required=False, allow_null=True)
    # One job per nomination rather than one for the whole competition — the
    # queue-pressure case rather than the single-worker-throughput one.
    split = serializers.BooleanField(default=False)
    force = serializers.BooleanField(default=False)

    def validate(self, attrs: dict[str, object]) -> dict[str, object]:
        count = int(str(attrs.get("count", 0)))
        nominations = int(str(attrs.get("nominations", 1)))
        if nominations > count:
            raise serializers.ValidationError("Номинаций не может быть больше, чем заявок.")
        return attrs


class _LoadTestJobSerializer(serializers.Serializer[dict[str, object]]):
    jobId = serializers.UUIDField()
    status = serializers.CharField()
    created = serializers.IntegerField()
    skipped = serializers.IntegerField()
    zipUrl = serializers.CharField(allow_null=True)
    error = serializers.CharField(allow_null=True)


class _LoadTestRunSerializer(serializers.Serializer[dict[str, object]]):
    competitionId = serializers.UUIDField()
    title = serializers.CharField()
    createdAt = serializers.DateTimeField()
    entries = serializers.IntegerField()
    nominations = serializers.IntegerField()
    diplomas = serializers.IntegerField()
    rendered = serializers.IntegerField()
    status = serializers.CharField()
    elapsedSeconds = serializers.FloatField(allow_null=True)
    msPerDiploma = serializers.IntegerField(allow_null=True)
    jobs = _LoadTestJobSerializer(many=True)


class _LoadTestTemplateSerializer(serializers.Serializer[dict[str, object]]):
    id = serializers.UUIDField()
    name = serializers.CharField()


LoadTestRunResponseSerializer = inline_serializer(
    name="PlatformLoadTestRunResponse",
    fields={"data": _LoadTestRunSerializer(), "meta": _meta},
)

LoadTestOverviewResponseSerializer = inline_serializer(
    name="PlatformLoadTestOverviewResponse",
    fields={
        "data": inline_serializer(
            name="PlatformLoadTestOverview",
            fields={
                "runs": _LoadTestRunSerializer(many=True),
                "templates": _LoadTestTemplateSerializer(many=True),
                "totals": inline_serializer(
                    name="PlatformLoadTestTotals",
                    fields={
                        "runs": serializers.IntegerField(),
                        "entries": serializers.IntegerField(),
                        "diplomas": serializers.IntegerField(),
                    },
                ),
                "maxCount": serializers.IntegerField(),
            },
        ),
        "meta": _meta,
    },
)

LoadTestCleanupResponseSerializer = inline_serializer(
    name="PlatformLoadTestCleanupResponse",
    fields={
        "data": inline_serializer(
            name="PlatformLoadTestCleanup",
            fields={
                "runs": serializers.IntegerField(),
                "files": serializers.IntegerField(),
                "diplomas": serializers.IntegerField(),
                "entries": serializers.IntegerField(),
            },
        ),
        "meta": _meta,
    },
)
