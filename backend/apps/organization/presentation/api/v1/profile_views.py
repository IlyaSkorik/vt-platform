"""REST view for the organization profile."""

from __future__ import annotations

from drf_spectacular.utils import OpenApiResponse, extend_schema, inline_serializer
from rest_framework import serializers
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.authentication import JWTStatelessUserAuthentication

from apps.identity.presentation.api.v1.problems import request_id
from apps.organization.application.exceptions import ApplicationError
from apps.organization.composition import build_get_organization_profile_handler
from apps.organization.presentation.api.v1.staff.serializers import ProblemDetailSerializer
from apps.organization.presentation.api.v1.staff.views import application_problem
from apps.organization.presentation.permissions import IsOrganizationStaff

_TAG = "Organization"


class OrganizationProfileSerializer(serializers.Serializer[dict[str, object]]):
    id = serializers.CharField()
    name = serializers.CharField()
    slug = serializers.CharField()
    phone = serializers.CharField(allow_null=True)
    email = serializers.CharField(allow_null=True)
    website = serializers.CharField(allow_null=True)
    address = serializers.CharField(allow_null=True)
    logo = serializers.CharField(allow_null=True)
    vk = serializers.CharField(allow_null=True)
    instagram = serializers.CharField(allow_null=True)
    telegram = serializers.CharField(allow_null=True)
    legalInformation = serializers.CharField(source="legal_information", allow_null=True)  # noqa: N815  # API camelCase wire key (API-000 §7)


OrganizationProfileResponseSerializer = inline_serializer(
    name="OrganizationProfileResponse",
    fields={
        "data": OrganizationProfileSerializer(),
        "meta": inline_serializer(name="OrganizationProfileMeta", fields={"requestId": serializers.CharField()}),
    },
)


class OrganizationProfileView(APIView):
    """GET /api/v1/organization/profile — singleton organization profile (staff-only)."""

    authentication_classes = (JWTStatelessUserAuthentication,)
    permission_classes = (IsAuthenticated, IsOrganizationStaff)

    @extend_schema(
        tags=[_TAG],
        operation_id="getOrganizationProfile",
        summary="Get organization profile",
        description="Return the singleton organization profile. Contact fields are null until persisted.",
        responses={
            200: OrganizationProfileResponseSerializer,
            403: OpenApiResponse(ProblemDetailSerializer, description="Not organization staff."),
            404: OpenApiResponse(ProblemDetailSerializer, description="Organization not seeded."),
        },
    )
    def get(self, request: Request) -> Response:
        try:
            profile = build_get_organization_profile_handler().handle()
        except ApplicationError as exc:
            return application_problem(exc, instance=request.path, request=request)

        body = {
            "data": {
                "id": profile.id,
                "name": profile.name,
                "slug": profile.slug,
                "phone": profile.phone,
                "email": profile.email,
                "website": profile.website,
                "address": profile.address,
                "logo": profile.logo,
                "vk": profile.vk,
                "instagram": profile.instagram,
                "telegram": profile.telegram,
                "legalInformation": profile.legal_information,
            },
            "meta": {"requestId": request_id(request)},
        }
        return Response(body, status=200)
