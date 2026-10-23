"""Files put onto an entry by the organizer, on the applicant's behalf.

The paper trail of a festival is rarely as tidy as the form. A backing track arrives
in a message the night before, a video comes on a flash drive at the rehearsal, a
photograph is emailed because the applicant's phone would not upload it over the
hall's wifi. Until now all of those ended the same way: the organizer asking the
applicant to log in and upload the file themselves — after the deadline, when the
applicant has stopped checking their email, and while the sound desk waits.

So the organizer may attach the file where they are already standing: in the entry's
own card. The two differences from the applicant's own upload live in the use case
(authority, and no upload deadline) — see
:class:`~apps.applications.application.commands.attachments.UploadAttachmentByOrganizerHandler`.

**It is recorded, not announced.** Every organizer correction of an entry's *data*
sends the applicant a letter, because a surname changed behind their back is a fact
they cannot see. A file is not that: it appears in their cabinet beside their own, and
the organizer is usually uploading something the applicant sent them minutes ago. So
it goes into the entry's journal — who attached what, and when — and no further.
"""

from __future__ import annotations

from typing import Any

from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.request import Request
from rest_framework.response import Response

from apps.applications.application.dto import SubmissionOperationResultDto
from apps.applications.application.dto.commands import (
    RemoveAttachmentByOrganizerCommand,
    UploadAttachmentByOrganizerCommand,
)
from apps.applications.application.exceptions import ApplicationError
from apps.applications.infrastructure.models.submission import SubmissionModel
from apps.applications.presentation.api.v1 import problems
from apps.applications.presentation.api.v1.files import file_url
from apps.applications.presentation.api.v1.submissions import composition
from apps.applications.presentation.api.v1.submissions.serializers import UploadAttachmentRequestSerializer

from .support import _StaffView
from .views import _now

__all__ = ["OrganizerSubmissionAttachmentDetailView", "OrganizerSubmissionAttachmentsView"]

#: Attachment kinds in the words the entry's journal uses. An unknown kind falls back
#: to the neutral "вложение" rather than leaking the wire enum into a history line.
_FILE_KINDS = {
    "MUSIC": "фонограмма",
    "VIDEO": "видео",
    "IMAGE": "фото",
    "DOCUMENT": "документ",
    "BENEFIT": "документ на льготу",
}


def _attachments(result: SubmissionOperationResultDto) -> dict[str, Any]:
    """The entry's files as the organizer's card lists them — the same shape it reads."""
    dto = result.submission
    return {
        "id": dto.id,
        "status": dto.status,
        "attachments": [
            {"id": a.id, "type": a.type, "fileReference": file_url(a.file_reference), "caption": a.caption, "sizeBytes": a.size_bytes}
            for a in dto.attachments
        ],
    }


def _record(*, submission_id: str, user_id: str, line: str) -> None:
    """Write one file movement into the entry's record of being corrected.

    The same journal the data corrections use, so the card's history reads as one
    story: who touched this entry, and what they did to it.
    """
    model = SubmissionModel.objects.get(id=submission_id, deleted_at__isnull=True)
    edits = list(model.organizer_edits or [])
    edits.append({"changes": [line], "comment": "", "created_by": user_id, "created_at": _now().isoformat()})
    model.organizer_edits = edits
    model.updated_at = _now()
    model.save(update_fields=["organizer_edits", "updated_at"])


def _envelope(request: Request, data: Any, *, status: int) -> Response:
    rid = problems.request_id(request)
    return Response({"data": data, "meta": {"requestId": rid}}, status=status, headers={"X-Request-ID": rid})


class OrganizerSubmissionAttachmentsView(_StaffView):
    """``POST staff/applications/{submission_id}/attachments`` — attach a file."""

    parser_classes = (MultiPartParser, FormParser)

    def post(self, request: Request, submission_id: str) -> Response:
        serializer = UploadAttachmentRequestSerializer(data=request.data)
        if not serializer.is_valid():
            return problems.validation_problem(serializer.errors, instance=request.path, request=request)
        upload = serializer.validated_data["file"]
        caption = serializer.validated_data.get("caption")
        command = UploadAttachmentByOrganizerCommand(
            submission_id=submission_id,
            reviewer_id=str(request.user.id),
            attachment_type=str(serializer.validated_data["attachmentType"]),
            filename=str(upload.name),
            content_type=str(getattr(upload, "content_type", "") or "application/octet-stream"),
            content=upload.read(),
            caption=str(caption) if caption else None,
        )
        try:
            result = composition.build_upload_attachment_by_organizer_handler().handle(command)
        except ApplicationError as exc:
            return problems.application_problem(exc, instance=request.path, request=request)
        kind = _FILE_KINDS.get(command.attachment_type, "вложение")
        _record(submission_id=submission_id, user_id=command.reviewer_id, line=f"Загружен файл ({kind}): {command.filename}")
        return _envelope(request, _attachments(result), status=201)


class OrganizerSubmissionAttachmentDetailView(_StaffView):
    """``DELETE staff/applications/{submission_id}/attachments/{attachment_id}``."""

    def delete(self, request: Request, submission_id: str, attachment_id: str) -> Response:
        command = RemoveAttachmentByOrganizerCommand(
            submission_id=submission_id,
            reviewer_id=str(request.user.id),
            attachment_id=attachment_id,
        )
        try:
            result = composition.build_remove_attachment_by_organizer_handler().handle(command)
        except ApplicationError as exc:
            return problems.application_problem(exc, instance=request.path, request=request)
        _record(submission_id=submission_id, user_id=command.reviewer_id, line="Удалён прикреплённый файл")
        return _envelope(request, _attachments(result), status=200)
