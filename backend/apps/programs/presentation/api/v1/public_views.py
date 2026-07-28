"""Public program REST edge (anyone-facing).

``GET /api/v1/public/programs/{slug}`` - the single unauthenticated endpoint of this
context, and the backend of the screen an organizer hands to a sound engineer, a host,
the jury or a display beside the stage.

Public by design: whoever holds the link reads the program, with no account. The slug
*is* the credential - minted per edition from a confusable-free alphabet, never
derived from the program's name - so a link cannot be found by guessing, and a revoked
one is indistinguishable from one that never existed.
"""

from __future__ import annotations

from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.programs.application.dto import PublicProgramView
from apps.programs.composition import build_program_service
from apps.programs.presentation.api.v1.problems import problem_response, request_id
from apps.programs.presentation.api.v1.public_serializers import (
    PublicProgramEnvelopeSerializer,
)

_TAG = "Public Program"

__all__ = ["PublicProgramDetailView"]


def _public_json(view: PublicProgramView) -> dict[str, object]:
    return {
        "name": view.name,
        "slug": view.slug,
        "competitionTitle": view.competition_title,
        "nomination": view.nomination,
        "startsAt": view.starts_at,
        "totalSeconds": view.total_seconds,
        "items": [
            {
                "position": item.position,
                "kind": item.kind,
                "title": item.title,
                "performer": item.performer,
                "teachers": list(item.teachers),
                "organization": item.organization,
                "durationSeconds": item.duration_seconds,
                "startsAt": item.starts_at,
                "note": item.note,
            }
            for item in view.items
        ],
    }


class PublicProgramDetailView(APIView):
    """Read one published program by its slug.

    An unknown, malformed or revoked slug is a single, indistinguishable ``404``, so
    nothing about which of the three it was leaks.
    """

    # Public by design: no authentication and no staff gate. A visitor may happen to
    # carry a bearer token; it is irrelevant here - the link is the whole of the input.
    authentication_classes = ()
    permission_classes = (AllowAny,)

    @extend_schema(
        tags=[_TAG],
        operation_id="publicProgramRetrieve",
        responses={status.HTTP_200_OK: PublicProgramEnvelopeSerializer},
    )
    def get(self, request: Request, slug: str) -> Response:
        correlation_id = request_id(request)
        program = build_program_service().public_program(slug)
        if program is None:
            return problem_response(
                status=status.HTTP_404_NOT_FOUND,
                type_suffix="not-found",
                title="Resource not found",
                detail="No published program answers to this link.",
                instance=request.get_full_path(),
                correlation_id=correlation_id,
            )
        return Response(
            {"data": _public_json(program), "meta": {"requestId": correlation_id}},
            status=status.HTTP_200_OK,
            headers={"X-Request-ID": correlation_id},
        )
