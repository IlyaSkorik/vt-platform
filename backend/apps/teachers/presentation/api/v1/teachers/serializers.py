"""Serializers for the Teacher Directory API endpoints (API-000 §7, §25).

Serializers here do exactly one job: **validate the request's JSON shape** - field
presence, types, and simple format. They enforce no business rules (role/email/phone
validity is the domain's; ownership is the use case's) and never touch the ORM.
Request fields use the API's camelCase wire names. The response serializers exist so
drf-spectacular can render an accurate OpenAPI 3.1 contract; views build the
envelopes directly from DTOs.
"""

from __future__ import annotations

from drf_spectacular.utils import inline_serializer
from rest_framework import serializers

__all__ = [
    "AddTeacherRequestSerializer",
    "ProblemDetailSerializer",
    "TeacherDirectoryResponseSerializer",
    "TeacherResponseSerializer",
    "UpdateTeacherRequestSerializer",
]


# ---------------------------------------------------------------------------
# Request serializers (validation only)
# ---------------------------------------------------------------------------


class AddTeacherRequestSerializer(serializers.Serializer[dict[str, object]]):
    """Validate an add-teacher request body."""

    firstName = serializers.CharField()
    lastName = serializers.CharField()
    middleName = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    role = serializers.CharField()
    email = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    phone = serializers.CharField(required=False, allow_null=True, allow_blank=True)


class UpdateTeacherRequestSerializer(AddTeacherRequestSerializer):
    """Validate an update-teacher request body (same shape as add)."""


# ---------------------------------------------------------------------------
# Response serializers (OpenAPI schema only; API-000 §7, §25)
# ---------------------------------------------------------------------------


class TeacherMetaSerializer(serializers.Serializer[dict[str, object]]):
    """The ``meta`` envelope block (API-000 §7.3), named to avoid a component clash."""

    requestId = serializers.CharField()


class TeacherResourceSerializer(serializers.Serializer[dict[str, object]]):
    """A teacher directory resource."""

    id = serializers.UUIDField()
    type = serializers.CharField(default="teacher")
    ownerId = serializers.UUIDField()
    firstName = serializers.CharField()
    lastName = serializers.CharField()
    middleName = serializers.CharField(allow_null=True)
    displayName = serializers.CharField()
    role = serializers.CharField()
    email = serializers.CharField(allow_null=True)
    phone = serializers.CharField(allow_null=True)
    status = serializers.CharField()
    archivedAt = serializers.DateTimeField(allow_null=True)
    createdAt = serializers.DateTimeField()
    updatedAt = serializers.DateTimeField()


TeacherResponseSerializer = inline_serializer(
    name="TeacherResponse",
    fields={"data": TeacherResourceSerializer(), "meta": TeacherMetaSerializer()},
)

TeacherDirectoryResponseSerializer = inline_serializer(
    name="TeacherDirectoryResponse",
    fields={"data": TeacherResourceSerializer(many=True), "meta": TeacherMetaSerializer()},
)

ProblemDetailSerializer = inline_serializer(
    name="TeachersProblemDetail",
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
