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
    """Validate a set-performance request body.

    ``comment`` is the applicant's optional free-text note for the organizers about
    this act (stage entry, props, equipment, backing-track quirks).
    """

    title = serializers.CharField()
    durationSeconds = serializers.IntegerField(min_value=1)
    nominationId = serializers.UUIDField()
    disciplineId = serializers.UUIDField()
    ageCategoryId = serializers.UUIDField()
    participantGroupId = serializers.UUIDField()
    participationFormatId = serializers.UUIDField()
    comment = serializers.CharField(required=False, allow_blank=True, max_length=1_000)


class AddParticipantRequestSerializer(serializers.Serializer[dict[str, object]]):
    """Validate an add-participant request body.

    A participant is normally chosen from the Participant Registry: send
    ``participantRegistryId`` plus a snapshot. A solo carries the structured name +
    birth date + gender; a collective carries only ``displayName``. All person
    fields are optional so both shapes (and legacy manual entry) validate.
    """

    participantRegistryId = serializers.UUIDField(required=False, allow_null=True)
    displayName = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    firstName = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    lastName = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    middleName = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    birthDate = serializers.DateField(required=False, allow_null=True)
    gender = serializers.ChoiceField(choices=["MALE", "FEMALE", "OTHER"], required=False, allow_null=True)
    memberCount = serializers.IntegerField(required=False, allow_null=True, min_value=1)


class CreditTeacherRequestSerializer(serializers.Serializer[dict[str, object]]):
    """Validate an add-teacher request body.

    A teacher is normally chosen from the Teacher Directory: send
    ``teacherDirectoryId`` plus the name/role snapshot preserved on the submission.
    """

    teacherDirectoryId = serializers.UUIDField(required=False, allow_null=True)
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
    comment = serializers.CharField(allow_blank=True)


class _ParticipantResourceSerializer(serializers.Serializer[dict[str, object]]):
    id = serializers.UUIDField()
    registryParticipantId = serializers.UUIDField(allow_null=True)
    displayName = serializers.CharField()
    firstName = serializers.CharField(allow_null=True)
    lastName = serializers.CharField(allow_null=True)
    middleName = serializers.CharField(allow_null=True)
    birthDate = serializers.DateField(allow_null=True)
    gender = serializers.CharField(allow_null=True)
    memberCount = serializers.IntegerField()


class _TeacherResourceSerializer(serializers.Serializer[dict[str, object]]):
    id = serializers.UUIDField()
    teacherDirectoryId = serializers.UUIDField(allow_null=True)
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


class _SubmissionStatusHistorySerializer(serializers.Serializer[dict[str, object]]):
    fromStatus = serializers.CharField(allow_null=True)
    toStatus = serializers.CharField()
    occurredAt = serializers.DateTimeField()


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
    statusHistory = _SubmissionStatusHistorySerializer(many=True)
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
