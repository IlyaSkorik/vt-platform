"""Public Festival Catalog REST edge (participant-facing).

``GET /api/v1/public/festivals`` — the entry point to the Participant Portal. It
is the *only* public, unauthenticated competition endpoint: everything under the
organizer :class:`CompetitionViewSet` is staff-only. It reads a dedicated
projection (:class:`PublicCatalogReadService`) — never the Competition aggregate
or the organizer API — and returns every publicly-visible competition (published
through completed; drafts and archived competitions are excluded) newest first,
in the platform's ``{data, meta}`` envelope.
"""

from __future__ import annotations

from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.competitions.composition import build_public_catalog_read_service
from apps.competitions.presentation.api.v1.problems import request_id
from apps.competitions.presentation.api.v1.public_serializers import (
    PublicFestivalListEnvelopeSerializer,
    PublicFestivalSerializer,
)

_TAG = "Public Catalog"


class PublicFestivalCatalogView(APIView):
    """List every publicly-visible competition for the participant catalog."""

    # Public by design: no authentication required and no staff gate. An
    # authenticated participant may carry a bearer token, but it is irrelevant
    # here — the catalog is the same for everyone.
    authentication_classes = ()
    permission_classes = (AllowAny,)

    @extend_schema(
        tags=[_TAG],
        operation_id="listPublicFestivals",
        responses={status.HTTP_200_OK: PublicFestivalListEnvelopeSerializer},
    )
    def get(self, request: Request) -> Response:
        festivals = build_public_catalog_read_service().list_festivals()
        correlation_id = request_id(request)
        data = PublicFestivalSerializer(festivals, many=True).data
        return Response(
            {"data": data, "meta": {"requestId": correlation_id}},
            status=status.HTTP_200_OK,
            headers={"X-Request-ID": correlation_id},
        )
