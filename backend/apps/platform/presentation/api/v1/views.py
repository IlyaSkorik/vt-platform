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
from datetime import date
from decimal import Decimal
from typing import Any, Final

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
    SetOrganizationModulesCommand,
    SetPerformanceFeeScheduleCommand,
)
from apps.organization.composition import (
    build_change_organization_status_handler,
    build_connect_organization_handler,
    build_list_organization_modules_handler,
    build_list_organizations_handler,
    build_set_commission_rate_handler,
    build_set_organization_modules_handler,
    build_set_performance_fee_schedule_handler,
)
from apps.organization.presentation.api.v1.staff.serializers import ProblemDetailSerializer
from apps.organization.presentation.api.v1.staff.views import application_problem
from apps.platform.presentation.api.v1 import loadtest, purge
from apps.platform.presentation.api.v1.audience import build_audience
from apps.platform.presentation.api.v1.read_models import build_dashboard
from apps.platform.presentation.api.v1.serializers import (
    AudienceResponseSerializer,
    ConnectOrganizationRequestSerializer,
    DashboardResponseSerializer,
    LoadTestCleanupResponseSerializer,
    LoadTestOverviewResponseSerializer,
    LoadTestRunResponseSerializer,
    OrganizationListResponseSerializer,
    OrganizationModulesResponseSerializer,
    OrganizationResponseSerializer,
    PurgePlanResponseSerializer,
    PurgeSearchResponseSerializer,
    SetOrganizationModulesRequestSerializer,
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


#: Console refusals carry a domain message that may be internal English prose; the
#: title beside it is already the Russian sentence an administrator should read, so
#: it stands in whenever the message is not addressed to a person.
_CYRILLIC: Final = re.compile("[А-Яа-яЁё]")


def _problem(request: Request, detail: str, *, title: str, status: int = 400) -> Response:
    """A plain RFC 9457 refusal for a request this edge itself turns down."""
    return problem_response(
        status=status,
        type_suffix="bad-request",
        title=title,
        detail=detail if detail and _CYRILLIC.search(detail) else title,
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


def _fee_breakdown_data(rows: Any) -> list[dict[str, Any]]:
    """The per-band tally on the wire — the rows an act is written from.

    Every band of the schedule appears, including the ones nothing fell into: a
    price list with rows silently missing is one the organizer cannot check against
    their own copy.
    """
    return [
        {
            "minParticipants": row.min_participants,
            "maxParticipants": row.max_participants,
            "rangeLabel": row.range_label,
            "unitAmount": str(row.unit_amount),
            "performances": row.performances,
            "amount": str(row.amount),
        }
        for row in rows
    ]


def _optional_date(request: Request, name: str) -> date | None:
    """A ``YYYY-MM-DD`` query parameter, or ``None`` when it was not sent.

    An unparseable date is treated as absent rather than refused, exactly as the
    expense ledger treats its own: these are the two ends of a period filter on a
    screen, and a half-typed date in the address bar should narrow nothing rather
    than blank the dashboard with an error.
    """
    raw = (request.query_params.get(name) or "").strip()
    if not raw:
        return None
    try:
        return date.fromisoformat(raw)
    except ValueError:
        return None


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
            # Absent means the full-access preset; an explicit list (even an empty
            # one) is the operator saying exactly what was sold.
            modules=None if "modules" not in payload else tuple(payload["modules"]),
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


def _modules_data(view: Any) -> dict[str, Any]:
    return {
        "organizationId": view.organization_id,
        "modules": [
            {
                "module": row.module,
                "enabled": row.enabled,
                "enabledAt": row.enabled_at,
                "disabledAt": row.disabled_at,
            }
            for row in view.modules
        ],
    }


class PlatformOrganizationModulesView(_PlatformView):
    """GET/PUT /api/v1/platform/organizations/{id}/modules — what the organization was sold.

    Separate from the terms endpoint next door on purpose. Which modules an
    organization holds is not one of its commercial *terms* — it is the shape of the
    product, it is edited on its own screen, and a PATCH that merged the two would
    make "set the modules" and "change the commission" share a failure mode.

    PUT rather than PATCH: the body is the whole switchboard, and anything absent is
    off. See :class:`SetOrganizationModulesRequestSerializer`.
    """

    @extend_schema(
        tags=[_TAG],
        operation_id="platform_list_organization_modules",
        summary="Read an organization's modules",
        description="Every module the platform knows, with whether this organization holds it and since when.",
        request=None,
        responses={
            200: OrganizationModulesResponseSerializer,
            403: OpenApiResponse(ProblemDetailSerializer, description="Not a platform administrator."),
            404: OpenApiResponse(ProblemDetailSerializer, description="No such organization."),
        },
    )
    def get(self, request: Request, organization_id: str) -> Response:
        try:
            view = build_list_organization_modules_handler().handle(organization_id)
        except ApplicationError as exc:
            return application_problem(exc, instance=request.path, request=request)
        return _envelope(_modules_data(view), request)

    @extend_schema(
        tags=[_TAG],
        operation_id="platform_set_organization_modules",
        summary="Set an organization's modules",
        description=(
            "Replace the organization's module set: everything listed is switched on, everything else off. "
            "Idempotent — re-sending an unchanged set keeps the date each module was first connected."
        ),
        request=SetOrganizationModulesRequestSerializer,
        responses={
            200: OrganizationModulesResponseSerializer,
            400: OpenApiResponse(ProblemDetailSerializer, description="Malformed request."),
            403: OpenApiResponse(ProblemDetailSerializer, description="Not a platform administrator."),
            404: OpenApiResponse(ProblemDetailSerializer, description="No such organization."),
        },
    )
    def put(self, request: Request, organization_id: str) -> Response:
        serializer = SetOrganizationModulesRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        command = SetOrganizationModulesCommand(
            organization_id=organization_id,
            modules=tuple(serializer.validated_data["modules"]),
            changed_by=str(request.user.id),
        )
        try:
            view = build_set_organization_modules_handler().handle(command)
        except ApplicationError as exc:
            return application_problem(exc, instance=request.path, request=request)
        return _envelope(_modules_data(view), request)


class PlatformAudienceView(_PlatformView):
    """GET /api/v1/platform/audience — how many cabinets, participants and teachers exist."""

    @extend_schema(
        tags=[_TAG],
        operation_id="platform_audience",
        summary="Platform audience",
        description=(
            "Platform-wide head counts: registered personal cabinets (and how many confirmed their "
            "e-mail), participants in the cabinets' registries (and how many are archived) and "
            "teachers. Deliberately unfiltered — a cabinet belongs to a person, not to a festival."
        ),
        request=None,
        responses={
            200: AudienceResponseSerializer,
            403: OpenApiResponse(ProblemDetailSerializer, description="Not a platform administrator."),
        },
    )
    def get(self, request: Request) -> Response:
        audience = build_audience()
        data = {
            "cabinets": {"total": audience.cabinets, "emailVerified": audience.verified_cabinets},
            "participants": {"total": audience.participants, "archived": audience.archived_participants},
            "teachers": {"total": audience.teachers, "archived": audience.archived_teachers},
        }
        return _envelope(data, request)


class PlatformDashboardView(_PlatformView):
    """GET /api/v1/platform/dashboard — the platform's books across every organization."""

    @extend_schema(
        tags=[_TAG],
        operation_id="platform_dashboard",
        summary="Platform dashboard",
        description=(
            "What the platform is owed, what it has been paid and what it has spent, across all "
            "connected organizations, with the order funnel behind the figures.\n\n"
            "Commission is counted per **performance**, never per order: an entry is billable once it "
            "is committed to taking part (`ACCEPTED`, `SCHEDULED` or `COMPLETED`), and is priced "
            "either off the organization's fee schedule — banded by how many participants it has, with "
            "`feeBreakdown` giving the per-band rows an act is written from — or as a percentage of "
            "what those entries themselves cost. Additional services an organizer sells are outside "
            "the base in both models.\n\n"
            "`accruedCommission` is what is owed; `receivedCommission` is what the operator has "
            "recorded as actually paid in the commission receipts ledger; `commissionDebt` is the "
            "difference.\n\n"
            "Filterable by organization, by competition and by period. Under a competition filter "
            "`expensesApply` is false, because expenses and receipts are recorded per organization "
            "and never per festival. A period narrows the money — entries by the day they became "
            "chargeable, expenses by the day they were spent, receipts by the day they landed — and "
            "leaves the order funnel alone, which `periodApplies` says so the console can label it."
        ),
        parameters=[
            OpenApiParameter(name="organizationId", type=str, required=False, description="Narrow to one organization."),
            OpenApiParameter(name="competitionId", type=str, required=False, description="Narrow to one competition."),
            OpenApiParameter(name="from", type=str, required=False, description="Start of the period, inclusive (YYYY-MM-DD)."),
            OpenApiParameter(name="to", type=str, required=False, description="End of the period, inclusive (YYYY-MM-DD)."),
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
            since=_optional_date(request, "from"),
            until=_optional_date(request, "to"),
        )
        data = {
            "statusCounts": dashboard.status_counts,
            "applications": dashboard.applications,
            "orderFees": str(dashboard.order_fees),
            "performances": dashboard.performances,
            "participants": dashboard.participants,
            "commissionBase": str(dashboard.commission_base),
            "accruedCommission": str(dashboard.accrued_commission),
            "receivedCommission": str(dashboard.received_commission),
            "commissionDebt": str(dashboard.commission_debt),
            "expenses": str(dashboard.expenses),
            "unattributedExpenses": str(dashboard.unattributed_expenses),
            "profit": str(dashboard.profit),
            "expensesApply": dashboard.expenses_apply,
            "periodApplies": dashboard.period_applies,
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
                    "orderFees": str(row.order_fees),
                    "performances": row.performances,
                    "participants": row.participants,
                    "commissionBase": str(row.commission_base),
                    "accruedCommission": str(row.accrued_commission),
                    "receivedCommission": str(row.received_commission),
                    "commissionDebt": str(row.commission_debt),
                    "feeBreakdown": _fee_breakdown_data(row.fee_breakdown),
                    "expenses": str(row.expenses),
                    "profit": str(row.profit),
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


def _target_data(target: purge.Target) -> dict[str, Any]:
    return {"kind": target.kind, "id": target.id, "label": target.label, "hint": target.hint}


def _plan_data(plan: purge.Plan) -> dict[str, Any]:
    return {
        "target": _target_data(plan.target),
        "rows": [{"table": row.table, "label": row.label, "count": row.count} for row in plan.rows],
        "total": plan.total,
        "files": plan.files,
        "warnings": list(plan.warnings),
    }


def _purge_refusal(request: Request, error: purge.PurgeError) -> Response:
    """Turn one of the eraser's refusals into the status it deserves."""
    if isinstance(error, purge.UnknownTargetError):
        return _problem(request, str(error), title="Неизвестный тип объекта", status=404)
    if isinstance(error, purge.TargetNotFoundError):
        return _problem(request, str(error), title="Объект не найден", status=404)
    if isinstance(error, purge.SelfDeletionError):
        return _problem(request, str(error), title="Удаление собственного аккаунта", status=409)
    return _problem(request, str(error), title="Подтверждение не совпадает", status=400)


class PlatformPurgeSearchView(_PlatformView):
    """GET /api/v1/platform/purge/search — find the thing that is to be erased.

    Deliberately a search and not a listing: the operator arrives here with a
    specific festival or a specific person in a support request, and a browsable
    table of everything on the platform would turn a targeted, irreversible tool
    into something to click around in.
    """

    @extend_schema(
        tags=[_TAG],
        operation_id="platform_purge_search",
        summary="Find an object to erase",
        description=(
            "Candidates matching the query, by name, email or id. `target` is one of "
            "`festival`, `program`, `application`, `organization`, `template`, `account`, "
            "`participant`, `teacher`."
        ),
        parameters=[
            OpenApiParameter(name="target", type=str, required=True, description="Which kind of object to search."),
            OpenApiParameter(name="query", type=str, required=True, description="A name, an email, or an id."),
        ],
        request=None,
        responses={
            200: PurgeSearchResponseSerializer,
            403: OpenApiResponse(ProblemDetailSerializer, description="Not a platform administrator."),
            404: OpenApiResponse(ProblemDetailSerializer, description="Unknown target kind."),
        },
    )
    def get(self, request: Request) -> Response:
        target = (request.query_params.get("target") or "").strip()
        query = (request.query_params.get("query") or "").strip()
        try:
            candidates = purge.search(target, query)
        except purge.PurgeError as exc:
            return _purge_refusal(request, exc)
        return _envelope([_target_data(candidate) for candidate in candidates], request)


class PlatformPurgeTargetView(_PlatformView):
    """GET/DELETE /api/v1/platform/purge/{target}/{objectId} — the eraser itself.

    ``GET`` is the plan: every table and every file the deletion would take, which
    the console shows before it offers the button. ``DELETE`` executes that same
    plan, and only when ``confirm`` carries the object's own name back — an id
    alone is not enough, because the whole point of the guard is that the caller
    has to have read the thing first.

    There is no undo. See :mod:`apps.platform.presentation.api.v1.purge`.
    """

    @extend_schema(
        tags=[_TAG],
        operation_id="platform_purge_plan",
        summary="What erasing this object would delete",
        description=(
            "Reads only. Returns every table the deletion reaches with its row count, how many "
            "stored files would go with it, and the consequences worth reading twice."
        ),
        request=None,
        responses={
            200: PurgePlanResponseSerializer,
            403: OpenApiResponse(ProblemDetailSerializer, description="Not a platform administrator."),
            404: OpenApiResponse(ProblemDetailSerializer, description="Unknown target kind, or no such object."),
        },
    )
    def get(self, request: Request, target: str, object_id: str) -> Response:
        try:
            plan = purge.plan(target, object_id)
        except purge.PurgeError as exc:
            return _purge_refusal(request, exc)
        return _envelope(_plan_data(plan), request)

    @extend_schema(
        tags=[_TAG],
        operation_id="platform_purge_execute",
        summary="Erase the object and everything it holds",
        description=(
            "Hard delete, not the soft delete the rest of the platform uses: the rows are removed "
            "from the database and the files they reference are removed from storage. There is no undo. "
            "`confirm` must repeat the object's own name exactly as the plan reports it."
        ),
        parameters=[
            OpenApiParameter(name="confirm", type=str, required=True, description="The object's own name, retyped."),
        ],
        request=None,
        responses={
            200: PurgePlanResponseSerializer,
            400: OpenApiResponse(ProblemDetailSerializer, description="Confirmation does not match the object's name."),
            403: OpenApiResponse(ProblemDetailSerializer, description="Not a platform administrator."),
            404: OpenApiResponse(ProblemDetailSerializer, description="Unknown target kind, or no such object."),
            409: OpenApiResponse(ProblemDetailSerializer, description="Refused: that is the caller's own account."),
        },
    )
    def delete(self, request: Request, target: str, object_id: str) -> Response:
        confirm = request.query_params.get("confirm") or ""
        try:
            removed = purge.purge(target, object_id, confirm=confirm, actor_id=_actor_id(request))
        except purge.PurgeError as exc:
            return _purge_refusal(request, exc)
        return _envelope(_plan_data(removed), request)
