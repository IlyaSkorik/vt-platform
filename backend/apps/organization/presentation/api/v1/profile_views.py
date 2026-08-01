"""REST view for the organization profile."""

from __future__ import annotations

from drf_spectacular.utils import OpenApiResponse, extend_schema, inline_serializer
from rest_framework import serializers
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.identity.infrastructure.auth import CredentialAwareJWTAuthentication
from apps.identity.presentation.api.v1.problems import request_id, validation_problem
from apps.organization.application.dto.commands import UpdateOrganizationProfileCommand
from apps.organization.application.dto.queries import GetOrganizationProfileQuery
from apps.organization.application.exceptions import ApplicationError
from apps.organization.application.handlers import OrganizationProfileView as OrganizationProfileReadModel
from apps.organization.composition import (
    build_get_organization_profile_handler,
    build_update_organization_profile_handler,
)
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


def _profile_field() -> serializers.CharField:
    """A single optional profile field: absent leaves it, blank/null clears it."""
    return serializers.CharField(required=False, allow_blank=True, allow_null=True)


class OrganizationProfileUpdateSerializer(serializers.Serializer[dict[str, object]]):
    """Request body for editing the profile — every contact/legal field, all optional.

    A full-replacement edit: an omitted contact field is treated as cleared. Wire
    keys are camelCase (API-000 §7); the view maps them onto the snake_case
    command. ``name`` is the display name — omitting it leaves the name unchanged;
    a blank name is rejected (the domain refuses an empty organization name).
    """

    name = serializers.CharField(required=False, allow_blank=False, max_length=200)
    phone = _profile_field()
    email = _profile_field()
    website = _profile_field()
    address = _profile_field()
    logo = _profile_field()
    vk = _profile_field()
    instagram = _profile_field()
    telegram = _profile_field()
    legalInformation = _profile_field()  # noqa: N815  # API camelCase wire key (API-000 §7)


class OrganizationProfileView(APIView):
    """GET /api/v1/organization/profile — singleton organization profile (staff-only)."""

    authentication_classes = (CredentialAwareJWTAuthentication,)
    permission_classes = (IsAuthenticated, IsOrganizationStaff)

    @extend_schema(
        tags=[_TAG],
        operation_id="getOrganizationProfile",
        summary="Get organization profile",
        description="Return the caller's own organization profile. Contact fields are null until persisted.",
        responses={
            200: OrganizationProfileResponseSerializer,
            403: OpenApiResponse(ProblemDetailSerializer, description="Not organization staff."),
            404: OpenApiResponse(ProblemDetailSerializer, description="Organization not seeded."),
        },
    )
    def get(self, request: Request) -> Response:
        try:
            profile = build_get_organization_profile_handler().handle(GetOrganizationProfileQuery(requested_by=str(request.user.id)))
        except ApplicationError as exc:
            return application_problem(exc, instance=request.path, request=request)
        return Response(_envelope(profile, request), status=200)

    @extend_schema(
        tags=[_TAG],
        operation_id="updateOrganizationProfile",
        summary="Update organization profile",
        description="Replace the organization's public contact & legal profile. Full-replacement: an omitted field is cleared.",
        request=OrganizationProfileUpdateSerializer,
        responses={
            200: OrganizationProfileResponseSerializer,
            400: OpenApiResponse(ProblemDetailSerializer, description="Malformed request."),
            403: OpenApiResponse(ProblemDetailSerializer, description="Not organization staff."),
            404: OpenApiResponse(ProblemDetailSerializer, description="Organization not seeded."),
        },
    )
    def patch(self, request: Request) -> Response:
        serializer = OrganizationProfileUpdateSerializer(data=request.data)
        if not serializer.is_valid():
            return validation_problem(serializer.errors, instance=request.path, request=request)

        data = serializer.validated_data
        command = UpdateOrganizationProfileCommand(
            updated_by=str(request.user.id),
            name=data.get("name"),
            phone=data.get("phone"),
            email=data.get("email"),
            website=data.get("website"),
            address=data.get("address"),
            logo=data.get("logo"),
            vk=data.get("vk"),
            instagram=data.get("instagram"),
            telegram=data.get("telegram"),
            legal_information=data.get("legalInformation"),
        )
        try:
            profile = build_update_organization_profile_handler().handle(command)
        except ApplicationError as exc:
            return application_problem(exc, instance=request.path, request=request)
        return Response(_envelope(profile, request), status=200)


def _envelope(profile: OrganizationProfileReadModel, request: Request) -> dict[str, object]:
    """Wrap an ``OrganizationProfileView`` read model in the standard ``{data, meta}`` body."""
    return {
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
