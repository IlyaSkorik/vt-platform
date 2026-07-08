"""Serializers for the Participants API endpoints (API-000 §7, §25).

Serializers here do exactly one job: **validate the request's JSON shape** — field
presence, types, and simple format. They enforce no business rules: the display
alias's pseudonymity is a domain policy (JDG-006), the date of birth's validity and
the activation preconditions (PRT-001, PRT-002) are the domain's, and uniqueness is
a use-case concern. A serializer never touches the ORM and issues no query.

Request fields use the API's camelCase wire names; the view maps validated data
onto the application command. The response serializers are declared purely so
drf-spectacular can render an accurate OpenAPI 3.1 contract (API-000 §25) — the
views build the response envelopes directly from DTOs.
"""

from __future__ import annotations

from drf_spectacular.utils import inline_serializer
from rest_framework import serializers

__all__ = [
    "CreateParticipantRequestSerializer",
    "ProposeGuardianLinkRequestSerializer",
]


# ---------------------------------------------------------------------------
# Request serializers (validation only)
# ---------------------------------------------------------------------------


class CreateParticipantRequestSerializer(serializers.Serializer[dict[str, object]]):
    """Validate a create-participant request body."""

    firstName = serializers.CharField()
    lastName = serializers.CharField()
    middleName = serializers.CharField(required=False, allow_null=True)
    dateOfBirth = serializers.DateField()
    displayAlias = serializers.CharField()
    createdByType = serializers.ChoiceField(
        choices=["guardian", "teacher"], required=False, default="guardian"
    )


class ProposeGuardianLinkRequestSerializer(serializers.Serializer[dict[str, object]]):
    """Validate a propose-guardian-link request body."""

    guardianId = serializers.UUIDField()
    relationshipType = serializers.ChoiceField(
        choices=["mother", "father", "legal_guardian", "other"]
    )


# ---------------------------------------------------------------------------
# Response serializers (OpenAPI schema only; API-000 §7, §25)
# ---------------------------------------------------------------------------


class ParticipantMetaSerializer(serializers.Serializer[dict[str, object]]):
    """The ``meta`` envelope block (API-000 §7.3).

    Named distinctly from other contexts' meta blocks so drf-spectacular emits a
    uniquely-named OpenAPI component (no cross-context name collision).
    """

    requestId = serializers.CharField()


class GuardianLinkResourceSerializer(serializers.Serializer[dict[str, object]]):
    """A guardian relationship embedded in a participant resource."""

    guardianId = serializers.UUIDField()
    relationshipType = serializers.CharField()
    status = serializers.CharField()
    establishedAt = serializers.DateTimeField(allow_null=True)


class ParticipantResourceSerializer(serializers.Serializer[dict[str, object]]):
    """A participant resource (DIA-001 §4.2)."""

    id = serializers.UUIDField()
    type = serializers.CharField(default="participant")
    displayAlias = serializers.CharField()
    displayName = serializers.CharField()
    status = serializers.CharField()
    dateOfBirth = serializers.DateField()
    guardianLinks = GuardianLinkResourceSerializer(many=True)
    institutionId = serializers.UUIDField(allow_null=True)
    consentRecorded = serializers.BooleanField()
    createdAt = serializers.DateTimeField()
    updatedAt = serializers.DateTimeField()


ParticipantResponseSerializer = inline_serializer(
    name="ParticipantResponse",
    fields={"data": ParticipantResourceSerializer(), "meta": ParticipantMetaSerializer()},
)

ProblemDetailSerializer = inline_serializer(
    name="ParticipantsProblemDetail",
    fields={
        "type": serializers.URLField(),
        "title": serializers.CharField(),
        "status": serializers.IntegerField(),
        "detail": serializers.CharField(),
        "instance": serializers.CharField(),
        "requestId": serializers.CharField(),
        "code": serializers.CharField(required=False),
        "errors": serializers.ListField(child=serializers.DictField(), required=False),
    },
)
