"""Diplomas workspace REST surface (organizer-only).

MVP endpoints: read the template library (with usage counts) and manage the
assignment mechanism that binds a template to a (competition, nomination) pair.
Generation and archive are future work and have no endpoints yet.
"""

from __future__ import annotations

import uuid

from django.conf import settings
from django.core.files.storage import default_storage
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.diplomas.domain.exceptions import DiplomaError
from apps.diplomas.presentation.api.v1 import problems
from apps.diplomas.presentation.api.v1.diplomas import (
    composition,
    documents,
    preview,
    print_package,
    registry,
)
from apps.diplomas.presentation.api.v1.diplomas.serializers import (
    DOCUMENT_TYPES,
    AssignmentResponseSerializer,
    CreateAssignmentRequestSerializer,
    CreateDiplomaRequestSerializer,
    CreateTemplateRequestSerializer,
    DiplomaResponseSerializer,
    GenerateDocumentsRequestSerializer,
    GenerateDocumentsResponseSerializer,
    LayoutResponseSerializer,
    PreviewApplicationSerializer,
    PreviewBindingsSerializer,
    PrintJobResponseSerializer,
    PrintPackageRequestSerializer,
    PrintPackageSummaryResponseSerializer,
    SaveLayoutRequestSerializer,
    TemplateDocumentResponseSerializer,
    TemplateResponseSerializer,
    UploadTemplateDocumentRequestSerializer,
)
from apps.identity.infrastructure.auth import CredentialAwareJWTAuthentication
from apps.organization.presentation.permissions import IsOrganizationStaff

_TAG = "Diplomas"
_MAX_PDF_BYTES = 20 * 1024 * 1024


class _StaffView(APIView):
    authentication_classes = (CredentialAwareJWTAuthentication,)
    permission_classes = (IsAuthenticated, IsOrganizationStaff)


class DiplomaTemplatesView(_StaffView):
    """The reusable template library, optionally narrowed to one document kind."""

    @extend_schema(
        tags=[_TAG],
        operation_id="diplomas_templates_list",
        parameters=[
            OpenApiParameter(
                name="type",
                type=str,
                location=OpenApiParameter.QUERY,
                enum=DOCUMENT_TYPES,
                description="Return only templates of this kind (a nomination's thank-you slot uses this).",
            )
        ],
        responses={200: TemplateResponseSerializer(many=True)},
    )
    def get(self, request: Request) -> Response:
        document_type = (request.query_params.get("type") or "").strip()
        if document_type and document_type not in DOCUMENT_TYPES:
            return problems.validation_problem(
                {"type": ["Неизвестный тип документа."]}, instance=request.path, request=request
            )
        return problems.envelope(request, composition.list_templates(document_type=document_type or None))

    @extend_schema(
        tags=[_TAG],
        operation_id="diplomas_create_template",
        request=CreateTemplateRequestSerializer,
        responses={201: TemplateResponseSerializer},
    )
    def post(self, request: Request) -> Response:
        serializer = CreateTemplateRequestSerializer(data=request.data)
        if not serializer.is_valid():
            return problems.validation_problem(serializer.errors, instance=request.path, request=request)
        data = serializer.validated_data
        template = composition.create_template(
            name=str(data["name"]),
            document_type=str(data["type"]),
            description=str(data.get("description") or ""),
        )
        return problems.envelope(request, template, status=201)


class DiplomaTemplateDocumentView(_StaffView):
    """Upload (or replace) the PDF a template is marked up over."""

    parser_classes = (MultiPartParser, FormParser)

    @extend_schema(
        tags=[_TAG],
        operation_id="diplomas_upload_template_document",
        request={"multipart/form-data": UploadTemplateDocumentRequestSerializer},
        responses={201: TemplateDocumentResponseSerializer},
    )
    def post(self, request: Request, template_id: str) -> Response:
        uploaded = request.FILES.get("file")
        if uploaded is None:
            return problems.validation_problem({"file": ["Выберите PDF-файл."]}, instance=request.path, request=request)
        content_type = (uploaded.content_type or "").lower()
        if content_type != "application/pdf":
            return problems.validation_problem({"file": ["Допустим только PDF."]}, instance=request.path, request=request)
        if uploaded.size > _MAX_PDF_BYTES:
            return problems.validation_problem(
                {"file": ["Размер файла не должен превышать 20 МБ."]},
                instance=request.path,
                request=request,
            )

        relative_path = default_storage.save(f"diplomas/templates/{template_id}/{uuid.uuid4().hex}.pdf", uploaded)
        file_reference = f"/{settings.MEDIA_URL.strip('/')}/{relative_path}"
        try:
            document = composition.set_template_document(
                template_id=template_id,
                file_reference=file_reference,
                original_filename=str(uploaded.name or ""),
            )
        except DiplomaError as exc:
            return problems.diploma_problem(exc, instance=request.path, request=request)
        return problems.envelope(request, document, status=201)


class DiplomaPreviewApplicationsView(_StaffView):
    """List a competition's applications for the diploma preview picker."""

    @extend_schema(
        tags=[_TAG],
        operation_id="diplomas_preview_applications",
        parameters=[OpenApiParameter(name="competitionId", type=str, location=OpenApiParameter.QUERY)],
        responses={200: PreviewApplicationSerializer(many=True)},
    )
    def get(self, request: Request) -> Response:
        competition_id = (request.query_params.get("competitionId") or "").strip()
        if not competition_id:
            return problems.validation_problem({"competitionId": ["Укажите конкурс."]}, instance=request.path, request=request)
        return problems.envelope(request, preview.list_preview_applications(competition_id))


class DiplomaPreviewBindingsView(_StaffView):
    """Resolve the binding→value map for one application (the BindingResolver)."""

    @extend_schema(
        tags=[_TAG],
        operation_id="diplomas_preview_bindings",
        parameters=[
            OpenApiParameter(name="applicationId", type=str, location=OpenApiParameter.QUERY),
            OpenApiParameter(
                name="documentType",
                type=str,
                location=OpenApiParameter.QUERY,
                enum=DOCUMENT_TYPES,
                description="Formatting rules to preview with (defaults to DIPLOMA).",
            ),
        ],
        responses={200: PreviewBindingsSerializer},
    )
    def get(self, request: Request) -> Response:
        application_id = (request.query_params.get("applicationId") or "").strip()
        document_type = (request.query_params.get("documentType") or "DIPLOMA").strip()
        if document_type not in DOCUMENT_TYPES:
            return problems.validation_problem(
                {"documentType": ["Неизвестный тип документа."]}, instance=request.path, request=request
            )
        bindings = (
            preview.resolve_preview_bindings(application_id, document_type=document_type)
            if application_id
            else None
        )
        if bindings is None:
            return problems.problem_response(
                status=404,
                type_suffix="not-found",
                title="Resource not found",
                detail="Application was not found.",
                instance=request.path,
                correlation_id=problems.request_id(request),
            )
        return problems.envelope(request, {"bindings": bindings})


class DiplomaTemplateLayoutView(_StaffView):
    """Read and atomically save a template's field layout (the whole document)."""

    @extend_schema(
        tags=[_TAG],
        operation_id="diplomas_get_template_layout",
        responses={200: LayoutResponseSerializer},
    )
    def get(self, request: Request, template_id: str) -> Response:
        try:
            layout = composition.get_template_layout(template_id)
        except DiplomaError as exc:
            return problems.diploma_problem(exc, instance=request.path, request=request)
        return problems.envelope(request, layout)

    @extend_schema(
        tags=[_TAG],
        operation_id="diplomas_save_template_layout",
        request=SaveLayoutRequestSerializer,
        responses={200: LayoutResponseSerializer},
    )
    def put(self, request: Request, template_id: str) -> Response:
        serializer = SaveLayoutRequestSerializer(data=request.data)
        if not serializer.is_valid():
            return problems.validation_problem(serializer.errors, instance=request.path, request=request)
        try:
            layout = composition.replace_template_layout(
                template_id=template_id,
                fields=list(serializer.validated_data["fields"]),
            )
        except DiplomaError as exc:
            return problems.diploma_problem(exc, instance=request.path, request=request)
        return problems.envelope(request, layout)


class DiplomaAssignmentsView(_StaffView):
    """List and create template assignments."""

    @extend_schema(
        tags=[_TAG],
        operation_id="diplomas_assignments_list",
        responses={200: AssignmentResponseSerializer(many=True)},
    )
    def get(self, request: Request) -> Response:
        return problems.envelope(request, composition.list_assignments())

    @extend_schema(
        tags=[_TAG],
        operation_id="diplomas_create_assignment",
        request=CreateAssignmentRequestSerializer,
        responses={201: AssignmentResponseSerializer},
    )
    def post(self, request: Request) -> Response:
        serializer = CreateAssignmentRequestSerializer(data=request.data)
        if not serializer.is_valid():
            return problems.validation_problem(serializer.errors, instance=request.path, request=request)
        data = serializer.validated_data
        try:
            assignment = composition.create_assignment(
                competition_id=str(data["competitionId"]),
                category_id=str(data["categoryId"]),
                template_id=str(data["templateId"]),
            )
        except DiplomaError as exc:
            return problems.diploma_problem(exc, instance=request.path, request=request)
        return problems.envelope(request, assignment, status=201)


class DiplomaAssignmentDetailView(_StaffView):
    """Delete a single template assignment."""

    @extend_schema(
        tags=[_TAG],
        operation_id="diplomas_delete_assignment",
        responses={204: None},
    )
    def delete(self, request: Request, assignment_id: str) -> Response:
        try:
            composition.delete_assignment(assignment_id)
        except DiplomaError as exc:
            return problems.diploma_problem(exc, instance=request.path, request=request)
        rid = problems.request_id(request)
        return Response(status=204, headers={"X-Request-ID": rid})


def _parse_uuid(value: str) -> uuid.UUID | None:
    try:
        return uuid.UUID(value)
    except (ValueError, AttributeError):
        return None


class DiplomaRegistryView(_StaffView):
    """The diploma registry: list a competition's diplomas and create one."""

    @extend_schema(
        tags=[_TAG],
        operation_id="diplomas_registry_list",
        parameters=[OpenApiParameter(name="competitionId", type=str, location=OpenApiParameter.QUERY)],
        responses={200: DiplomaResponseSerializer(many=True)},
    )
    def get(self, request: Request) -> Response:
        raw = (request.query_params.get("competitionId") or "").strip()
        competition_id = _parse_uuid(raw)
        if competition_id is None:
            return problems.validation_problem({"competitionId": ["Укажите конкурс."]}, instance=request.path, request=request)
        return problems.envelope(request, registry.list_diplomas(competition_id))

    @extend_schema(
        tags=[_TAG],
        operation_id="diplomas_create_diploma",
        request=CreateDiplomaRequestSerializer,
        responses={201: DiplomaResponseSerializer},
    )
    def post(self, request: Request) -> Response:
        serializer = CreateDiplomaRequestSerializer(data=request.data)
        if not serializer.is_valid():
            return problems.validation_problem(serializer.errors, instance=request.path, request=request)
        data = serializer.validated_data
        try:
            diploma = registry.create_diploma(
                submission_id=data["submissionId"],
                template_id=data["templateId"],
            )
        except DiplomaError as exc:
            return problems.diploma_problem(exc, instance=request.path, request=request)
        return problems.envelope(request, diploma, status=201)


class DiplomaRegistryDetailView(_StaffView):
    """Read a single diploma from the registry."""

    @extend_schema(
        tags=[_TAG],
        operation_id="diplomas_get_diploma",
        responses={200: DiplomaResponseSerializer},
    )
    def get(self, request: Request, diploma_id: str) -> Response:
        parsed = _parse_uuid(diploma_id)
        if parsed is None:
            return problems.problem_response(
                status=404,
                type_suffix="not-found",
                title="Resource not found",
                detail="Diploma was not found.",
                instance=request.path,
                correlation_id=problems.request_id(request),
            )
        try:
            diploma = registry.get_diploma(parsed)
        except DiplomaError as exc:
            return problems.diploma_problem(exc, instance=request.path, request=request)
        return problems.envelope(request, diploma)


class DiplomaPrintPackageSummaryView(_StaffView):
    """Per-nomination print-package summary for a competition."""

    @extend_schema(
        tags=[_TAG],
        operation_id="diplomas_print_package_summary",
        parameters=[OpenApiParameter(name="competitionId", type=str, location=OpenApiParameter.QUERY)],
        responses={200: PrintPackageSummaryResponseSerializer},
    )
    def get(self, request: Request) -> Response:
        raw = (request.query_params.get("competitionId") or "").strip()
        competition_id = _parse_uuid(raw)
        if competition_id is None:
            return problems.validation_problem(
                {"competitionId": ["Укажите конкурс."]}, instance=request.path, request=request
            )
        return problems.envelope(request, print_package.print_package_summary(competition_id))


class DiplomaPrintPackageView(_StaffView):
    """Start a mass print-package generation (async) for chosen nominations:
    create missing diplomas, render PDFs without a degree, and bundle a ZIP."""

    @extend_schema(
        tags=[_TAG],
        operation_id="diplomas_start_print_package",
        request=PrintPackageRequestSerializer,
        responses={202: PrintJobResponseSerializer},
    )
    def post(self, request: Request) -> Response:
        serializer = PrintPackageRequestSerializer(data=request.data)
        if not serializer.is_valid():
            return problems.validation_problem(serializer.errors, instance=request.path, request=request)
        data = serializer.validated_data
        try:
            job = print_package.start_print_package(
                competition_id=data["competitionId"],
                category_ids=[str(cid) for cid in data.get("categoryIds", [])],
                force=bool(data.get("force", False)),
            )
        except DiplomaError as exc:
            return problems.diploma_problem(exc, instance=request.path, request=request)
        return problems.envelope(request, job, status=202)


class DocumentGenerationView(_StaffView):
    """Generate non-registry documents (thank-you letters) for chosen nominations.

    Each nomination is generated from its own assigned template of that kind, so
    «Вокал» may print a blue thank-you while «Хореография» prints a gold one.
    Diplomas are not generated here — they keep the numbered print-package path,
    which this endpoint does not touch.

    Synchronous: there is no numbering to serialize and no ZIP to bundle, so the
    run completes in the request.
    """

    @extend_schema(
        tags=[_TAG],
        operation_id="diplomas_generate_documents",
        request=GenerateDocumentsRequestSerializer,
        responses={200: GenerateDocumentsResponseSerializer},
    )
    def post(self, request: Request) -> Response:
        serializer = GenerateDocumentsRequestSerializer(data=request.data)
        if not serializer.is_valid():
            return problems.validation_problem(serializer.errors, instance=request.path, request=request)
        data = serializer.validated_data
        try:
            summary = documents.generate_documents(
                competition_id=data["competitionId"],
                category_ids=list(data["categoryIds"]),
                document_type=str(data["documentType"]),
                force=bool(data.get("force", False)),
            )
        except DiplomaError as exc:
            return problems.diploma_problem(exc, instance=request.path, request=request)
        return problems.envelope(request, summary)


class DiplomaPrintJobDetailView(_StaffView):
    """Poll a print-package job's status and result."""

    @extend_schema(
        tags=[_TAG],
        operation_id="diplomas_get_print_job",
        responses={200: PrintJobResponseSerializer},
    )
    def get(self, request: Request, job_id: str) -> Response:
        parsed = _parse_uuid(job_id)
        if parsed is None:
            return problems.problem_response(
                status=404,
                type_suffix="not-found",
                title="Resource not found",
                detail="Print job was not found.",
                instance=request.path,
                correlation_id=problems.request_id(request),
            )
        try:
            job = print_package.get_print_job(parsed)
        except DiplomaError as exc:
            return problems.diploma_problem(exc, instance=request.path, request=request)
        return problems.envelope(request, job)
