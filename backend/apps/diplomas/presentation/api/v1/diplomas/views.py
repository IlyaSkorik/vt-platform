"""Diplomas workspace REST surface (organizer-only).

Reads the template library (with usage counts), manages the assignment mechanism
that binds a template to a (competition, nomination) pair, runs generation — the
numbered diploma package asynchronously, the other kinds in the request — and lists
the archive of completed runs.

**Every endpoint here is scoped to one organization**, because the platform hosts
several and a diploma design is not something an organizer shares. Two mechanisms,
picked by what the request names:

* A **listing** carries a :class:`~apps.diplomas.presentation.scope.Scope` into the
  query, so it can only ever return the caller's own rows.
* A request that names an **id** — a template, a competition, a diploma, a print
  job — is refused up front by the guards below, before any work is done. That
  mirrors ``CompetitionViewSet.initial``: authorization is answered in the
  presentation layer, and the reason reaches the client as a 403.

Neither is optional anywhere on this surface. Before this was true, any organizer
could read and overwrite anyone's template by id.
"""

from __future__ import annotations

import uuid
from typing import Any

from django.core.files.storage import default_storage
from django.db.models import QuerySet
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework.exceptions import PermissionDenied
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.applications.infrastructure.models.submission import SubmissionModel
from apps.diplomas.domain.exceptions import DiplomaError
from apps.diplomas.infrastructure.acl import actor_label
from apps.diplomas.infrastructure.models import DiplomaModel, PrintJobModel, TemplateModel
from apps.diplomas.presentation.api.v1 import problems
from apps.diplomas.presentation.api.v1.diplomas import (
    archive,
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
    GenerationRunResponseSerializer,
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
from apps.diplomas.presentation.scope import callers_scope, competition_organizer_id
from apps.identity.infrastructure.auth import CredentialAwareJWTAuthentication
from apps.organization.domain.value_objects import OrganizationModule
from apps.organization.presentation.permissions import IsModuleEnabled, IsOrganizationStaff
from apps.platform.presentation.permissions import IsPlatformAdministrator

_TAG = "Diplomas"
_MAX_PDF_BYTES = 20 * 1024 * 1024


class _StaffView(APIView):
    authentication_classes = (CredentialAwareJWTAuthentication,)
    # Staff of an organization, **or** the platform operator. The operator is staff
    # of nobody, so `IsOrganizationStaff` alone would refuse them — and then the
    # unrestricted branch of every scope below would be unreachable code.
    permission_classes = (IsAuthenticated, IsOrganizationStaff | IsPlatformAdministrator, IsModuleEnabled.of(OrganizationModule.DIPLOMAS))


# ----------------------------------------------------------------------------
# Organization scoping
#
# Guards, not filters: each one answers before the endpoint does any work. They
# raise rather than return a problem document so a new endpoint cannot forget to
# check the return value — the request stops whether or not the caller looked.
# ----------------------------------------------------------------------------


def _refuse_foreign_template(request: Request, template_id: str) -> None:
    """Refuse a template belonging to another organization.

    An **absent** template is deliberately not this function's business: the
    endpoint's own composition call raises ``TemplateNotFoundError`` and renders a
    proper 404. Only ownership is decided here.
    """
    organizer_id = TemplateModel.objects.filter(id=template_id, deleted_at__isnull=True).values_list("organizer_id", flat=True).first()
    if organizer_id is None:
        return
    if not callers_scope(request).admits(organizer_id):
        raise PermissionDenied("Этот шаблон принадлежит другой организации.")


def _refuse_foreign_competition(request: Request, competition_id: uuid.UUID | str) -> None:
    """Refuse a competition run by another organization.

    Unlike a template, an unknown competition **is** refused here. A competition id
    arrives as a filter on somebody else's data rather than as the addressed
    resource, so there is no 404 waiting downstream to answer it — left to fall
    through, an unknown id would simply widen the read.
    """
    if not callers_scope(request).admits(competition_organizer_id(competition_id)):
        raise PermissionDenied("Этот фестиваль принадлежит другой организации.")


def _refuse_foreign_row(request: Request, rows: QuerySet[Any], row_id: uuid.UUID) -> None:
    """Refuse a row that hangs off another organization's competition.

    A diploma, a print job and a submission carry no owner of their own — each names
    a ``competition_id``, and whoever runs that competition owns the row. An absent
    row falls through to the endpoint's own 404, as with a template.

    Takes a queryset rather than a model class because that is what it needs, and
    ``type[Model]`` has no manager to promise: ``objects`` is attached per concrete
    model, so the class form types as an escape hatch and this one does not.
    """
    competition_id = rows.filter(id=row_id, deleted_at__isnull=True).values_list("competition_id", flat=True).first()
    if competition_id is None:
        return
    _refuse_foreign_competition(request, competition_id)


def _authoring_organization(request: Request) -> uuid.UUID:
    """The organization a write is filed under, or a refusal.

    Reading across organizations and *writing into* one are different rights. The
    platform operator holds the first and not the second: they are staff of no
    organization, so there is no library for a template of theirs to land in. Saying
    so is better than inventing an owner.
    """
    scope = callers_scope(request)
    if scope.organization_id is None:
        raise PermissionDenied("Создание шаблона возможно только от лица организации. Оператор платформы читает библиотеки, но не ведёт свою.")
    return scope.organization_id


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
            return problems.validation_problem({"type": ["Неизвестный тип документа."]}, instance=request.path, request=request)
        return problems.envelope(request, composition.list_templates(scope=callers_scope(request), document_type=document_type or None))

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
            organizer_id=_authoring_organization(request),
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

        # Before the upload, not after: `default_storage.save` below writes the file
        # to the bucket under a path keyed by the template id, so refusing later
        # would still have deposited a foreign PDF next to that template's own.
        _refuse_foreign_template(request, template_id)

        relative_path = default_storage.save(f"diplomas/templates/{template_id}/{uuid.uuid4().hex}.pdf", uploaded)
        file_reference = default_storage.url(relative_path)
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
            return problems.validation_problem({"competitionId": ["Укажите фестиваль."]}, instance=request.path, request=request)
        # Preview rows are real applications — real participants, real works. The
        # editor only ever asks for the competition it is already open on.
        _refuse_foreign_competition(request, competition_id)
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
            return problems.validation_problem({"documentType": ["Неизвестный тип документа."]}, instance=request.path, request=request)
        bindings = preview.resolve_preview_bindings(application_id, document_type=document_type) if application_id else None
        if bindings is None:
            return problems.problem_response(
                status=404,
                type_suffix="not-found",
                title="Resource not found",
                detail="Заявка не найдена.",
                instance=request.path,
                correlation_id=problems.request_id(request),
            )
        return problems.envelope(request, {"bindings": bindings})


class DiplomaTemplateLayoutView(_StaffView):
    """Read and atomically save a template's field layout (the whole document).

    Both verbs address one template, so the ownership guard runs in :meth:`initial`
    for the whole class rather than being repeated in each — the PUT is the one that
    would silently rewrite another organization's design.
    """

    def initial(self, request: Request, *args: object, **kwargs: object) -> None:
        super().initial(request, *args, **kwargs)
        template_id = kwargs.get("template_id")
        if isinstance(template_id, str):
            _refuse_foreign_template(request, template_id)

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
    """List and create template assignments.

    A create is a batch: one template, one or more nominations, all or nothing. The
    organizer assigns the same design across a competition's nominations, so the
    batch is the natural unit and a single nomination is a batch of one.
    """

    @extend_schema(
        tags=[_TAG],
        operation_id="diplomas_assignments_list",
        responses={200: AssignmentResponseSerializer(many=True)},
    )
    def get(self, request: Request) -> Response:
        return problems.envelope(request, composition.list_assignments(scope=callers_scope(request)))

    @extend_schema(
        tags=[_TAG],
        operation_id="diplomas_create_assignment",
        request=CreateAssignmentRequestSerializer,
        responses={201: AssignmentResponseSerializer(many=True)},
    )
    def post(self, request: Request) -> Response:
        serializer = CreateAssignmentRequestSerializer(data=request.data)
        if not serializer.is_valid():
            return problems.validation_problem(serializer.errors, instance=request.path, request=request)
        data = serializer.validated_data
        # Both sides of the binding, because an assignment is the one write that
        # *joins* them: a template of this organization onto a competition of this
        # organization. Checking one alone would let a caller file their own design
        # against somebody else's festival, or somebody else's design against theirs.
        _refuse_foreign_template(request, str(data["templateId"]))
        _refuse_foreign_competition(request, str(data["competitionId"]))
        try:
            assignments = composition.create_assignments(
                competition_id=str(data["competitionId"]),
                category_ids=[str(category_id) for category_id in data["categoryIds"]],
                template_id=str(data["templateId"]),
                scope=callers_scope(request),
            )
        except DiplomaError as exc:
            return problems.diploma_problem(exc, instance=request.path, request=request)
        return problems.envelope(request, assignments, status=201)


class DiplomaAssignmentDetailView(_StaffView):
    """Delete a single template assignment."""

    @extend_schema(
        tags=[_TAG],
        operation_id="diplomas_delete_assignment",
        responses={204: None},
    )
    def delete(self, request: Request, assignment_id: str) -> Response:
        try:
            composition.delete_assignment(assignment_id, scope=callers_scope(request))
        except DiplomaError as exc:
            return problems.diploma_problem(exc, instance=request.path, request=request)
        rid = problems.request_id(request)
        return Response(status=204, headers={"X-Request-ID": rid})


def _parse_uuid(value: str) -> uuid.UUID | None:
    try:
        return uuid.UUID(value)
    except (ValueError, AttributeError):
        return None


def _actor(request: Request) -> tuple[uuid.UUID | None, str]:
    """The acting staff member as ``(id, display name)`` for the generation archive.

    The token carries only the subject, so the name is resolved once here and
    snapshotted with the run — the archive says who generated a package at the time,
    not who that account is called today. An unresolvable actor yields ``(None, "")``
    rather than blocking a generation over a missing label.
    """
    raw = getattr(getattr(request, "user", None), "id", None)
    actor_id = _parse_uuid(str(raw)) if raw is not None else None
    return actor_id, actor_label(actor_id)


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
            return problems.validation_problem({"competitionId": ["Укажите фестиваль."]}, instance=request.path, request=request)
        _refuse_foreign_competition(request, competition_id)
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
        # Two ids, two organizations to check. The template is this context's row;
        # the submission belongs to Applications and reaches its competition through
        # `competition_id` there. Guarding only the template would let a caller stamp
        # their own design onto another organization's performance — creating a
        # numbered diploma, off their sequence, in somebody else's registry.
        _refuse_foreign_template(request, str(data["templateId"]))
        _refuse_foreign_row(request, SubmissionModel.objects.all(), data["submissionId"])
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
                detail="Документ не найден.",
                instance=request.path,
                correlation_id=problems.request_id(request),
            )
        _refuse_foreign_row(request, DiplomaModel.objects.all(), parsed)
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
            return problems.validation_problem({"competitionId": ["Укажите фестиваль."]}, instance=request.path, request=request)
        _refuse_foreign_competition(request, competition_id)
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
        # A write, and an expensive one: it creates diplomas, renders every page and
        # uploads a ZIP. Refused before the job is queued rather than inside the
        # worker, where a failure has no request left to answer.
        _refuse_foreign_competition(request, str(data["competitionId"]))
        actor_id, label = _actor(request)
        try:
            job = print_package.start_print_package(
                competition_id=data["competitionId"],
                category_ids=[str(cid) for cid in data.get("categoryIds", [])],
                force=bool(data.get("force", False)),
                actor_id=actor_id,
                actor_label=label,
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

    Synchronous: there is no numbering to serialize, so the run completes in the
    request. ``publish`` and ``bundle`` are independent: a run can publish the
    documents to the participants' cabinets, hand back a ZIP to print from, or —
    for a print-only run — generate them without publishing anything yet.
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
        # `publish=True` by default puts the generated documents into participants'
        # cabinets. On another organization's competition that is not a leak, it is a
        # delivery — hence the guard before anything is rendered.
        _refuse_foreign_competition(request, str(data["competitionId"]))
        actor_id, label = _actor(request)
        try:
            summary = documents.generate_documents(
                competition_id=data["competitionId"],
                category_ids=list(data["categoryIds"]),
                document_type=str(data["documentType"]),
                force=bool(data.get("force", False)),
                bundle=bool(data.get("bundle", False)),
                publish=bool(data.get("publish", True)),
                actor_id=actor_id,
                actor_label=label,
            )
        except DiplomaError as exc:
            return problems.diploma_problem(exc, instance=request.path, request=request)
        return problems.envelope(request, summary)


class DiplomaGenerationArchiveView(_StaffView):
    """The generation history: every completed run, newest first.

    One list for every kind of run — the diploma print package and the thank-you
    runs — because the organizer's question ("what did we generate, and where is that
    ZIP?") does not care which mechanism produced it.
    """

    @extend_schema(
        tags=[_TAG],
        operation_id="diplomas_generation_archive",
        parameters=[
            OpenApiParameter(
                name="competitionId",
                type=str,
                location=OpenApiParameter.QUERY,
                description="Narrow the history to one competition (optional).",
            )
        ],
        responses={200: GenerationRunResponseSerializer(many=True)},
    )
    def get(self, request: Request) -> Response:
        raw = (request.query_params.get("competitionId") or "").strip()
        competition_id = _parse_uuid(raw) if raw else None
        if raw and competition_id is None:
            return problems.validation_problem(
                {"competitionId": ["Некорректный идентификатор фестиваля."]},
                instance=request.path,
                request=request,
            )
        if competition_id is not None:
            _refuse_foreign_competition(request, competition_id)
        return problems.envelope(request, archive.list_runs(competition_id, scope=callers_scope(request)))


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
                detail="Задание на печать не найдено.",
                instance=request.path,
                correlation_id=problems.request_id(request),
            )
        _refuse_foreign_row(request, PrintJobModel.objects.all(), parsed)
        try:
            job = print_package.get_print_job(parsed)
        except DiplomaError as exc:
            return problems.diploma_problem(exc, instance=request.path, request=request)
        return problems.envelope(request, job)
