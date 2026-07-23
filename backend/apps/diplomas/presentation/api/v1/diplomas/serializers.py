"""Request/response serializers for the Diplomas workspace REST surface.

Hand-written ``serializers.Serializer`` classes (not ``ModelSerializer``) with
camelCase fields, matching the platform's API contract (API-000). The response
serializers exist only to document the OpenAPI schema drf-spectacular emits; the
views build their payload dicts directly in :mod:`composition`.
"""

from __future__ import annotations

from rest_framework import serializers

__all__ = [
    "AssignmentResponseSerializer",
    "CreateAssignmentRequestSerializer",
    "CreateTemplateRequestSerializer",
    "TemplateResponseSerializer",
]


class CreateTemplateRequestSerializer(serializers.Serializer[dict[str, object]]):
    """Body for creating a template in the library."""

    name = serializers.CharField(max_length=160)
    description = serializers.CharField(
        max_length=500, required=False, allow_blank=True, default=""
    )


class CreateAssignmentRequestSerializer(serializers.Serializer[dict[str, object]]):
    """Body for creating a template assignment."""

    competitionId = serializers.UUIDField()
    categoryId = serializers.UUIDField()
    templateId = serializers.UUIDField()


class TemplateResponseSerializer(serializers.Serializer[dict[str, object]]):
    """A diploma template in the library."""

    id = serializers.UUIDField()
    name = serializers.CharField()
    description = serializers.CharField(allow_blank=True)
    usageCount = serializers.IntegerField()
    updatedAt = serializers.DateTimeField()


class AssignmentResponseSerializer(serializers.Serializer[dict[str, object]]):
    """A template assignment (competition + nomination -> template)."""

    id = serializers.UUIDField()
    competitionId = serializers.UUIDField()
    competition = serializers.CharField(allow_null=True)
    categoryId = serializers.UUIDField()
    nomination = serializers.CharField(allow_null=True)
    templateId = serializers.UUIDField()
    templateName = serializers.CharField()
    createdAt = serializers.DateTimeField()
    updatedAt = serializers.DateTimeField()
