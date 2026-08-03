"""The platform operator's console endpoints.

Everything here is gated by :class:`IsPlatformAdministrator`, which is granted only
by a management command. An organization's own OWNER is the top of that
organization and gets 403 from every route below.

The organization use cases live in the Organization context (it owns the
aggregate); this edge is what makes them platform-only, and what turns a
festival's name into the URL address it will be reached at.
"""

from __future__ import annotations

import re
from decimal import Decimal
from typing import Any

from drf_spectacular.utils import OpenApiParameter, OpenApiResponse, extend_schema
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.identity.infrastructure.auth import CredentialAwareJWTAuthentication
from apps.identity.presentation.api.v1.problems import request_id
from apps.organization.application.exceptions import ApplicationError
from apps.organization.application.handlers import (
    ChangeOrganizationStatusCommand,
    ConnectOrganizationCommand,
    SetCommissionRateCommand,
)
from apps.organization.composition import (
    build_change_organization_status_handler,
    build_connect_organization_handler,
    build_list_organizations_handler,
    build_set_commission_rate_handler,
)
from apps.organization.presentation.api.v1.staff.serializers import ProblemDetailSerializer
from apps.organization.presentation.api.v1.staff.views import application_problem
from apps.platform.presentation.api.v1.read_models import build_dashboard
from apps.platform.presentation.api.v1.serializers import (
    ConnectOrganizationRequestSerializer,
    DashboardResponseSerializer,
    OrganizationListResponseSerializer,
    OrganizationResponseSerializer,
    UpdateOrganizationRequestSerializer,
)
from apps.platform.presentation.permissions import IsPlatformAdministrator

_TAG = "Platform"

#: Cyrillic → Latin, so "Взлёт талантов" becomes an address a person can type and
#: read back over the phone. Deliberately simple and lossy: the operator can always
#: pass an explicit slug when the automatic one is not what they want.
_TRANSLITERATION = {
    "а": "a",
    "б": "b",
    "в": "v",
    "г": "g",
    "д": "d",
    "е": "e",
    "ё": "e",
    "ж": "zh",
    "з": "z",
    "и": "i",
    "й": "y",
    "к": "k",
    "л": "l",
    "м": "m",
    "н": "n",
    "о": "o",
    "п": "p",
    "р": "r",
    "с": "s",
    "т": "t",
    "у": "u",
    "ф": "f",
    "х": "h",
    "ц": "ts",
    "ч": "ch",
    "ш": "sh",
    "щ": "sch",
    "ъ": "",
    "ы": "y",
    "ь": "",
    "э": "e",
    "ю": "yu",
    "я": "ya",
}


def slugify_organization_name(name: str) -> str:
    """Derive a URL address from an organization's name."""
    lowered = name.strip().lower()
    latin = "".join(_TRANSLITERATION.get(char, char) for char in lowered)
    slug = re.sub(r"[^a-z0-9]+", "-", latin).strip("-")
    return slug[:100] or "organization"


def _envelope(data: Any, request: Request, *, status: int = 200) -> Response:
    correlation_id = request_id(request)
    return Response({"data": data, "meta": {"requestId": correlation_id}}, status=status, headers={"X-Request-ID": correlation_id})


def _organization_data(view: Any) -> dict[str, Any]:
    return {
        "id": view.id,
        "name": view.name,
        "slug": view.slug,
        "status": view.status,
        "commissionPercent": str(view.commission_percent),
        "createdAt": view.created_at,
    }


class _PlatformView(APIView):
    authentication_classes = (CredentialAwareJWTAuthentication,)
    permission_classes = (IsAuthenticated, IsPlatformAdministrator)


class PlatformOrganizationsView(_PlatformView):
    """GET/POST /api/v1/platform/organizations — the connected organizations."""

    @extend_schema(
        tags=[_TAG],
        operation_id="platform_list_organizations",
        summary="List connected organizations",
        request=None,
        responses={
            200: OrganizationListResponseSerializer,
            403: OpenApiResponse(ProblemDetailSerializer, description="Not a platform administrator."),
        },
    )
    def get(self, request: Request) -> Response:
        organizations = build_list_organizations_handler().handle()
        return _envelope([_organization_data(org) for org in organizations], request)

    @extend_schema(
        tags=[_TAG],
        operation_id="platform_connect_organization",
        summary="Connect an organization",
        description=(
            "Create the organization and email its owner an invitation making them its first OWNER. `slug` is derived from the name when omitted."
        ),
        request=ConnectOrganizationRequestSerializer,
        responses={
            201: OrganizationResponseSerializer,
            400: OpenApiResponse(ProblemDetailSerializer, description="Malformed request."),
            403: OpenApiResponse(ProblemDetailSerializer, description="Not a platform administrator."),
            409: OpenApiResponse(ProblemDetailSerializer, description="That address is already taken."),
        },
    )
    def post(self, request: Request) -> Response:
        serializer = ConnectOrganizationRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        payload = serializer.validated_data

        name = str(payload["name"])
        slug = str(payload.get("slug") or "").strip() or slugify_organization_name(name)
        command = ConnectOrganizationCommand(
            name=name,
            slug=slug,
            owner_email=str(payload["ownerEmail"]),
            commission_percent=Decimal(str(payload.get("commissionPercent", Decimal("0")))),
            connected_by=str(request.user.id),
        )
        try:
            result = build_connect_organization_handler().handle(command)
        except ApplicationError as exc:
            return application_problem(exc, instance=request.path, request=request)
        return _envelope(_organization_data(result.organization), request, status=201)


class PlatformOrganizationDetailView(_PlatformView):
    """PATCH /api/v1/platform/organizations/{id} — its terms, or its suspension."""

    @extend_schema(
        tags=[_TAG],
        operation_id="platform_update_organization",
        summary="Update an organization's terms or status",
        request=UpdateOrganizationRequestSerializer,
        responses={
            200: OrganizationResponseSerializer,
            400: OpenApiResponse(ProblemDetailSerializer, description="Malformed request."),
            403: OpenApiResponse(ProblemDetailSerializer, description="Not a platform administrator."),
            404: OpenApiResponse(ProblemDetailSerializer, description="No such organization."),
            409: OpenApiResponse(ProblemDetailSerializer, description="Already in that state."),
        },
    )
    def patch(self, request: Request, organization_id: str) -> Response:
        serializer = UpdateOrganizationRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        payload = serializer.validated_data

        view: Any = None
        try:
            if "commissionPercent" in payload:
                view = build_set_commission_rate_handler().handle(
                    SetCommissionRateCommand(
                        organization_id=organization_id,
                        commission_percent=Decimal(str(payload["commissionPercent"])),
                    )
                )
            if "status" in payload:
                view = build_change_organization_status_handler().handle(
                    ChangeOrganizationStatusCommand(organization_id=organization_id, status=str(payload["status"]))
                )
        except ApplicationError as exc:
            return application_problem(exc, instance=request.path, request=request)
        return _envelope(_organization_data(view), request)


class PlatformDashboardView(_PlatformView):
    """GET /api/v1/platform/dashboard — applications and fees across every organization."""

    @extend_schema(
        tags=[_TAG],
        operation_id="platform_dashboard",
        summary="Platform dashboard",
        description=(
            "Application counts per status across all connected organizations, with the participation "
            "fees behind them and the platform's commission on those fees. Filterable by organization "
            "and by competition."
        ),
        parameters=[
            OpenApiParameter(name="organizationId", type=str, required=False, description="Narrow to one organization."),
            OpenApiParameter(name="competitionId", type=str, required=False, description="Narrow to one competition."),
        ],
        request=None,
        responses={
            200: DashboardResponseSerializer,
            403: OpenApiResponse(ProblemDetailSerializer, description="Not a platform administrator."),
        },
    )
    def get(self, request: Request) -> Response:
        dashboard = build_dashboard(
            organization_id=(request.query_params.get("organizationId") or "").strip() or None,
            competition_id=(request.query_params.get("competitionId") or "").strip() or None,
        )
        data = {
            "statusCounts": dashboard.status_counts,
            "applications": dashboard.applications,
            "expectedFees": str(dashboard.expected_fees),
            "settledFees": str(dashboard.settled_fees),
            "expectedCommission": str(dashboard.expected_commission),
            "settledCommission": str(dashboard.settled_commission),
            "organizations": [
                {
                    "organizationId": row.organization_id,
                    "name": row.name,
                    "status": row.status,
                    "commissionPercent": str(row.commission_percent),
                    "competitions": row.competitions,
                    "applications": row.applications,
                    "statusCounts": row.status_counts,
                    "expectedFees": str(row.expected_fees),
                    "settledFees": str(row.settled_fees),
                    "expectedCommission": str(row.expected_commission),
                    "settledCommission": str(row.settled_commission),
                }
                for row in dashboard.organizations
            ],
            "competitions": [
                {
                    "id": option.id,
                    "title": option.title,
                    "organizationId": option.organization_id,
                    "organizationName": option.organization_name,
                }
                for option in dashboard.competitions
            ],
        }
        return _envelope(data, request)
