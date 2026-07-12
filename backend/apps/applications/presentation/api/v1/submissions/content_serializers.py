"""Request/response serializers for the Submission content endpoints (API-000 §7, §25).

Validate the JSON shape of building a submission (performance, participants,
teachers) and describe the full submission resource for the OpenAPI contract.
"""

from __future__ import annotations

from drf_spectacular.utils import inline_serializer
from rest_framework import serializers

__all__ = [
    "AddParticipantRequestSerializer",
    "CreditTeacherRequestSerializer",
    "SetPerformanceRequestSerializer",
    "SubmissionProblemDetailSerializer",
    "SubmissionResponseSerializer",
]


class SetPerformanceRequestSerializer(serializers.Serializer[dict[str, object]]):
    """Validate a set-performance request body."""

    title = serializers.CharField()
    durationSeconds = serializers.IntegerField(min_value=1)
    nominationId = serializers.UUIDField()
    disciplineId = serializers.UUIDField()
    ageCategoryId = serializers.UUIDField()
    participantGroupId = serializers.UUIDField()
    participationFormatId = serializers.UUIDField()


class AddParticipantRequestSerializer(serializers.Serializer[dict[str, object]]):
    """Validate an add-participant request body."""

    firstName = serializers.CharField()
    lastName = serializers.CharField()
    middleName = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    birthDate = serializers.DateField()
    gender = serializers.ChoiceField(choices=["MALE", "FEMALE"])


class CreditTeacherRequestSerializer(serializers.Serializer[dict[str, object]]):
    """Validate an add-teacher request body."""

    firstName = serializers.CharField()
    lastName = serializers.CharField()
    middleName = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    role = serializers.CharField()


class _PerformanceResourceSerializer(serializers.Serializer[dict[str, object]]):
    title = serializers.CharField()
    durationSeconds = serializers.IntegerField()
    nominationId = serializers.UUIDField()
    disciplineId = serializers.UUIDField()
    ageCategoryId = serializers.UUIDField()
    participantGroupId = serializers.UUIDField()
    participationFormatId = serializers.UUIDField()


class _ParticipantResourceSerializer(serializers.Serializer[dict[str, object]]):
    id = serializers.UUIDField()
    firstName = serializers.CharField()
    lastName = serializers.CharField()
    middleName = serializers.CharField(allow_null=True)
    birthDate = serializers.DateField()
    gender = serializers.CharField()


class _TeacherResourceSerializer(serializers.Serializer[dict[str, object]]):
    id = serializers.UUIDField()
    firstName = serializers.CharField()
    lastName = serializers.CharField()
    middleName = serializers.CharField(allow_null=True)
    role = serializers.CharField()


class _SubmissionAttachmentResourceSerializer(serializers.Serializer[dict[str, object]]):
    id = serializers.UUIDField()
    type = serializers.CharField()
    fileReference = serializers.CharField()
    caption = serializers.CharField(allow_null=True)


class _SubmissionPriceSerializer(serializers.Serializer[dict[str, object]]):
    amount = serializers.CharField()
    currency = serializers.CharField()
    calculatedAt = serializers.DateTimeField()


class SubmissionResourceSerializer(serializers.Serializer[dict[str, object]]):
    """The full submission resource (root + child graph)."""

    id = serializers.UUIDField()
    type = serializers.CharField(default="submission")
    competitionId = serializers.UUIDField()
    status = serializers.CharField()
    performance = _PerformanceResourceSerializer(allow_null=True)
    participants = _ParticipantResourceSerializer(many=True)
    teachers = _TeacherResourceSerializer(many=True)
    attachments = _SubmissionAttachmentResourceSerializer(many=True)
    price = _SubmissionPriceSerializer(allow_null=True)
    createdAt = serializers.DateTimeField()
    updatedAt = serializers.DateTimeField()


class _SubmissionMetaSerializer(serializers.Serializer[dict[str, object]]):
    requestId = serializers.CharField()


SubmissionResponseSerializer = inline_serializer(
    name="SubmissionResponse",
    fields={"data": SubmissionResourceSerializer(), "meta": _SubmissionMetaSerializer()},
)

SubmissionProblemDetailSerializer = inline_serializer(
    name="SubmissionProblemDetail",
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
