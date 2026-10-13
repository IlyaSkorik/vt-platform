"""Application (order) controllers for the Applications REST API v1.

Noun-resource endpoints for the applicant's order: the application collection/detail,
its submission and service sub-collections, the consents and educational-organization
sub-resources, and the lifecycle transitions (placement, payment-request, payment,
cancellation) modelled as sub-resources (API-000 §3.3). Each view is a thin adapter:

    HTTP request -> serializer (validate) -> command -> handler -> DTO -> HTTP response

Every endpoint is authenticated (deny-by-default): the acting applicant is the JWT
subject and owns the order being read or modified.
"""

from __future__ import annotations

from typing import Any

from drf_spectacular.utils import OpenApiParameter, OpenApiResponse, extend_schema
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.applications.application.dto.order_commands import (
    AddSubmissionToApplicationCommand,
    CancelApplicationCommand,
    ConsentInput,
    CreateApplicationCommand,
    MarkApplicationPaidCommand,
    RecordConsentsCommand,
    RemoveAdditionalServiceCommand,
    RemoveApplicationReceiptCommand,
    RemoveSubmissionFromApplicationCommand,
    RequestApplicationPaymentCommand,
    SelectAdditionalServiceCommand,
    SelectEducationalOrganizationCommand,
    SetApplicationPayerCommand,
    SubmitApplicationCommand,
    UploadApplicationReceiptCommand,
)
from apps.applications.application.dto.orders import ApplicationSummaryView, ApplicationView
from apps.applications.application.dto.queries import (
    GetApplicationQuery,
    ListApplicationsQuery,
    ListDraftApplicationsQuery,
)
from apps.applications.application.exceptions import ApplicationError
from apps.applications.infrastructure.models.submission import SubmissionModel
from apps.applications.infrastructure.revisions import note_application_revision
from apps.applications.presentation.api.v1 import problems
from apps.applications.presentation.api.v1.files import file_url
from apps.applications.presentation.api.v1.orders import composition
from apps.applications.presentation.api.v1.orders.serializers import (
    ApplicationDirectoryResponseSerializer,
    ApplicationResponseSerializer,
    CreateApplicationRequestSerializer,
    ProblemDetailSerializer,
    RecordConsentsRequestSerializer,
    SelectEducationalOrganizationRequestSerializer,
    SelectServiceRequestSerializer,
    SetPayerRequestSerializer,
    UploadReceiptRequestSerializer,
)
from apps.identity.infrastructure.auth import CredentialAwareJWTAuthentication

_TAG = "Applications"


def _iso(value: Any) -> Any:
    if value is None:
        return None
    return value.isoformat().replace("+00:00", "Z")


def _application_resource(dto: ApplicationView) -> dict[str, Any]:
    submission_ids = [ref.submission_id for ref in dto.submissions]
    latest_correction_comment: str | None = None
    has_corrections = any(ref.status == "REQUIRES_CORRECTION" for ref in dto.submissions)
    if submission_ids:
        review_rows = SubmissionModel.objects.filter(id__in=submission_ids, deleted_at__isnull=True).values_list("reviews", flat=True)
        latest_at: str = ""
        for reviews in review_rows:
            for review in reviews or []:
                if str(review.get("decision") or "").upper() != "RETURN_FOR_CORRECTION":
                    continue
                comment = str(review.get("comment") or "").strip()
                if not comment:
                    continue
                decided_at = str(review.get("decided_at") or "")
                if decided_at >= latest_at:
                    latest_at = decided_at
                    latest_correction_comment = comment
    total = dto.total_price
    return {
        "id": dto.id,
        "type": "application",
        "competitionId": dto.competition_id,
        "applicantId": dto.applicant_id,
        "status": dto.status,
        "editable": dto.editable,
        "hasCorrections": has_corrections,
        "correctionComment": latest_correction_comment,
        "educationalOrganizationId": dto.educational_organization_id,
        "organizationName": dto.organization_name,
        "payer": (
            {
                "lastName": dto.payer.last_name,
                "firstName": dto.payer.first_name,
                "middleName": dto.payer.middle_name,
                "fullName": dto.payer.full_name,
            }
            if dto.payer is not None
            else None
        ),
        "submissions": [
            {
                "submissionId": ref.submission_id,
                "performanceTitle": ref.performance_title,
                "participantDisplayName": ref.participant_display_name,
                "nomination": ref.nomination,
                "discipline": ref.discipline,
                "status": ref.status,
                "priceAmount": ref.price_amount,
                "currency": ref.currency,
            }
            for ref in dto.submissions
        ],
        "services": [
            {
                "serviceId": line.service_id,
                "name": line.name,
                "unitAmount": line.unit_amount,
                "quantity": line.quantity,
                "lineAmount": line.line_amount,
                "currency": line.currency,
            }
            for line in dto.services
        ],
        "consents": [{"code": c.code, "version": c.version, "acceptedAt": _iso(c.accepted_at)} for c in dto.consents],
        "totalPrice": (
            {
                "totalAmount": total.total_amount,
                "submissionsAmount": total.submissions_amount,
                "servicesAmount": total.services_amount,
                "currency": total.currency,
                "calculatedAt": _iso(total.calculated_at),
            }
            if total is not None
            else None
        ),
        "statusHistory": [
            {"fromStatus": change.from_status, "toStatus": change.to_status, "occurredAt": _iso(change.occurred_at)} for change in dto.status_history
        ],
        "paymentReceipts": [
            {"id": receipt.id, "fileReference": file_url(receipt.file_reference), "uploadedAt": _iso(receipt.uploaded_at)}
            for receipt in dto.payment_receipts
        ],
        "paidAt": _iso(dto.paid_at),
        "createdAt": _iso(dto.created_at),
        "updatedAt": _iso(dto.updated_at),
    }


def _summary_resource(dto: ApplicationSummaryView) -> dict[str, Any]:
    return {
        "id": dto.id,
        "type": "application",
        "competitionId": dto.competition_id,
        "status": dto.status,
        "hasCorrections": dto.has_corrections,
        "submissionCount": dto.submission_count,
        "totalAmount": dto.total_amount,
        "currency": dto.currency,
        "createdAt": _iso(dto.created_at),
        "updatedAt": _iso(dto.updated_at),
    }


def _envelope(request: Request, data: Any, *, status: int) -> Response:
    correlation_id = problems.request_id(request)
    return Response({"data": data, "meta": {"requestId": correlation_id}}, status=status, headers={"X-Request-ID": correlation_id})


def _uid(request: Request) -> str:
    return str(request.user.id)


def _note(application_id: str, change: str) -> None:
    """Journal one applicant edit, so the organizer hears about it if the order is placed.

    A no-op for a draft nobody has seen yet — the journal itself decides that. Called
    only after the handler succeeded, so nothing is ever reported that did not happen.
    """
    note_application_revision(application_id=application_id, change=change)


class _AuthenticatedView(APIView):
    authentication_classes = (CredentialAwareJWTAuthentication,)
    permission_classes = (IsAuthenticated,)


class ApplicationCollectionView(_AuthenticatedView):
    """GET/POST /api/v1/applications - list the applicant's orders or create one."""

    @extend_schema(
        tags=[_TAG],
        operation_id="applications_list",
        summary="List my applications",
        parameters=[OpenApiParameter(name="status", type=str, required=False, description="Filter to a status, e.g. DRAFT.")],
        request=None,
        responses={200: ApplicationDirectoryResponseSerializer},
    )
    def get(self, request: Request) -> Response:
        status_filter = str(request.query_params.get("status", "")).upper()
        try:
            if status_filter == "DRAFT":
                entries = composition.build_list_drafts_handler().handle(ListDraftApplicationsQuery(applicant_id=_uid(request)))
            else:
                entries = composition.build_list_applications_handler().handle(ListApplicationsQuery(applicant_id=_uid(request)))
        except ApplicationError as exc:
            return problems.application_problem(exc, instance=request.path, request=request)
        return _envelope(request, [_summary_resource(dto) for dto in entries], status=200)

    @extend_schema(
        tags=[_TAG],
        operation_id="applications_create",
        summary="Create an application",
        request=CreateApplicationRequestSerializer,
        responses={
            201: ApplicationResponseSerializer,
            400: OpenApiResponse(ProblemDetailSerializer, description="Malformed request."),
            404: OpenApiResponse(ProblemDetailSerializer, description="Competition/applicant not found."),
            409: OpenApiResponse(ProblemDetailSerializer, description="Competition not accepting applications."),
        },
    )
    def post(self, request: Request) -> Response:
        serializer = CreateApplicationRequestSerializer(data=request.data)
        if not serializer.is_valid():
            return problems.validation_problem(serializer.errors, instance=request.path, request=request)
        command = CreateApplicationCommand(requested_by=_uid(request), competition_id=str(serializer.validated_data["competitionId"]))
        try:
            result = composition.build_create_application_handler().handle(command)
        except ApplicationError as exc:
            return problems.application_problem(exc, instance=request.path, request=request)
        response = _envelope(request, _application_resource(result.application), status=201)
        response["Location"] = f"/api/v1/applications/{result.application.id}"
        return response


class ApplicationDetailView(_AuthenticatedView):
    """GET /api/v1/applications/{id} - retrieve one order in full."""

    @extend_schema(
        tags=[_TAG],
        operation_id="applications_retrieve",
        summary="Retrieve an application",
        request=None,
        responses={200: ApplicationResponseSerializer, 404: OpenApiResponse(ProblemDetailSerializer, description="Not found.")},
    )
    def get(self, request: Request, application_id: str) -> Response:
        try:
            dto = composition.build_get_application_handler().handle(GetApplicationQuery(application_id=application_id, requested_by=_uid(request)))
        except ApplicationError as exc:
            return problems.application_problem(exc, instance=request.path, request=request)
        return _envelope(request, _application_resource(dto), status=200)


class ApplicationSubmissionsView(_AuthenticatedView):
    """POST /api/v1/applications/{id}/submissions - add a performance (submission) to the order."""

    @extend_schema(
        tags=[_TAG],
        operation_id="applications_add_submission",
        summary="Add a submission",
        request=None,
        responses={201: ApplicationResponseSerializer},
    )
    def post(self, request: Request, application_id: str) -> Response:
        command = AddSubmissionToApplicationCommand(requested_by=_uid(request), application_id=application_id)
        try:
            result = composition.build_add_submission_handler().handle(command)
        except ApplicationError as exc:
            return problems.application_problem(exc, instance=request.path, request=request)
        _note(application_id, "Добавлено новое выступление")
        return _envelope(request, _application_resource(result.application), status=201)


class ApplicationSubmissionDetailView(_AuthenticatedView):
    """DELETE /api/v1/applications/{id}/submissions/{submissionId} - detach and cancel a submission."""

    @extend_schema(
        tags=[_TAG],
        operation_id="applications_remove_submission",
        summary="Remove a submission",
        request=None,
        responses={200: ApplicationResponseSerializer},
    )
    def delete(self, request: Request, application_id: str, submission_id: str) -> Response:
        command = RemoveSubmissionFromApplicationCommand(requested_by=_uid(request), application_id=application_id, submission_id=submission_id)
        try:
            result = composition.build_remove_submission_handler().handle(command)
        except ApplicationError as exc:
            return problems.application_problem(exc, instance=request.path, request=request)
        _note(application_id, "Выступление удалено из заявки")
        return _envelope(request, _application_resource(result.application), status=200)


class ApplicationServicesView(_AuthenticatedView):
    """POST /api/v1/applications/{id}/services - select an additional service."""

    @extend_schema(
        tags=[_TAG],
        operation_id="applications_select_service",
        summary="Select an additional service",
        request=SelectServiceRequestSerializer,
        responses={200: ApplicationResponseSerializer},
    )
    def post(self, request: Request, application_id: str) -> Response:
        serializer = SelectServiceRequestSerializer(data=request.data)
        if not serializer.is_valid():
            return problems.validation_problem(serializer.errors, instance=request.path, request=request)
        data = serializer.validated_data
        command = SelectAdditionalServiceCommand(
            requested_by=_uid(request), application_id=application_id, service_id=str(data["serviceId"]), quantity=int(data["quantity"])
        )
        try:
            result = composition.build_select_service_handler().handle(command)
        except ApplicationError as exc:
            return problems.application_problem(exc, instance=request.path, request=request)
        selected = next((line for line in result.application.services if line.service_id == command.service_id), None)
        _note(application_id, f"Добавлена дополнительная услуга: {selected.name}" if selected else "Добавлена дополнительная услуга")
        return _envelope(request, _application_resource(result.application), status=200)


class ApplicationServiceDetailView(_AuthenticatedView):
    """DELETE /api/v1/applications/{id}/services/{serviceId} - remove an additional service."""

    @extend_schema(
        tags=[_TAG],
        operation_id="applications_remove_service",
        summary="Remove an additional service",
        request=None,
        responses={200: ApplicationResponseSerializer},
    )
    def delete(self, request: Request, application_id: str, service_id: str) -> Response:
        command = RemoveAdditionalServiceCommand(requested_by=_uid(request), application_id=application_id, service_id=service_id)
        try:
            result = composition.build_remove_service_handler().handle(command)
        except ApplicationError as exc:
            return problems.application_problem(exc, instance=request.path, request=request)
        _note(application_id, "Убрана дополнительная услуга")
        return _envelope(request, _application_resource(result.application), status=200)


class ApplicationConsentsView(_AuthenticatedView):
    """PUT /api/v1/applications/{id}/consents - record the accepted consents."""

    @extend_schema(
        tags=[_TAG],
        operation_id="applications_record_consents",
        summary="Record consents",
        request=RecordConsentsRequestSerializer,
        responses={200: ApplicationResponseSerializer},
    )
    def put(self, request: Request, application_id: str) -> Response:
        serializer = RecordConsentsRequestSerializer(data=request.data)
        if not serializer.is_valid():
            return problems.validation_problem(serializer.errors, instance=request.path, request=request)
        consents = tuple(ConsentInput(code=str(item["code"]), version=str(item["version"])) for item in serializer.validated_data["consents"])
        command = RecordConsentsCommand(requested_by=_uid(request), application_id=application_id, consents=consents)
        try:
            result = composition.build_record_consents_handler().handle(command)
        except ApplicationError as exc:
            return problems.application_problem(exc, instance=request.path, request=request)
        _note(application_id, "Изменён состав согласий")
        return _envelope(request, _application_resource(result.application), status=200)


class ApplicationEducationalOrganizationView(_AuthenticatedView):
    """PUT /api/v1/applications/{id}/educational-organization - select the educational organization."""

    @extend_schema(
        tags=[_TAG],
        operation_id="applications_select_organization",
        summary="Select educational organization",
        request=SelectEducationalOrganizationRequestSerializer,
        responses={200: ApplicationResponseSerializer},
    )
    def put(self, request: Request, application_id: str) -> Response:
        serializer = SelectEducationalOrganizationRequestSerializer(data=request.data)
        if not serializer.is_valid():
            return problems.validation_problem(serializer.errors, instance=request.path, request=request)
        command = SelectEducationalOrganizationCommand(
            requested_by=_uid(request),
            application_id=application_id,
            educational_organization_id=str(serializer.validated_data["educationalOrganizationId"]),
        )
        try:
            result = composition.build_select_educational_organization_handler().handle(command)
        except ApplicationError as exc:
            return problems.application_problem(exc, instance=request.path, request=request)
        name = result.application.organization_name
        _note(application_id, f"Изменена образовательная организация: {name}" if name else "Изменена образовательная организация")
        return _envelope(request, _application_resource(result.application), status=200)


class ApplicationPayerView(_AuthenticatedView):
    """PUT /api/v1/applications/{id}/payer - name who the contract is signed with."""

    @extend_schema(
        tags=[_TAG],
        operation_id="applications_set_payer",
        summary="Set the application payer",
        request=SetPayerRequestSerializer,
        responses={200: ApplicationResponseSerializer},
    )
    def put(self, request: Request, application_id: str) -> Response:
        serializer = SetPayerRequestSerializer(data=request.data)
        if not serializer.is_valid():
            return problems.validation_problem(serializer.errors, instance=request.path, request=request)
        middle = serializer.validated_data.get("middleName")
        command = SetApplicationPayerCommand(
            requested_by=_uid(request),
            application_id=application_id,
            last_name=str(serializer.validated_data["lastName"]),
            first_name=str(serializer.validated_data["firstName"]),
            middle_name=str(middle).strip() or None if middle else None,
        )
        try:
            result = composition.build_set_application_payer_handler().handle(command)
        except ApplicationError as exc:
            return problems.application_problem(exc, instance=request.path, request=request)
        payer = result.application.payer
        _note(application_id, f"Указан заказчик: {payer.full_name}" if payer else "Изменён заказчик")
        return _envelope(request, _application_resource(result.application), status=200)


class _TransitionView(_AuthenticatedView):
    """Base for the lifecycle-transition sub-resources (each a bodyless POST)."""

    def _run(self, request: Request, application_id: str, command: Any, handler: Any) -> Response:
        try:
            result = handler.handle(command)
        except ApplicationError as exc:
            return problems.application_problem(exc, instance=request.path, request=request)
        return _envelope(request, _application_resource(result.application), status=200)


class ApplicationPlacementView(_TransitionView):
    """POST /api/v1/applications/{id}/placement - submit the order."""

    @extend_schema(
        tags=[_TAG],
        operation_id="applications_submit",
        summary="Submit the application",
        request=None,
        responses={200: ApplicationResponseSerializer},
    )
    def post(self, request: Request, application_id: str) -> Response:
        command = SubmitApplicationCommand(requested_by=_uid(request), application_id=application_id)
        return self._run(request, application_id, command, composition.build_submit_application_handler())


class ApplicationPaymentRequestView(_TransitionView):
    """POST /api/v1/applications/{id}/payment-request - move to awaiting payment."""

    @extend_schema(
        tags=[_TAG],
        operation_id="applications_request_payment",
        summary="Request payment",
        request=None,
        responses={200: ApplicationResponseSerializer},
    )
    def post(self, request: Request, application_id: str) -> Response:
        command = RequestApplicationPaymentCommand(requested_by=_uid(request), application_id=application_id)
        return self._run(request, application_id, command, composition.build_request_payment_handler())


class ApplicationPaymentView(_TransitionView):
    """POST /api/v1/applications/{id}/payment - record payment."""

    @extend_schema(
        tags=[_TAG], operation_id="applications_mark_paid", summary="Mark paid", request=None, responses={200: ApplicationResponseSerializer}
    )
    def post(self, request: Request, application_id: str) -> Response:
        command = MarkApplicationPaidCommand(requested_by=_uid(request), application_id=application_id)
        return self._run(request, application_id, command, composition.build_mark_paid_handler())


class ApplicationCancellationView(_TransitionView):
    """POST /api/v1/applications/{id}/cancellation - cancel the order."""

    @extend_schema(
        tags=[_TAG],
        operation_id="applications_cancel",
        summary="Cancel the application",
        request=None,
        responses={200: ApplicationResponseSerializer},
    )
    def post(self, request: Request, application_id: str) -> Response:
        command = CancelApplicationCommand(requested_by=_uid(request), application_id=application_id)
        return self._run(request, application_id, command, composition.build_cancel_application_handler())


class ApplicationReceiptsView(_AuthenticatedView):
    """POST /api/v1/applications/{id}/receipts - attach one more payment receipt.

    A collection, not a single document: an order's fee is regularly settled by
    several transfers, so posting again adds a receipt instead of replacing the
    one already there.
    """

    parser_classes = (MultiPartParser, FormParser)

    @extend_schema(
        tags=[_TAG],
        operation_id="applications_upload_receipt",
        summary="Attach a payment receipt",
        request={"multipart/form-data": UploadReceiptRequestSerializer},
        responses={
            200: ApplicationResponseSerializer,
            400: OpenApiResponse(ProblemDetailSerializer, description="Malformed request."),
            404: OpenApiResponse(ProblemDetailSerializer, description="Application not found."),
            409: OpenApiResponse(ProblemDetailSerializer, description="Settled, or too many receipts already."),
            413: OpenApiResponse(ProblemDetailSerializer, description="File too large."),
            415: OpenApiResponse(ProblemDetailSerializer, description="Unsupported file type."),
        },
    )
    def post(self, request: Request, application_id: str) -> Response:
        serializer = UploadReceiptRequestSerializer(data=request.data)
        if not serializer.is_valid():
            return problems.validation_problem(serializer.errors, instance=request.path, request=request)
        upload = serializer.validated_data["file"]
        command = UploadApplicationReceiptCommand(
            requested_by=_uid(request),
            application_id=application_id,
            filename=str(upload.name),
            content_type=str(getattr(upload, "content_type", "") or "application/octet-stream"),
            content=upload.read(),
        )
        try:
            result = composition.build_upload_receipt_handler().handle(command)
        except ApplicationError as exc:
            return problems.application_problem(exc, instance=request.path, request=request)
        _note(application_id, "Прикреплена квитанция об оплате")
        return _envelope(request, _application_resource(result.application), status=200)


class ApplicationReceiptDetailView(_AuthenticatedView):
    """DELETE /api/v1/applications/{id}/receipts/{receipt_id} - take one receipt back."""

    @extend_schema(
        tags=[_TAG],
        operation_id="applications_remove_receipt",
        summary="Remove a payment receipt",
        request=None,
        responses={
            200: ApplicationResponseSerializer,
            404: OpenApiResponse(ProblemDetailSerializer, description="Application or receipt not found."),
            409: OpenApiResponse(ProblemDetailSerializer, description="The order is already settled."),
        },
    )
    def delete(self, request: Request, application_id: str, receipt_id: str) -> Response:
        command = RemoveApplicationReceiptCommand(
            requested_by=_uid(request),
            application_id=application_id,
            receipt_id=receipt_id,
        )
        try:
            result = composition.build_remove_receipt_handler().handle(command)
        except ApplicationError as exc:
            return problems.application_problem(exc, instance=request.path, request=request)
        _note(application_id, "Удалена квитанция об оплате")
        return _envelope(request, _application_resource(result.application), status=200)
