"""Submission attachment controllers for the Applications REST API v1.

File uploads for a submission: a ``multipart/form-data`` POST that validates the
file against the competition's upload constraints, stores it, and attaches the
resulting reference; and a DELETE to remove an attachment. Both are owner-scoped
(the acting applicant is the JWT subject).
"""

from __future__ import annotations

from typing import Any

from drf_spectacular.utils import OpenApiResponse, extend_schema
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.applications.application.dto import SubmissionOperationResultDto
from apps.applications.application.dto.commands import RemoveAttachmentCommand, UploadAttachmentCommand
from apps.applications.application.exceptions import ApplicationError
from apps.applications.presentation.api.v1 import problems
from apps.applications.presentation.api.v1.submissions import composition
from apps.applications.presentation.api.v1.submissions.serializers import (
    ProblemDetailSerializer,
    SubmissionAttachmentResponseSerializer,
    UploadAttachmentRequestSerializer,
)
from apps.identity.infrastructure.auth import CredentialAwareJWTAuthentication

_TAG = "Submission Attachments"


def _attachments_resource(result: SubmissionOperationResultDto) -> dict[str, Any]:
    dto = result.submission
    return {
        "id": dto.id,
        "status": dto.status,
        "attachments": [{"id": a.id, "type": a.type, "fileReference": a.file_reference, "caption": a.caption} for a in dto.attachments],
    }


def _envelope(request: Request, data: Any, *, status: int) -> Response:
    correlation_id = problems.request_id(request)
    return Response({"data": data, "meta": {"requestId": correlation_id}}, status=status, headers={"X-Request-ID": correlation_id})


class _AuthenticatedView(APIView):
    authentication_classes = (CredentialAwareJWTAuthentication,)
    permission_classes = (IsAuthenticated,)


class SubmissionAttachmentsView(_AuthenticatedView):
    """POST /api/v1/submissions/{id}/attachments - upload and attach a file."""

    parser_classes = (MultiPartParser, FormParser)

    @extend_schema(
        tags=[_TAG],
        operation_id="submissions_upload_attachment",
        summary="Upload an attachment",
        request={"multipart/form-data": UploadAttachmentRequestSerializer},
        responses={
            201: SubmissionAttachmentResponseSerializer,
            400: OpenApiResponse(ProblemDetailSerializer, description="Malformed request."),
            404: OpenApiResponse(ProblemDetailSerializer, description="Submission not found."),
            409: OpenApiResponse(ProblemDetailSerializer, description="Submission not editable."),
            413: OpenApiResponse(ProblemDetailSerializer, description="File too large."),
            415: OpenApiResponse(ProblemDetailSerializer, description="Unsupported file type."),
        },
    )
    def post(self, request: Request, submission_id: str) -> Response:
        serializer = UploadAttachmentRequestSerializer(data=request.data)
        if not serializer.is_valid():
            return problems.validation_problem(serializer.errors, instance=request.path, request=request)
        upload = serializer.validated_data["file"]
        caption = serializer.validated_data.get("caption")
        command = UploadAttachmentCommand(
            submission_id=submission_id,
            requested_by=str(request.user.id),
            attachment_type=str(serializer.validated_data["attachmentType"]),
            filename=str(upload.name),
            content_type=str(getattr(upload, "content_type", "") or "application/octet-stream"),
            content=upload.read(),
            caption=str(caption) if caption else None,
        )
        try:
            result = composition.build_upload_attachment_handler().handle(command)
        except ApplicationError as exc:
            return problems.application_problem(exc, instance=request.path, request=request)
        return _envelope(request, _attachments_resource(result), status=201)


class SubmissionAttachmentDetailView(_AuthenticatedView):
    """DELETE /api/v1/submissions/{id}/attachments/{attachmentId} - remove an attachment."""

    @extend_schema(
        tags=[_TAG],
        operation_id="submissions_remove_attachment",
        summary="Remove an attachment",
        request=None,
        responses={200: SubmissionAttachmentResponseSerializer, 404: OpenApiResponse(ProblemDetailSerializer, description="Not found.")},
    )
    def delete(self, request: Request, submission_id: str, attachment_id: str) -> Response:
        command = RemoveAttachmentCommand(submission_id=submission_id, requested_by=str(request.user.id), attachment_id=attachment_id)
        try:
            result = composition.build_remove_attachment_handler().handle(command)
        except ApplicationError as exc:
            return problems.application_problem(exc, instance=request.path, request=request)
        return _envelope(request, _attachments_resource(result), status=200)
