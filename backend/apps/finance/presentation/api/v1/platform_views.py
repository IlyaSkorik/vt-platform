"""The platform operator's expense book, over HTTP.

Every route here is gated by :class:`IsPlatformAdministrator` and there is no
organizer-facing counterpart. That is the point: what the platform spends is not
an organization's business, and an endpoint an organization could reach would make
the platform's overheads visible to the clients it is charged against.

Lives in this context rather than in ``apps.platform`` for the same reason the
operator's review list does: recording an expense is what Finance owns, and a
console that wrote to another context's tables directly would be a second, quieter
copy of this one's rules. What ``apps.platform`` supplies is the permission class.
"""

from __future__ import annotations

import uuid
from datetime import date

from drf_spectacular.utils import OpenApiParameter, OpenApiResponse, extend_schema
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.finance.application.dto.commands import AmendExpenseCommand, RecordExpenseCommand
from apps.finance.composition import build_expense_service
from apps.finance.domain.exceptions import ExpenseNotFoundError, FinanceError
from apps.finance.presentation.api.v1 import resources
from apps.finance.presentation.api.v1.problems import envelope, finance_problem
from apps.finance.presentation.api.v1.serializers import (
    EXPENSE_CATEGORIES,
    AmendExpenseRequestSerializer,
    ExpenseLedgerResponseSerializer,
    ExpenseResponseSerializer,
    FinanceProblemDetailSerializer,
    RecordExpenseRequestSerializer,
)
from apps.identity.infrastructure.auth import CredentialAwareJWTAuthentication
from apps.platform.presentation.permissions import IsPlatformAdministrator

_TAG = "Platform Finance"

__all__ = ["PlatformExpenseCollectionView", "PlatformExpenseDetailView"]

_PROBLEM_RESPONSES = {
    400: OpenApiResponse(FinanceProblemDetailSerializer, description="Malformed request."),
    403: OpenApiResponse(FinanceProblemDetailSerializer, description="Not a platform operator."),
    404: OpenApiResponse(FinanceProblemDetailSerializer, description="No such expense."),
}


def _optional_date(request: Request, name: str) -> date | None:
    """A ``YYYY-MM-DD`` query parameter, or ``None`` when it was not sent.

    An unparseable date is treated as absent rather than refused: these are the
    two ends of a period filter on a screen, and a half-typed date in the address
    bar should narrow nothing, not blank the ledger with an error.
    """
    from datetime import date

    raw = (request.query_params.get(name) or "").strip()
    if not raw:
        return None
    try:
        return date.fromisoformat(raw)
    except ValueError:
        return None


def _parsed(expense_id: str) -> uuid.UUID | None:
    """The id in the path, or ``None`` when it is not one."""
    try:
        return uuid.UUID(expense_id)
    except (ValueError, TypeError):
        return None


class _OperatorView(APIView):
    """The platform operator, and nobody else."""

    authentication_classes = (CredentialAwareJWTAuthentication,)
    permission_classes = (IsAuthenticated, IsPlatformAdministrator)

    def _problem(self, error: FinanceError, request: Request) -> Response:
        return finance_problem(error, instance=request.get_full_path(), request=request)


class PlatformExpenseCollectionView(_OperatorView):
    """``GET``/``POST`` the platform's expenses."""

    @extend_schema(
        tags=[_TAG],
        operation_id="platform_expenses_list",
        summary="The platform's expense book",
        description=(
            "Recorded costs, newest first, with their total and a breakdown by article. "
            "Every filter is optional and narrows both the list and the totals beside it: "
            "`organizationId` to costs carried for one client, `category` to one article, "
            "`from`/`to` to a period, read against the day the money went rather than the "
            "day it was typed in."
        ),
        parameters=[
            OpenApiParameter(name="organizationId", type=str, required=False, description="Only costs carried for this organization."),
            OpenApiParameter(name="category", type=str, required=False, enum=list(EXPENSE_CATEGORIES), description="Only this article."),
            OpenApiParameter(name="from", type=str, required=False, description="Earliest spending date, inclusive (YYYY-MM-DD)."),
            OpenApiParameter(name="to", type=str, required=False, description="Latest spending date, inclusive (YYYY-MM-DD)."),
        ],
        request=None,
        responses={200: ExpenseLedgerResponseSerializer, **_PROBLEM_RESPONSES},
    )
    def get(self, request: Request) -> Response:
        try:
            view = build_expense_service().ledger(
                organization_id=(request.query_params.get("organizationId") or "").strip() or None,
                category=(request.query_params.get("category") or "").strip() or None,
                since=_optional_date(request, "from"),
                until=_optional_date(request, "to"),
            )
        except FinanceError as exc:
            return self._problem(exc, request)
        return envelope(resources.ledger(view), request)

    @extend_schema(
        tags=[_TAG],
        operation_id="platform_expenses_record",
        summary="Record an expense",
        description=(
            "Enter one cost. `purpose` is what the money went on and is required — it is the "
            "line the total is read back through. `organizationId` attributes the cost to one "
            "client, so it counts against that client's commission; omit it for the platform's "
            "own overheads."
        ),
        request=RecordExpenseRequestSerializer,
        responses={201: ExpenseResponseSerializer, **_PROBLEM_RESPONSES},
    )
    def post(self, request: Request) -> Response:
        serializer = RecordExpenseRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        payload = serializer.validated_data
        organization = payload.get("organizationId")
        command = RecordExpenseCommand(
            amount=str(payload["amount"]),
            category=str(payload["category"]),
            purpose=str(payload["purpose"]),
            spent_at=payload["spentAt"],
            organization_id=None if organization is None else str(organization),
            note=str(payload.get("note") or ""),
            # Who entered it. Recorded on the row rather than in a log: a figure in
            # the books that nobody owns is one nobody can be asked about.
            recorded_by=str(request.user.id),
        )
        try:
            view = build_expense_service().record(command)
        except FinanceError as exc:
            return self._problem(exc, request)
        return envelope(resources.expense(view), request, status=201)


class PlatformExpenseDetailView(_OperatorView):
    """``PATCH``/``DELETE`` one recorded expense."""

    @extend_schema(
        tags=[_TAG],
        operation_id="platform_expenses_amend",
        summary="Correct a recorded expense",
        description=(
            "Every field is optional and an omitted one is left alone. Sending "
            "`organizationId: null` explicitly moves the cost off the client and onto the "
            "platform — omitting the key entirely leaves the attribution as it was."
        ),
        request=AmendExpenseRequestSerializer,
        responses={200: ExpenseResponseSerializer, **_PROBLEM_RESPONSES},
    )
    def patch(self, request: Request, expense_id: str) -> Response:
        # An id that is not an id names nothing, and "nothing" is a 404 rather than a
        # malformed-request 400 — the same answer this route gives for an id that is
        # well-formed and simply not in the books.
        if _parsed(expense_id) is None:
            return self._problem(ExpenseNotFoundError("Расход не найден."), request)
        serializer = AmendExpenseRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        payload = serializer.validated_data
        # Present-and-null is a value here ("carry this yourself"), absent is not a
        # value at all. Only the raw body can tell the two apart, because the
        # serializer renders both as a missing key.
        reassign = isinstance(request.data, dict) and "organizationId" in request.data
        organization = payload.get("organizationId")
        command = AmendExpenseCommand(
            expense_id=expense_id,
            amount=None if "amount" not in payload else str(payload["amount"]),
            category=None if "category" not in payload else str(payload["category"]),
            purpose=None if "purpose" not in payload else str(payload["purpose"]),
            spent_at=payload.get("spentAt"),
            note=None if "note" not in payload else str(payload["note"]),
            organization_id=None if organization is None else str(organization),
            reassign=reassign,
        )
        try:
            view = build_expense_service().amend(command)
        except FinanceError as exc:
            return self._problem(exc, request)
        return envelope(resources.expense(view), request)

    @extend_schema(
        tags=[_TAG],
        operation_id="platform_expenses_delete",
        summary="Strike an expense from the books",
        request=None,
        responses={204: OpenApiResponse(description="Removed."), **_PROBLEM_RESPONSES},
    )
    def delete(self, request: Request, expense_id: str) -> Response:
        parsed = _parsed(expense_id)
        if parsed is None:
            return self._problem(ExpenseNotFoundError("Расход не найден."), request)
        try:
            build_expense_service().remove(parsed)
        except FinanceError as exc:
            return self._problem(exc, request)
        return Response(status=204)
