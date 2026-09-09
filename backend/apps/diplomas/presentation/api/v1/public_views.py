"""Public diploma verification REST edge (anyone-facing).

``GET /api/v1/public/diplomas/verify/{verification_token}`` — the single
unauthenticated diploma endpoint, and the backend of the page a printed
diploma's QR code points at (``/verify/{token}`` on the web client). Everything
else under the Diplomas tag is organizer-only.

Public by design: whoever holds the paper can check it, with no account. The
token itself is the credential — 32 bytes of entropy minted per diploma, so a
diploma cannot be found by guessing, and holding a number is not enough to look
one up.

It reads the dedicated :class:`DiplomaVerificationReadService` projection over the
diploma's own frozen snapshot — never the ``Diploma`` aggregate, never the
organizer API, and never another bounded context.
"""

from __future__ import annotations

from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.diplomas.composition import build_diploma_verification_read_service
from apps.diplomas.presentation.api.v1.problems import problem_response, request_id
from apps.diplomas.presentation.api.v1.public_serializers import (
    DiplomaVerificationEnvelopeSerializer,
    DiplomaVerificationSerializer,
)

_TAG = "Diploma Verification"


class PublicDiplomaVerificationView(APIView):
    """Verify one diploma by its verification token.

    An unknown, malformed or revoked token is a single, indistinguishable ``404``
    problem — the page renders "Диплом не найден" and nothing about which of the
    three it was leaks.
    """

    # Public by design: no authentication and no staff gate. A visitor may happen
    # to carry a bearer token; it is irrelevant here — verification is the same
    # for everyone, which is the point of an authenticity check.
    authentication_classes = ()
    permission_classes = (AllowAny,)

    @extend_schema(
        tags=[_TAG],
        operation_id="verifyDiploma",
        responses={status.HTTP_200_OK: DiplomaVerificationEnvelopeSerializer},
    )
    def get(self, request: Request, verification_token: str) -> Response:
        correlation_id = request_id(request)
        diploma = build_diploma_verification_read_service().get_by_token(verification_token)
        if diploma is None:
            return problem_response(
                status=status.HTTP_404_NOT_FOUND,
                type_suffix="not-found",
                title="Resource not found",
                detail="По этому коду документ не найден.",
                instance=request.get_full_path(),
                correlation_id=correlation_id,
            )
        return Response(
            {"data": DiplomaVerificationSerializer(diploma).data, "meta": {"requestId": correlation_id}},
            status=status.HTTP_200_OK,
            headers={"X-Request-ID": correlation_id},
        )
