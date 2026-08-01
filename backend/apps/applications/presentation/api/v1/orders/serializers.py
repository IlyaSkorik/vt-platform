"""Serializers for the Application (order) API endpoints (API-000 §7, §25).

Serializers validate the request's JSON shape only - no business rules, no ORM.
Request fields use camelCase wire names; the view maps validated data onto an
application command. Response serializers exist purely for the OpenAPI 3.1 contract;
the views build envelopes directly from DTOs.
"""

from __future__ import annotations

from drf_spectacular.utils import inline_serializer
from rest_framework import serializers

__all__ = [
    "ApplicationDirectoryResponseSerializer",
    "ApplicationResponseSerializer",
    "CreateApplicationRequestSerializer",
    "ProblemDetailSerializer",
    "RecordConsentsRequestSerializer",
    "SelectEducationalOrganizationRequestSerializer",
    "SelectServiceRequestSerializer",
]


# ---------------------------------------------------------------------------
# Request serializers (validation only)
# ---------------------------------------------------------------------------


class CreateApplicationRequestSerializer(serializers.Serializer[dict[str, object]]):
    """Validate a create-application request body."""

    competitionId = serializers.UUIDField()


class SelectServiceRequestSerializer(serializers.Serializer[dict[str, object]]):
    """Validate a select-additional-service request body."""

    serviceId = serializers.UUIDField()
    quantity = serializers.IntegerField(min_value=1, default=1)


class _ConsentItemSerializer(serializers.Serializer[dict[str, object]]):
    """One accepted consent (code + accepted text version)."""

    code = serializers.CharField()
    version = serializers.CharField()


class RecordConsentsRequestSerializer(serializers.Serializer[dict[str, object]]):
    """Validate a record-consents request body."""

    consents = _ConsentItemSerializer(many=True)


class SelectEducationalOrganizationRequestSerializer(serializers.Serializer[dict[str, object]]):
    """Validate a select-educational-organization request body."""

    educationalOrganizationId = serializers.UUIDField()


# ---------------------------------------------------------------------------
# Response serializers (OpenAPI schema only)
# ---------------------------------------------------------------------------


class ApplicationMetaSerializer(serializers.Serializer[dict[str, object]]):
    """The ``meta`` envelope block, named to avoid a component clash."""

    requestId = serializers.CharField()


class _SubmissionRefSerializer(serializers.Serializer[dict[str, object]]):
    submissionId = serializers.UUIDField()
    performanceTitle = serializers.CharField(allow_blank=True)
    participantDisplayName = serializers.CharField(allow_blank=True)
    nomination = serializers.CharField(allow_blank=True)
    discipline = serializers.CharField(allow_blank=True)
    status = serializers.CharField()
    priceAmount = serializers.CharField(allow_null=True)
    currency = serializers.CharField(allow_null=True)


class _ServiceLineSerializer(serializers.Serializer[dict[str, object]]):
    serviceId = serializers.UUIDField()
    name = serializers.CharField()
    unitAmount = serializers.CharField()
    quantity = serializers.IntegerField()
    lineAmount = serializers.CharField()
    currency = serializers.CharField()


class _ConsentViewSerializer(serializers.Serializer[dict[str, object]]):
    code = serializers.CharField()
    version = serializers.CharField()
    acceptedAt = serializers.DateTimeField()


class _TotalPriceSerializer(serializers.Serializer[dict[str, object]]):
    totalAmount = serializers.CharField()
    submissionsAmount = serializers.CharField()
    servicesAmount = serializers.CharField()
    currency = serializers.CharField()
    calculatedAt = serializers.DateTimeField()


class _PaymentReceiptSerializer(serializers.Serializer[dict[str, object]]):
    id = serializers.CharField()
    fileReference = serializers.CharField()
    uploadedAt = serializers.DateTimeField()


class ApplicationResourceSerializer(serializers.Serializer[dict[str, object]]):
    """An application (order) resource."""

    id = serializers.UUIDField()
    type = serializers.CharField(default="application")
    competitionId = serializers.UUIDField()
    applicantId = serializers.UUIDField()
    status = serializers.CharField()
    hasCorrections = serializers.BooleanField()
    correctionComment = serializers.CharField(allow_null=True)
    educationalOrganizationId = serializers.UUIDField(allow_null=True)
    organizationName = serializers.CharField(allow_null=True)
    submissions = _SubmissionRefSerializer(many=True)
    services = _ServiceLineSerializer(many=True)
    consents = _ConsentViewSerializer(many=True)
    totalPrice = _TotalPriceSerializer(allow_null=True)
    paymentReceipts = _PaymentReceiptSerializer(many=True)
    paidAt = serializers.DateTimeField(allow_null=True)
    createdAt = serializers.DateTimeField()
    updatedAt = serializers.DateTimeField()


class UploadReceiptRequestSerializer(serializers.Serializer[dict[str, object]]):
    """Validate one payment-receipt upload (a ``multipart/form-data`` file part)."""

    file = serializers.FileField()


class ApplicationSummaryResourceSerializer(serializers.Serializer[dict[str, object]]):
    """A compact application summary for listing screens."""

    id = serializers.UUIDField()
    type = serializers.CharField(default="application")
    competitionId = serializers.UUIDField()
    status = serializers.CharField()
    hasCorrections = serializers.BooleanField()
    submissionCount = serializers.IntegerField()
    totalAmount = serializers.CharField(allow_null=True)
    currency = serializers.CharField(allow_null=True)
    createdAt = serializers.DateTimeField()
    updatedAt = serializers.DateTimeField()


ApplicationResponseSerializer = inline_serializer(
    name="ApplicationResponse",
    fields={"data": ApplicationResourceSerializer(), "meta": ApplicationMetaSerializer()},
)

ApplicationDirectoryResponseSerializer = inline_serializer(
    name="ApplicationListResponse",
    fields={"data": ApplicationSummaryResourceSerializer(many=True), "meta": ApplicationMetaSerializer()},
)

ProblemDetailSerializer = inline_serializer(
    name="ApplicationsProblemDetail",
    fields={
        "type": serializers.URLField(),
        "title": serializers.CharField(),
        "status": serializers.IntegerField(),
        "detail": serializers.CharField(),
        "instance": serializers.CharField(),
        "requestId": serializers.CharField(),
        "errors": serializers.ListField(child=serializers.DictField(), required=False),
    },
)
