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

from apps.competitions.composition import (
    build_public_catalog_read_service,
    build_registration_read_service,
)
from apps.competitions.presentation.api.v1.problems import problem_response, request_id
from apps.competitions.presentation.api.v1.public_serializers import (
    PublicFestivalDetailEnvelopeSerializer,
    PublicFestivalDetailSerializer,
    PublicFestivalListEnvelopeSerializer,
    PublicFestivalSerializer,
    RegistrationEnvelopeSerializer,
    RegistrationSerializer,
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


class PublicFestivalDetailView(APIView):
    """The public landing view of a single competition.

    Powers the participant-facing Competition Landing Page: the hero facts, the
    organizer's Landing Builder blocks (enabled, in order) and the reused
    Competition Contacts. Unpublished, draft or archived competitions are
    indistinguishable from a missing id — both return a 404 problem, never
    leaking their existence.
    """

    authentication_classes = ()
    permission_classes = (AllowAny,)

    @extend_schema(
        tags=[_TAG],
        operation_id="getPublicFestival",
        responses={status.HTTP_200_OK: PublicFestivalDetailEnvelopeSerializer},
    )
    def get(self, request: Request, festival_id: str) -> Response:
        correlation_id = request_id(request)
        festival = build_public_catalog_read_service().get_festival(festival_id)
        if festival is None:
            return problem_response(
                status=status.HTTP_404_NOT_FOUND,
                type_suffix="not-found",
                title="Resource not found",
                detail="No publicly available festival matches this identifier.",
                instance=request.get_full_path(),
                correlation_id=correlation_id,
                code="festival_not_found",
            )
        data = PublicFestivalDetailSerializer(festival).data
        return Response(
            {"data": data, "meta": {"requestId": correlation_id}},
            status=status.HTTP_200_OK,
            headers={"X-Request-ID": correlation_id},
        )


class PublicRegistrationView(APIView):
    """The single Registration projection for the wizard (participant-facing).

    ``GET /api/v1/public/competitions/{competition_id}/registration`` returns
    everything the Registration Wizard needs to render — competition summary,
    the full configuration taxonomy, admission rules, additional services,
    required consents, per-format upload requirements, deadlines and registration
    availability — assembled from the Competition aggregate in one read. Draft or
    archived competitions return a 404 problem, never leaking their existence.
    """

    authentication_classes = ()
    permission_classes = (AllowAny,)

    @extend_schema(
        tags=[_TAG],
        operation_id="getRegistration",
        responses={status.HTTP_200_OK: RegistrationEnvelopeSerializer},
    )
    def get(self, request: Request, competition_id: str) -> Response:
        correlation_id = request_id(request)
        registration = build_registration_read_service().get(competition_id)
        if registration is None:
            return problem_response(
                status=status.HTTP_404_NOT_FOUND,
                type_suffix="not-found",
                title="Resource not found",
                detail="No publicly available competition matches this identifier.",
                instance=request.get_full_path(),
                correlation_id=correlation_id,
                code="competition_not_found",
            )
        data = RegistrationSerializer(registration).data
        return Response(
            {"data": data, "meta": {"requestId": correlation_id}},
            status=status.HTTP_200_OK,
            headers={"X-Request-ID": correlation_id},
        )
