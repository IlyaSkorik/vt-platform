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
import uuid
from decimal import Decimal
from typing import Any

from drf_spectacular.utils import OpenApiParameter, OpenApiResponse, extend_schema
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.diplomas.domain.exceptions import PrintTemplateNotReadyError
from apps.diplomas.infrastructure.acl import actor_label as diploma_actor_label
from apps.identity.infrastructure.auth import CredentialAwareJWTAuthentication
from apps.identity.presentation.api.v1.problems import problem_response, request_id
from apps.organization.application.exceptions import ApplicationError
from apps.organization.application.handlers import (
    ChangeOrganizationStatusCommand,
    ConnectOrganizationCommand,
    FeeTierRow,
    SetCommissionRateCommand,
    SetPerformanceFeeScheduleCommand,
)
from apps.organization.composition import (
    build_change_organization_status_handler,
    build_connect_organization_handler,
    build_list_organizations_handler,
    build_set_commission_rate_handler,
    build_set_performance_fee_schedule_handler,
)
from apps.organization.presentation.api.v1.staff.serializers import ProblemDetailSerializer
from apps.organization.presentation.api.v1.staff.views import application_problem
from apps.platform.presentation.api.v1 import loadtest
from apps.platform.presentation.api.v1.read_models import build_dashboard
from apps.platform.presentation.api.v1.serializers import (
    ConnectOrganizationRequestSerializer,
    DashboardResponseSerializer,
    LoadTestCleanupResponseSerializer,
    LoadTestOverviewResponseSerializer,
    LoadTestRunResponseSerializer,
    OrganizationListResponseSerializer,
    OrganizationResponseSerializer,
    StartLoadTestRequestSerializer,
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


def _problem(request: Request, detail: str, *, title: str, status: int = 400) -> Response:
    """A plain RFC 9457 refusal for a request this edge itself turns down."""
    return problem_response(
        status=status,
        type_suffix="bad-request",
        title=title,
        detail=detail,
        instance=request.path,
        correlation_id=request_id(request),
    )


def _actor_id(request: Request) -> uuid.UUID | None:
    try:
        return uuid.UUID(str(request.user.id))
    except (ValueError, TypeError, AttributeError):
        return None


def _actor_label(request: Request) -> str:
    """Who to record on the run — the operator's own name, as the archive shows it."""
    return diploma_actor_label(_actor_id(request)) or "платформа"


def _fee_tiers_data(tiers: Any) -> list[dict[str, Any]]:
    """The fee schedule on the wire: camelCase keys, the amount as a decimal string."""
    return [
        {
            "minParticipants": tier.min_participants,
            "maxParticipants": tier.max_participants,
            "amount": str(tier.amount),
        }
        for tier in tiers
    ]


def _fee_tier_rows(payload: Any) -> tuple[FeeTierRow, ...]:
    """Turn the validated ``feeTiers`` payload into the use case's flat bands."""
    return tuple(
        FeeTierRow(
            min_participants=int(row["minParticipants"]),
            max_participants=None if row.get("maxParticipants") is None else int(row["maxParticipants"]),
            amount=Decimal(str(row["amount"])),
        )
        for row in payload
    )


def _organization_data(view: Any) -> dict[str, Any]:
    return {
        "id": view.id,
        "name": view.name,
        "slug": view.slug,
        "status": view.status,
        "billingModel": view.billing_model,
        "commissionPercent": str(view.commission_percent),
        "feeTiers": _fee_tiers_data(view.fee_tiers),
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
            fee_tiers=_fee_tier_rows(payload.get("feeTiers") or ()),
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

        # The commercial terms are mutually exclusive, so the model in the payload
        # decides which use case runs; `billingModel` is inferred from the bands when
        # the caller left it out, so a bare `commissionPercent` still means percent.
        model = payload.get("billingModel")
        view: Any = None
        try:
            if model == "PER_PERFORMANCE_FEE":
                view = build_set_performance_fee_schedule_handler().handle(
                    SetPerformanceFeeScheduleCommand(
                        organization_id=organization_id,
                        tiers=_fee_tier_rows(payload.get("feeTiers") or ()),
                    )
                )
            elif "commissionPercent" in payload:
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
                    "billingModel": row.billing_model,
                    "commissionPercent": str(row.commission_percent),
                    "feeTiers": _fee_tiers_data(row.fee_tiers),
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


class PlatformLoadTestView(_PlatformView):
    """GET/POST/DELETE /api/v1/platform/loadtest/diplomas — the generation load test.

    Operator-only, and deliberately so: a run writes hundreds of rows and megabytes
    of rendered PDFs into the live deployment. It stays off the real diploma
    numbering (see :mod:`apps.platform.presentation.api.v1.loadtest`) and every
    artefact it leaves behind is removable from this same endpoint.
    """

    @extend_schema(
        tags=[_TAG],
        operation_id="platform_loadtest_overview",
        summary="Load-test runs and what can be started",
        description=(
            "Every diploma-generation load test that still exists, with the state of its jobs, plus the "
            "diploma templates a new run can print over and the totals currently sitting in the database."
        ),
        request=None,
        responses={
            200: LoadTestOverviewResponseSerializer,
            403: OpenApiResponse(ProblemDetailSerializer, description="Not a platform administrator."),
        },
    )
    def get(self, request: Request) -> Response:
        data = {
            "runs": loadtest.list_runs(),
            "templates": loadtest.printable_templates(),
            "totals": loadtest.sandbox_counts(),
            "maxCount": loadtest.MAX_COUNT,
        }
        return _envelope(data, request)

    @extend_schema(
        tags=[_TAG],
        operation_id="platform_loadtest_start",
        summary="Start a diploma-generation load test",
        description=(
            "Seeds a synthetic competition with the requested number of entries and enqueues generation "
            "down the organizer's own print-package path — the same Celery task, worker and renderer a real "
            "run uses. Returns immediately; poll the overview for progress."
        ),
        request=StartLoadTestRequestSerializer,
        responses={
            202: LoadTestRunResponseSerializer,
            400: OpenApiResponse(ProblemDetailSerializer, description="Invalid parameters, or no printable template."),
            403: OpenApiResponse(ProblemDetailSerializer, description="Not a platform administrator."),
        },
    )
    def post(self, request: Request) -> Response:
        serializer = StartLoadTestRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        payload = serializer.validated_data

        template_id = payload.get("templateId")
        try:
            run = loadtest.start_run(
                count=int(payload["count"]),
                nominations=int(payload["nominations"]),
                template_id=str(template_id) if template_id else None,
                split=bool(payload["split"]),
                force=bool(payload["force"]),
                actor_id=_actor_id(request),
                actor_label=_actor_label(request),
            )
        except loadtest.LoadTestTemplateUnavailableError as exc:
            return _problem(request, str(exc), title="Нет шаблона для печати")
        except PrintTemplateNotReadyError as exc:
            return _problem(request, str(exc), title="Шаблон не готов к печати")
        return _envelope(run, request, status=202)

    @extend_schema(
        tags=[_TAG],
        operation_id="platform_loadtest_cleanup",
        summary="Delete load-test runs",
        description=(
            "Removes load-test competitions together with their entries, diplomas, jobs, archive records and "
            "the files they wrote to storage. Pass `competitionId` to remove one run; omit it to remove all."
        ),
        parameters=[
            OpenApiParameter(name="competitionId", type=str, required=False, description="Remove only this run."),
        ],
        request=None,
        responses={
            200: LoadTestCleanupResponseSerializer,
            403: OpenApiResponse(ProblemDetailSerializer, description="Not a platform administrator."),
        },
    )
    def delete(self, request: Request) -> Response:
        competition_id = (request.query_params.get("competitionId") or "").strip() or None
        return _envelope(loadtest.cleanup(competition_id=competition_id), request)
