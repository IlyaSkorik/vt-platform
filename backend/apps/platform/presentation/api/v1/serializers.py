"""Serializers for the platform operator's console — request validation and contract shape."""

from __future__ import annotations

from decimal import Decimal

from drf_spectacular.utils import inline_serializer
from rest_framework import serializers

from apps.platform.presentation.api.v1.loadtest import MAX_COUNT

__all__ = [
    "BILLING_MODELS",
    "ConnectOrganizationRequestSerializer",
    "DashboardResponseSerializer",
    "FeeTierSerializer",
    "LoadTestCleanupResponseSerializer",
    "LoadTestOverviewResponseSerializer",
    "LoadTestRunResponseSerializer",
    "OrganizationListResponseSerializer",
    "OrganizationResponseSerializer",
    "PurgePlanResponseSerializer",
    "PurgeSearchResponseSerializer",
    "StartLoadTestRequestSerializer",
    "UpdateOrganizationRequestSerializer",
]


#: The two commercial terms an organization can be connected under (mirrors the
#: domain ``BillingModel``; kept here as plain strings so the presentation edge does
#: not import the domain enum just to spell a choice list).
BILLING_MODELS = ("COMMISSION_PERCENT", "PER_PERFORMANCE_FEE")


class FeeTierSerializer(serializers.Serializer[dict[str, object]]):
    """One band of a per-performance fee schedule: a headcount range and its price.

    ``maxParticipants`` may be ``null`` — the open-ended top band ("6 and up"). The
    band set as a whole (sorted, gap-free, starting at one, open-ended at the top)
    is validated by the domain, which owns that invariant; this only checks that
    each row is a sane range with a sane price.
    """

    minParticipants = serializers.IntegerField(min_value=1, max_value=10000)
    maxParticipants = serializers.IntegerField(min_value=1, max_value=10000, required=False, allow_null=True, default=None)
    amount = serializers.DecimalField(max_digits=12, decimal_places=2, min_value=Decimal("0"))


def _validate_terms(attrs: dict[str, object]) -> dict[str, object]:
    """Refuse a payload whose billing model and terms disagree.

    A per-performance model needs bands; a percentage model must not carry them. An
    unnamed model is inferred from the bands — they are the only thing bands can
    mean — so a caller never has to say the same thing twice.
    """
    tiers = attrs.get("feeTiers")
    model = attrs.get("billingModel")
    if model is None and tiers:
        model = "PER_PERFORMANCE_FEE"
        attrs["billingModel"] = model
    if model == "PER_PERFORMANCE_FEE" and not tiers:
        raise serializers.ValidationError({"feeTiers": "Тарифная сетка должна содержать хотя бы одно правило."})
    if model == "COMMISSION_PERCENT" and tiers:
        raise serializers.ValidationError({"feeTiers": "Тарифная сетка не применяется при комиссии в процентах."})
    return attrs


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
    # Unset means "infer it": bands connect the organization on the fee model, their
    # absence on the percentage one.
    billingModel = serializers.ChoiceField(choices=list(BILLING_MODELS), required=False)
    feeTiers = FeeTierSerializer(many=True, required=False)

    def validate(self, attrs: dict[str, object]) -> dict[str, object]:
        attrs = _validate_terms(attrs)
        attrs.setdefault("billingModel", "COMMISSION_PERCENT")
        return attrs


class UpdateOrganizationRequestSerializer(serializers.Serializer[dict[str, object]]):
    """Change an organization's commercial terms or suspend/reactivate it."""

    commissionPercent = serializers.DecimalField(
        max_digits=5,
        decimal_places=2,
        min_value=Decimal("0"),
        max_value=Decimal("100"),
        required=False,
    )
    billingModel = serializers.ChoiceField(choices=list(BILLING_MODELS), required=False)
    feeTiers = FeeTierSerializer(many=True, required=False)
    status = serializers.ChoiceField(choices=["ACTIVE", "SUSPENDED"], required=False)

    def validate(self, attrs: dict[str, object]) -> dict[str, object]:
        if not attrs:
            raise serializers.ValidationError("Измените хотя бы одно поле: комиссию, модель оплаты, тарифы или статус.")
        attrs = _validate_terms(attrs)
        if attrs.get("billingModel") == "COMMISSION_PERCENT" and "commissionPercent" not in attrs:
            raise serializers.ValidationError({"commissionPercent": "Укажите ставку комиссии."})
        return attrs


class _FeeTierResponseSerializer(serializers.Serializer[dict[str, object]]):
    minParticipants = serializers.IntegerField()
    maxParticipants = serializers.IntegerField(allow_null=True)
    # A decimal string, like every other money figure on this console.
    amount = serializers.CharField()


class _OrganizationSerializer(serializers.Serializer[dict[str, object]]):
    id = serializers.UUIDField()
    name = serializers.CharField()
    slug = serializers.CharField()
    status = serializers.CharField()
    billingModel = serializers.ChoiceField(choices=list(BILLING_MODELS))
    commissionPercent = serializers.DecimalField(max_digits=5, decimal_places=2)
    feeTiers = _FeeTierResponseSerializer(many=True)
    createdAt = serializers.DateTimeField()


class _OrganizationBreakdownSerializer(serializers.Serializer[dict[str, object]]):
    organizationId = serializers.UUIDField(allow_null=True)
    name = serializers.CharField()
    status = serializers.CharField()
    billingModel = serializers.ChoiceField(choices=list(BILLING_MODELS))
    commissionPercent = serializers.DecimalField(max_digits=5, decimal_places=2)
    feeTiers = _FeeTierResponseSerializer(many=True)
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


def _head_count(name: str, subset: str) -> serializers.Serializer[dict[str, object]]:
    """One audience figure: the total, plus the subset named beside it.

    Built by a helper because the three groups differ only in what their subset is
    called, and three near-identical inline serializers would drift the first time
    one of them gained a field.
    """
    return inline_serializer(name=name, fields={"total": serializers.IntegerField(), subset: serializers.IntegerField()})


AudienceResponseSerializer = inline_serializer(
    name="PlatformAudienceResponse",
    fields={
        "data": inline_serializer(
            name="PlatformAudience",
            fields={
                "cabinets": _head_count("PlatformAudienceCabinets", "emailVerified"),
                "participants": _head_count("PlatformAudienceParticipants", "archived"),
                "teachers": _head_count("PlatformAudienceTeachers", "archived"),
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


# ----------------------------------------------------------------------
# The eraser
# ----------------------------------------------------------------------


class _PurgeTargetSerializer(serializers.Serializer[dict[str, object]]):
    """One erasable thing, as the console names it in a list and in a dialog."""

    kind = serializers.CharField()
    id = serializers.UUIDField()
    #: What the operator has to retype to confirm — a title, a name, an email.
    #: The ignore is DRF's own shape: the metaclass pops declared fields off the
    #: class, so this never actually shadows ``Field.label``.
    label = serializers.CharField()  # type: ignore[assignment]
    hint = serializers.CharField()


class _PurgeRowSerializer(serializers.Serializer[dict[str, object]]):
    """One table's contribution to the plan: the machine name, and the human one."""

    table = serializers.CharField()
    label = serializers.CharField()  # type: ignore[assignment]
    count = serializers.IntegerField()


_PurgePlanSerializer = inline_serializer(
    name="PlatformPurgePlan",
    fields={
        "target": _PurgeTargetSerializer(),
        "rows": _PurgeRowSerializer(many=True),
        "total": serializers.IntegerField(),
        "files": serializers.IntegerField(),
        "warnings": serializers.ListField(child=serializers.CharField()),
    },
)

PurgePlanResponseSerializer = inline_serializer(
    name="PlatformPurgePlanResponse",
    fields={"data": _PurgePlanSerializer, "meta": _meta},
)

PurgeSearchResponseSerializer = inline_serializer(
    name="PlatformPurgeSearchResponse",
    fields={"data": _PurgeTargetSerializer(many=True), "meta": _meta},
)
