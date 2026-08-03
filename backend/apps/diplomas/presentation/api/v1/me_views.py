"""The participant's documents REST edge ("Мои документы").

``GET /api/v1/me/documents`` — every document the platform has issued to the
authenticated applicant: diplomas from the register and thank-you letters from the
issued-document table, as one list ready to render.

Authenticated but **not** staff-gated: this is the participant's own cabinet, and
it is scoped to the caller's own applicant id — never to an id from the request, so
one participant cannot read another's documents.

It reads the dedicated :class:`ParticipantDocumentsReadService` projection and
performs no publication of its own: a document appears here exactly when its own
rules make it the participant's to see.
"""

from __future__ import annotations

import uuid

from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.diplomas.composition import build_participant_documents_read_service
from apps.diplomas.presentation.api.v1 import problems
from apps.diplomas.presentation.api.v1.me_serializers import (
    ParticipantDocumentsEnvelopeSerializer,
    ParticipantDocumentSerializer,
)
from apps.identity.infrastructure.auth import CredentialAwareJWTAuthentication

_TAG = "My Documents"


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
