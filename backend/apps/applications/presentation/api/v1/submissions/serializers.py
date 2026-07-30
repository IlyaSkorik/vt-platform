"""Serializers for the Submission attachment endpoints (API-000 §7, §25).

The upload request is ``multipart/form-data``: the binary ``file`` plus an
``attachmentType`` and optional ``caption``. Response serializers exist for the
OpenAPI contract; the view builds the envelope from the DTO.
"""

from __future__ import annotations

from drf_spectacular.utils import inline_serializer
from rest_framework import serializers

__all__ = ["ProblemDetailSerializer", "SubmissionAttachmentResponseSerializer", "UploadAttachmentRequestSerializer"]

_ATTACHMENT_TYPES = ["MUSIC", "VIDEO", "IMAGE", "DOCUMENT", "BENEFIT"]


class UploadAttachmentRequestSerializer(serializers.Serializer[dict[str, object]]):
    """Validate a multipart upload request."""

    file = serializers.FileField()
    attachmentType = serializers.ChoiceField(choices=_ATTACHMENT_TYPES)
    caption = serializers.CharField(required=False, allow_null=True, allow_blank=True)


class _AttachmentResourceSerializer(serializers.Serializer[dict[str, object]]):
    id = serializers.UUIDField()
    type = serializers.CharField()
    fileReference = serializers.CharField()
    caption = serializers.CharField(allow_null=True)


class SubmissionAttachmentsResourceSerializer(serializers.Serializer[dict[str, object]]):
    """A compact submission view focused on its attachments."""

    id = serializers.UUIDField()
    status = serializers.CharField()
    attachments = _AttachmentResourceSerializer(many=True)


class _SubmissionAttachmentMetaSerializer(serializers.Serializer[dict[str, object]]):
    requestId = serializers.CharField()


SubmissionAttachmentResponseSerializer = inline_serializer(
    name="SubmissionAttachmentResponse",
    fields={"data": SubmissionAttachmentsResourceSerializer(), "meta": _SubmissionAttachmentMetaSerializer()},
)

ProblemDetailSerializer = inline_serializer(
    name="SubmissionAttachmentProblemDetail",
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
