"""The participant's documents REST edge ("Мои документы").

``GET /api/v1/me/documents`` — every document the platform has issued to the
authenticated applicant: diplomas from the register and thank-you letters from the
issued-document table, as one list ready to render.

``GET /api/v1/me/documents/archive`` — one entry's individual diplomas as a single
ZIP. An ensemble of twelve produces twelve of them, and clicking twelve downloads is
not how anybody hands them out.

Authenticated but **not** staff-gated: this is the participant's own cabinet, and
it is scoped to the caller's own applicant id — never to an id from the request, so
one participant cannot read another's documents.

It reads the dedicated :class:`ParticipantDocumentsReadService` projection and
performs no publication of its own: a document appears here exactly when its own
rules make it the participant's to see. The archive is assembled from that same
projection on each request and stored nowhere, so it can never disagree with the list
it was downloaded from — a corrected protocol re-renders the diplomas, and the next
download simply carries the corrected ones.
"""

from __future__ import annotations

import uuid

from django.http import HttpResponseBase
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.diplomas.application.read_models.participant_documents import (
    archive_entry_name,
    archive_filename,
    bundled_documents,
)
from apps.diplomas.composition import build_participant_documents_read_service
from apps.diplomas.domain.document_types import DocumentType
from apps.diplomas.infrastructure.pdf.workspace import storage_key_of
from apps.diplomas.presentation.api.v1 import problems
from apps.diplomas.presentation.api.v1.me_serializers import (
    ParticipantDocumentsEnvelopeSerializer,
    ParticipantDocumentSerializer,
)
from apps.identity.infrastructure.auth import CredentialAwareJWTAuthentication
from config.archive import ArchiveMember, zip_response

_TAG = "My Documents"

#: What the individual-diploma archive is called before the festival's name is added.
_ARCHIVE_LABEL = "Дипломы участников"


def _applicant_uuid(raw_user_id: object) -> uuid.UUID:
    """The caller's own id as a UUID.

    ``request.user`` is typed by django-stubs as a generic Django user, whose ``id``
    is an ``int``; this platform's accounts are keyed by UUID, so the value has to be
    re-read rather than passed straight through. A subject that is not a UUID at all
    is folded into a deterministic one so the lookup stays total instead of raising —
    it will simply match no documents.
    """
    text = str(raw_user_id).strip()
    try:
        return uuid.UUID(text)
    except ValueError:
        return uuid.uuid5(uuid.NAMESPACE_URL, f"participant-owner:{text}")


class MyDocumentsView(APIView):
    """List the authenticated participant's issued documents."""

    authentication_classes = (CredentialAwareJWTAuthentication,)
    permission_classes = (IsAuthenticated,)

    @extend_schema(
        tags=[_TAG],
        operation_id="listMyDocuments",
        responses={status.HTTP_200_OK: ParticipantDocumentsEnvelopeSerializer},
    )
    def get(self, request: Request) -> Response:
        # Scoped to the caller. The applicant id never comes from the request.
        found = build_participant_documents_read_service().list_for_applicant(_applicant_uuid(request.user.pk))
        return problems.envelope(request, ParticipantDocumentSerializer(found, many=True).data)


class MyIndividualDiplomasArchiveView(APIView):
    """One entry's individual diplomas as a single ZIP download.

    A ``GET`` because it is a download, and assembled per request because nothing is
    worth storing: the members are already-rendered PDFs, and a stored bundle would
    have to be invalidated every time a corrected protocol re-renders one of them.

    The entry is named in the query, but it is not a permission: the bundle is
    filtered out of *the caller's own* documents, so somebody else's submission id
    matches nothing and returns a 404 rather than their diplomas.
    """

    authentication_classes = (CredentialAwareJWTAuthentication,)
    permission_classes = (IsAuthenticated,)

    @extend_schema(
        tags=[_TAG],
        operation_id="downloadMyIndividualDiplomas",
        summary="Download one entry's individual diplomas as one ZIP",
        parameters=[
            OpenApiParameter(
                name="submissionId",
                type=OpenApiTypes.UUID,
                location=OpenApiParameter.QUERY,
                required=True,
                description="The entry whose individual diplomas to bundle.",
            )
        ],
        responses={(status.HTTP_200_OK, "application/zip"): OpenApiTypes.BINARY},
    )
    # ``HttpResponseBase``, not ``HttpResponse``: a ZIP download is a
    # ``StreamingHttpResponse``, which is not an ``HttpResponse`` at all. The base class
    # is the only type covering a streamed body and a DRF ``Response`` both.
    def get(self, request: Request) -> HttpResponseBase | Response:
        raw = (request.query_params.get("submissionId") or "").strip()
        try:
            submission_id = uuid.UUID(raw)
        except ValueError:
            return problems.validation_problem({"submissionId": ["Ожидается UUID заявки."]}, instance=request.path, request=request)

        mine = build_participant_documents_read_service().list_for_applicant(_applicant_uuid(request.user.pk))
        bundle = bundled_documents(mine, submission_id=submission_id, document_type=DocumentType.INDIVIDUAL_DIPLOMA)
        if not bundle:
            # Nothing of the caller's under that id — an unknown entry, an entry with no
            # individual diplomas, and somebody else's entry are one answer on purpose.
            return problems.problem_response(
                status=status.HTTP_404_NOT_FOUND,
                type_suffix="not-found",
                title="Resource not found",
                detail="Индивидуальные дипломы по этой заявке не найдены.",
                instance=request.path,
                correlation_id=problems.request_id(request),
            )
        members = [
            # ``file_url`` is a stored *reference* (a URL); the archive copies objects,
            # so it needs the key that reference was minted from.
            ArchiveMember(arcname=archive_entry_name(document, position=position), reference=storage_key_of(document.file_url))
            for position, document in enumerate(bundle, start=1)
        ]
        return zip_response(members, filename=archive_filename(bundle, label=_ARCHIVE_LABEL))
