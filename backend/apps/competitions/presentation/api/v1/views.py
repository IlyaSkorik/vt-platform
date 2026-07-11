"""REST API for Competition management (the organizer control panel).

A single :class:`CompetitionViewSet` exposing every organizer use case. Each
action validates its request with a serializer, assembles the framework-free
command/query via the composition root, invokes the handler, and renders the
result as a camelCase ``{data, meta}`` envelope (API-000 §7). Application and
domain errors are funnelled through :mod:`.problems` into RFC 9457 Problem
Details — views never hand-assemble an error body. The whole surface is
staff-only (:class:`IsOrganizationStaff`); participants cannot reach it.
"""

from __future__ import annotations

import uuid
from decimal import Decimal
from typing import Any, Protocol, cast

from django.conf import settings
from django.core.files.storage import default_storage
from drf_spectacular.utils import OpenApiResponse, extend_schema
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.permissions import BasePermission, IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.serializers import Serializer
from rest_framework_simplejwt.authentication import JWTStatelessUserAuthentication

from apps.competitions.application.dto.commands import (
    AddAdditionalServiceCommand,
    AddAdmissionRuleCommand,
    AddAgeCategoryCommand,
    AddCategoryCommand,
    AddContactCommand,
    AddDisciplineCommand,
    AddDocumentCommand,
    AddInformationBlockCommand,
    AddParticipantGroupCommand,
    AddPricingRuleCommand,
    AddRegulationCommand,
    ArchiveCompetitionCommand,
    ChangePriceCommand,
    CloseRegistrationCommand,
    CompleteCompetitionCommand,
    CreateCompetitionCommand,
    DisableAdditionalServiceCommand,
    DisableFormatCommand,
    EnableAdditionalServiceCommand,
    EnableFormatCommand,
    HideInformationBlockCommand,
    MakeRegulationCurrentCommand,
    MarkConfiguredCommand,
    MarkReadyCommand,
    OpenRegistrationCommand,
    PublishCompetitionCommand,
    PublishDocumentCommand,
    PublishInformationBlockCommand,
    RemoveAdditionalServiceCommand,
    RemoveAdmissionRuleCommand,
    RemoveAgeCategoryCommand,
    RemoveCategoryCommand,
    RemoveContactCommand,
    RemoveDisciplineCommand,
    RemoveDocumentCommand,
    RemoveInformationBlockCommand,
    RemoveParticipantGroupCommand,
    RemovePricingRuleCommand,
    RemoveRegulationCommand,
    RenameCategoryCommand,
    RenameDisciplineCommand,
    RevertToConfiguredCommand,
    RevertToDraftCommand,
    SetPrimaryContactCommand,
    StartCompetitionCommand,
    UnpublishDocumentCommand,
    UpdateAdditionalServiceCommand,
    UpdateBrandingCommand,
    UpdateDeadlinesCommand,
    UpdateDocumentCommand,
    UpdateGeneralInformationCommand,
    UpdateInformationBlockCommand,
    UpdateSettingsCommand,
)
from apps.competitions.application.dto.queries import (
    GetCompetitionQuery,
    ListCompetitionsQuery,
)
from apps.competitions.application.exceptions import ApplicationError
from apps.competitions.application.handlers import (
    AddAdditionalServiceHandler,
    AddAdmissionRuleHandler,
    AddAgeCategoryHandler,
    AddCategoryHandler,
    AddContactHandler,
    AddDisciplineHandler,
    AddDocumentHandler,
    AddInformationBlockHandler,
    AddParticipantGroupHandler,
    AddPricingRuleHandler,
    AddRegulationHandler,
    ArchiveCompetitionHandler,
    ChangePriceHandler,
    CloseRegistrationHandler,
    CompleteCompetitionHandler,
    CreateCompetitionHandler,
    DisableAdditionalServiceHandler,
    DisableFormatHandler,
    EnableAdditionalServiceHandler,
    EnableFormatHandler,
    HideInformationBlockHandler,
    MakeRegulationCurrentHandler,
    MarkCompetitionConfiguredHandler,
    MarkCompetitionReadyHandler,
    OpenRegistrationHandler,
    PublishCompetitionHandler,
    PublishDocumentHandler,
    PublishInformationBlockHandler,
    RemoveAdditionalServiceHandler,
    RemoveAdmissionRuleHandler,
    RemoveAgeCategoryHandler,
    RemoveCategoryHandler,
    RemoveContactHandler,
    RemoveDisciplineHandler,
    RemoveDocumentHandler,
    RemoveInformationBlockHandler,
    RemoveParticipantGroupHandler,
    RemovePricingRuleHandler,
    RemoveRegulationHandler,
    RenameCategoryHandler,
    RenameDisciplineHandler,
    RevertCompetitionToConfiguredHandler,
    RevertCompetitionToDraftHandler,
    SetPrimaryContactHandler,
    StartCompetitionHandler,
    UnpublishDocumentHandler,
    UpdateAdditionalServiceHandler,
    UpdateCompetitionBrandingHandler,
    UpdateCompetitionDeadlinesHandler,
    UpdateCompetitionGeneralInformationHandler,
    UpdateCompetitionSettingsHandler,
    UpdateDocumentHandler,
    UpdateInformationBlockHandler,
)
from apps.competitions.application.handlers._support import CompetitionCommandHandler
from apps.competitions.composition import (
    build_command_handler,
    build_get_competition_handler,
    build_list_competitions_handler,
)
from apps.competitions.domain.exceptions import CompetitionDomainError
from apps.competitions.presentation.api.v1.problems import (
    competition_problem,
    request_id,
    validation_problem,
)
from apps.competitions.presentation.permissions import IsOrganizationStaff

from .serializers import (
    AddAdditionalServiceSerializer,
    AddAdmissionRuleSerializer,
    AddAgeCategorySerializer,
    AddCategorySerializer,
    AddContactSerializer,
    AddDisciplineSerializer,
    AddDocumentSerializer,
    AddInformationBlockSerializer,
    AddParticipantGroupSerializer,
    AddPricingRuleSerializer,
    AddRegulationSerializer,
    ChangePriceSerializer,
    CompetitionDetailEnvelopeSerializer,
    CompetitionDetailSerializer,
    CompetitionListEnvelopeSerializer,
    CompetitionSummarySerializer,
    CreateCompetitionSerializer,
    ParticipationFormatSerializer,
    ProblemDetailSerializer,
    RenameCategorySerializer,
    RenameDisciplineSerializer,
    UpdateAdditionalServiceSerializer,
    UpdateCompetitionBrandingSerializer,
    UpdateCompetitionDeadlinesSerializer,
    UpdateCompetitionGeneralInformationSerializer,
    UpdateCompetitionSettingsSerializer,
    UpdateDocumentSerializer,
    UpdateInformationBlockSerializer,
    _AdmissionCombinationSerializer,
)

_TAG = "Competitions"


class _CommandRunner(Protocol):
    """Structural view of a command handler for the presentation edge."""

    def handle(self, command: Any, /) -> Any: ...


def _error_responses(success: dict[int, Any]) -> dict[int | str, Any]:
    """Shared response schema: the success entries plus the standard problems."""
    responses: dict[int | str, Any] = {}
    for code, schema in success.items():
        responses[code] = schema
    responses[400] = OpenApiResponse(ProblemDetailSerializer, description="Validation failed.")
    responses[403] = OpenApiResponse(ProblemDetailSerializer, description="Not organization staff.")
    responses[404] = OpenApiResponse(ProblemDetailSerializer, description="Competition or element not found.")
    responses[409] = OpenApiResponse(ProblemDetailSerializer, description="Lifecycle or configuration conflict.")
    responses[422] = OpenApiResponse(ProblemDetailSerializer, description="Business rule violation.")
    return responses


def _detail_ok(status_code: int = status.HTTP_200_OK) -> dict[int | str, Any]:
    return _error_responses({status_code: CompetitionDetailEnvelopeSerializer})


def _command_kwargs(serializer: Serializer[Any]) -> dict[str, Any]:
    """Coerce validated data into command-friendly primitives (UUID/Decimal → str)."""
    cleaned: dict[str, Any] = {}
    for key, value in serializer.validated_data.items():
        if isinstance(value, uuid.UUID | Decimal):
            cleaned[key] = str(value)
        else:
            cleaned[key] = value
    return cleaned


class CompetitionViewSet(viewsets.ViewSet):
    """Organizer Competition API — staff-only."""

    authentication_classes = (JWTStatelessUserAuthentication,)
    permission_classes: tuple[type[BasePermission], ...] = (IsAuthenticated, IsOrganizationStaff)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _body(
        self,
        serializer_cls: type[Serializer[Any]],
        request: Request,
    ) -> tuple[dict[str, Any] | None, Response | None]:
        """Validate a request body; return (kwargs, None) or (None, problem)."""
        serializer = serializer_cls(data=request.data)
        if not serializer.is_valid():
            return None, validation_problem(serializer.errors, instance=request.path, request=request)
        return _command_kwargs(serializer), None

    def _run(
        self,
        handler_cls: type[CompetitionCommandHandler],
        command: Any,
        request: Request,
        *,
        success: int = status.HTTP_200_OK,
    ) -> Response:
        """Execute a command handler and render the refreshed competition (or a problem)."""
        handler = cast("_CommandRunner", build_command_handler(handler_cls))
        try:
            result = handler.handle(command)
        except (ApplicationError, CompetitionDomainError) as exc:
            return competition_problem(exc, instance=request.path, request=request)
        return self._detail(result, request, success)

    def _detail(self, view: Any, request: Request, status_code: int) -> Response:
        correlation_id = request_id(request)
        body = {"data": CompetitionDetailSerializer(view).data, "meta": {"requestId": correlation_id}}
        return Response(body, status=status_code, headers={"X-Request-ID": correlation_id})

    # ------------------------------------------------------------------
    # CRUD
    # ------------------------------------------------------------------

    @extend_schema(tags=[_TAG], operation_id="listCompetitions", responses=_error_responses({200: CompetitionListEnvelopeSerializer}))
    def list(self, request: Request) -> Response:
        query = ListCompetitionsQuery(season=request.query_params.get("season"))
        try:
            result = build_list_competitions_handler().handle(query)
        except (ApplicationError, CompetitionDomainError) as exc:
            return competition_problem(exc, instance=request.path, request=request)
        correlation_id = request_id(request)
        data = CompetitionSummarySerializer(cast("Any", result), many=True).data
        return Response({"data": data, "meta": {"requestId": correlation_id}}, status=status.HTTP_200_OK, headers={"X-Request-ID": correlation_id})

    @extend_schema(tags=[_TAG], operation_id="getCompetition", responses=_detail_ok())
    def retrieve(self, request: Request, pk: str) -> Response:
        query = GetCompetitionQuery(competition_id=pk)
        try:
            result = build_get_competition_handler().handle(query)
        except (ApplicationError, CompetitionDomainError) as exc:
            return competition_problem(exc, instance=request.path, request=request)
        return self._detail(result, request, status.HTTP_200_OK)

    @extend_schema(tags=[_TAG], operation_id="createCompetition", request=CreateCompetitionSerializer, responses=_detail_ok(status.HTTP_201_CREATED))
    def create(self, request: Request) -> Response:
        kwargs, problem = self._body(CreateCompetitionSerializer, request)
        if problem is not None:
            return problem
        assert kwargs is not None
        return self._run(CreateCompetitionHandler, CreateCompetitionCommand(**kwargs), request, success=status.HTTP_201_CREATED)

    @extend_schema(
        tags=[_TAG],
        operation_id="updateCompetition",
        request=UpdateCompetitionGeneralInformationSerializer,
        responses=_detail_ok(),
    )
    def partial_update(self, request: Request, pk: str) -> Response:
        kwargs, problem = self._body(UpdateCompetitionGeneralInformationSerializer, request)
        if problem is not None:
            return problem
        assert kwargs is not None
        return self._run(UpdateCompetitionGeneralInformationHandler, UpdateGeneralInformationCommand(competition_id=pk, **kwargs), request)

    @extend_schema(tags=[_TAG], operation_id="updateBranding", request=UpdateCompetitionBrandingSerializer, responses=_detail_ok())
    @action(detail=True, methods=["patch"], url_path="branding")
    def branding(self, request: Request, pk: str) -> Response:
        kwargs, problem = self._body(UpdateCompetitionBrandingSerializer, request)
        if problem is not None:
            return problem
        assert kwargs is not None
        return self._run(UpdateCompetitionBrandingHandler, UpdateBrandingCommand(competition_id=pk, **kwargs), request)

    @extend_schema(
        tags=[_TAG],
        operation_id="uploadCompetitionPoster",
        request={
            "multipart/form-data": {
                "type": "object",
                "properties": {"file": {"type": "string", "format": "binary"}},
                "required": ["file"],
            }
        },
        responses=_detail_ok(),
    )
    @action(detail=True, methods=["post"], url_path="branding/poster", parser_classes=[MultiPartParser, FormParser])
    def upload_poster(self, request: Request, pk: str) -> Response:
        """Upload a competition poster image and store its media reference."""
        uploaded = request.FILES.get("file")
        if uploaded is None:
            return validation_problem(
                {"file": ["Выберите файл афиши."]},
                instance=request.path,
                request=request,
            )

        content_type = (uploaded.content_type or "").lower()
        allowed = {"image/jpeg", "image/png", "image/webp"}
        if content_type not in allowed:
            return validation_problem(
                {"file": ["Допустимы только JPEG, PNG или WebP."]},
                instance=request.path,
                request=request,
            )

        if uploaded.size > 5 * 1024 * 1024:
            return validation_problem(
                {"file": ["Размер файла не должен превышать 5 МБ."]},
                instance=request.path,
                request=request,
            )

        extension_by_type = {
            "image/jpeg": ".jpg",
            "image/png": ".png",
            "image/webp": ".webp",
        }
        extension = extension_by_type[content_type]
        relative_path = default_storage.save(f"competitions/{pk}/poster{extension}", uploaded)
        poster_ref = f"/{settings.MEDIA_URL.strip('/')}/{relative_path}"

        return self._run(
            UpdateCompetitionBrandingHandler,
            UpdateBrandingCommand(
                competition_id=pk,
                logo=None,
                banner=None,
                poster=poster_ref,
            ),
            request,
        )

    @extend_schema(tags=[_TAG], operation_id="updateSettings", request=UpdateCompetitionSettingsSerializer, responses=_detail_ok())
    @action(detail=True, methods=["put"], url_path="settings")
    def configure_settings(self, request: Request, pk: str) -> Response:
        kwargs, problem = self._body(UpdateCompetitionSettingsSerializer, request)
        if problem is not None:
            return problem
        assert kwargs is not None
        return self._run(UpdateCompetitionSettingsHandler, UpdateSettingsCommand(competition_id=pk, **kwargs), request)

    @extend_schema(tags=[_TAG], operation_id="updateDeadlines", request=UpdateCompetitionDeadlinesSerializer, responses=_detail_ok())
    @action(detail=True, methods=["put"], url_path="deadlines")
    def deadlines(self, request: Request, pk: str) -> Response:
        kwargs, problem = self._body(UpdateCompetitionDeadlinesSerializer, request)
        if problem is not None:
            return problem
        assert kwargs is not None
        return self._run(UpdateCompetitionDeadlinesHandler, UpdateDeadlinesCommand(competition_id=pk, **kwargs), request)

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    @extend_schema(tags=[_TAG], operation_id="markCompetitionConfigured", request=None, responses=_detail_ok())
    @action(detail=True, methods=["post"], url_path="configured")
    def mark_configured(self, request: Request, pk: str) -> Response:
        return self._run(MarkCompetitionConfiguredHandler, MarkConfiguredCommand(competition_id=pk), request)

    @extend_schema(tags=[_TAG], operation_id="revertCompetitionToDraft", request=None, responses=_detail_ok())
    @action(detail=True, methods=["post"], url_path="revert-to-draft")
    def revert_to_draft(self, request: Request, pk: str) -> Response:
        return self._run(RevertCompetitionToDraftHandler, RevertToDraftCommand(competition_id=pk), request)

    @extend_schema(tags=[_TAG], operation_id="markCompetitionReady", request=None, responses=_detail_ok())
    @action(detail=True, methods=["post"], url_path="ready")
    def mark_ready(self, request: Request, pk: str) -> Response:
        return self._run(MarkCompetitionReadyHandler, MarkReadyCommand(competition_id=pk), request)

    @extend_schema(tags=[_TAG], operation_id="revertCompetitionToConfigured", request=None, responses=_detail_ok())
    @action(detail=True, methods=["post"], url_path="revert-to-configured")
    def revert_to_configured(self, request: Request, pk: str) -> Response:
        return self._run(RevertCompetitionToConfiguredHandler, RevertToConfiguredCommand(competition_id=pk), request)

    @extend_schema(tags=[_TAG], operation_id="publishCompetition", request=None, responses=_detail_ok())
    @action(detail=True, methods=["post"], url_path="publish")
    def publish(self, request: Request, pk: str) -> Response:
        return self._run(PublishCompetitionHandler, PublishCompetitionCommand(competition_id=pk), request)

    @extend_schema(tags=[_TAG], operation_id="openRegistration", request=None, responses=_detail_ok())
    @action(detail=True, methods=["post"], url_path="registration/open")
    def open_registration(self, request: Request, pk: str) -> Response:
        return self._run(OpenRegistrationHandler, OpenRegistrationCommand(competition_id=pk), request)

    @extend_schema(tags=[_TAG], operation_id="closeRegistration", request=None, responses=_detail_ok())
    @action(detail=True, methods=["post"], url_path="registration/close")
    def close_registration(self, request: Request, pk: str) -> Response:
        return self._run(CloseRegistrationHandler, CloseRegistrationCommand(competition_id=pk), request)

    @extend_schema(tags=[_TAG], operation_id="startCompetition", request=None, responses=_detail_ok())
    @action(detail=True, methods=["post"], url_path="start")
    def start(self, request: Request, pk: str) -> Response:
        return self._run(StartCompetitionHandler, StartCompetitionCommand(competition_id=pk), request)

    @extend_schema(tags=[_TAG], operation_id="completeCompetition", request=None, responses=_detail_ok())
    @action(detail=True, methods=["post"], url_path="complete")
    def complete(self, request: Request, pk: str) -> Response:
        return self._run(CompleteCompetitionHandler, CompleteCompetitionCommand(competition_id=pk), request)

    @extend_schema(tags=[_TAG], operation_id="archiveCompetition", request=None, responses=_detail_ok())
    @action(detail=True, methods=["post"], url_path="archive")
    def archive(self, request: Request, pk: str) -> Response:
        return self._run(ArchiveCompetitionHandler, ArchiveCompetitionCommand(competition_id=pk), request)

    # ------------------------------------------------------------------
    # Categories
    # ------------------------------------------------------------------

    @extend_schema(tags=[_TAG], operation_id="addCategory", request=AddCategorySerializer, responses=_detail_ok(status.HTTP_201_CREATED))
    @action(detail=True, methods=["post"], url_path="categories")
    def categories(self, request: Request, pk: str) -> Response:
        kwargs, problem = self._body(AddCategorySerializer, request)
        if problem is not None:
            return problem
        assert kwargs is not None
        return self._run(AddCategoryHandler, AddCategoryCommand(competition_id=pk, **kwargs), request, success=status.HTTP_201_CREATED)

    @extend_schema(methods=["PATCH"], tags=[_TAG], operation_id="renameCategory", request=RenameCategorySerializer, responses=_detail_ok())
    @extend_schema(methods=["DELETE"], tags=[_TAG], operation_id="removeCategory", request=None, responses=_detail_ok())
    @action(detail=True, methods=["patch", "delete"], url_path=r"categories/(?P<category_id>[^/.]+)")
    def category_detail(self, request: Request, pk: str, category_id: str) -> Response:
        if request.method == "DELETE":
            return self._run(RemoveCategoryHandler, RemoveCategoryCommand(competition_id=pk, category_id=category_id), request)
        kwargs, problem = self._body(RenameCategorySerializer, request)
        if problem is not None:
            return problem
        assert kwargs is not None
        return self._run(RenameCategoryHandler, RenameCategoryCommand(competition_id=pk, category_id=category_id, **kwargs), request)

    # ------------------------------------------------------------------
    # Disciplines
    # ------------------------------------------------------------------

    @extend_schema(tags=[_TAG], operation_id="addDiscipline", request=AddDisciplineSerializer, responses=_detail_ok(status.HTTP_201_CREATED))
    @action(detail=True, methods=["post"], url_path="disciplines")
    def disciplines(self, request: Request, pk: str) -> Response:
        kwargs, problem = self._body(AddDisciplineSerializer, request)
        if problem is not None:
            return problem
        assert kwargs is not None
        return self._run(AddDisciplineHandler, AddDisciplineCommand(competition_id=pk, **kwargs), request, success=status.HTTP_201_CREATED)

    @extend_schema(methods=["PATCH"], tags=[_TAG], operation_id="renameDiscipline", request=RenameDisciplineSerializer, responses=_detail_ok())
    @extend_schema(methods=["DELETE"], tags=[_TAG], operation_id="removeDiscipline", request=None, responses=_detail_ok())
    @action(detail=True, methods=["patch", "delete"], url_path=r"disciplines/(?P<discipline_id>[^/.]+)")
    def discipline_detail(self, request: Request, pk: str, discipline_id: str) -> Response:
        if request.method == "DELETE":
            return self._run(RemoveDisciplineHandler, RemoveDisciplineCommand(competition_id=pk, discipline_id=discipline_id), request)
        kwargs, problem = self._body(RenameDisciplineSerializer, request)
        if problem is not None:
            return problem
        assert kwargs is not None
        return self._run(RenameDisciplineHandler, RenameDisciplineCommand(competition_id=pk, discipline_id=discipline_id, **kwargs), request)

    # ------------------------------------------------------------------
    # Age categories
    # ------------------------------------------------------------------

    @extend_schema(tags=[_TAG], operation_id="addAgeCategory", request=AddAgeCategorySerializer, responses=_detail_ok(status.HTTP_201_CREATED))
    @action(detail=True, methods=["post"], url_path="age-categories")
    def age_categories(self, request: Request, pk: str) -> Response:
        kwargs, problem = self._body(AddAgeCategorySerializer, request)
        if problem is not None:
            return problem
        assert kwargs is not None
        return self._run(AddAgeCategoryHandler, AddAgeCategoryCommand(competition_id=pk, **kwargs), request, success=status.HTTP_201_CREATED)

    @extend_schema(tags=[_TAG], operation_id="removeAgeCategory", request=None, responses=_detail_ok())
    @action(detail=True, methods=["delete"], url_path=r"age-categories/(?P<age_category_id>[^/.]+)")
    def age_category_detail(self, request: Request, pk: str, age_category_id: str) -> Response:
        return self._run(RemoveAgeCategoryHandler, RemoveAgeCategoryCommand(competition_id=pk, age_category_id=age_category_id), request)

    # ------------------------------------------------------------------
    # Participant groups
    # ------------------------------------------------------------------

    @extend_schema(
        tags=[_TAG], operation_id="addParticipantGroup", request=AddParticipantGroupSerializer, responses=_detail_ok(status.HTTP_201_CREATED)
    )
    @action(detail=True, methods=["post"], url_path="participant-groups")
    def participant_groups(self, request: Request, pk: str) -> Response:
        kwargs, problem = self._body(AddParticipantGroupSerializer, request)
        if problem is not None:
            return problem
        assert kwargs is not None
        return self._run(
            AddParticipantGroupHandler, AddParticipantGroupCommand(competition_id=pk, **kwargs), request, success=status.HTTP_201_CREATED
        )

    @extend_schema(tags=[_TAG], operation_id="removeParticipantGroup", request=None, responses=_detail_ok())
    @action(detail=True, methods=["delete"], url_path=r"participant-groups/(?P<participant_group_id>[^/.]+)")
    def participant_group_detail(self, request: Request, pk: str, participant_group_id: str) -> Response:
        return self._run(
            RemoveParticipantGroupHandler, RemoveParticipantGroupCommand(competition_id=pk, participant_group_id=participant_group_id), request
        )

    # ------------------------------------------------------------------
    # Participation formats
    # ------------------------------------------------------------------

    @extend_schema(
        tags=[_TAG], operation_id="enableParticipationFormat", request=ParticipationFormatSerializer, responses=_detail_ok(status.HTTP_201_CREATED)
    )
    @action(detail=True, methods=["post"], url_path="participation-formats")
    def participation_formats(self, request: Request, pk: str) -> Response:
        kwargs, problem = self._body(ParticipationFormatSerializer, request)
        if problem is not None:
            return problem
        assert kwargs is not None
        return self._run(EnableFormatHandler, EnableFormatCommand(competition_id=pk, **kwargs), request, success=status.HTTP_201_CREATED)

    @extend_schema(tags=[_TAG], operation_id="disableParticipationFormat", request=None, responses=_detail_ok())
    @action(detail=True, methods=["delete"], url_path=r"participation-formats/(?P<participation_format>[^/.]+)")
    def participation_format_detail(self, request: Request, pk: str, participation_format: str) -> Response:
        return self._run(DisableFormatHandler, DisableFormatCommand(competition_id=pk, participation_format=participation_format), request)

    # ------------------------------------------------------------------
    # Admission rules
    # ------------------------------------------------------------------

    @extend_schema(tags=[_TAG], operation_id="addAdmissionRule", request=AddAdmissionRuleSerializer, responses=_detail_ok(status.HTTP_201_CREATED))
    @action(detail=True, methods=["post"], url_path="admission-rules")
    def admission_rules(self, request: Request, pk: str) -> Response:
        kwargs, problem = self._body(AddAdmissionRuleSerializer, request)
        if problem is not None:
            return problem
        assert kwargs is not None
        return self._run(AddAdmissionRuleHandler, AddAdmissionRuleCommand(competition_id=pk, **kwargs), request, success=status.HTTP_201_CREATED)

    @extend_schema(tags=[_TAG], operation_id="removeAdmissionRule", request=_AdmissionCombinationSerializer, responses=_detail_ok())
    @action(detail=True, methods=["post"], url_path="admission-rules/remove")
    def remove_admission_rule(self, request: Request, pk: str) -> Response:
        kwargs, problem = self._body(_AdmissionCombinationSerializer, request)
        if problem is not None:
            return problem
        assert kwargs is not None
        return self._run(RemoveAdmissionRuleHandler, RemoveAdmissionRuleCommand(competition_id=pk, **kwargs), request)

    # ------------------------------------------------------------------
    # Pricing rules
    # ------------------------------------------------------------------

    @extend_schema(
        methods=["POST"], tags=[_TAG], operation_id="addPricingRule", request=AddPricingRuleSerializer, responses=_detail_ok(status.HTTP_201_CREATED)
    )
    @extend_schema(methods=["PATCH"], tags=[_TAG], operation_id="changePrice", request=ChangePriceSerializer, responses=_detail_ok())
    @action(detail=True, methods=["post", "patch"], url_path="pricing-rules")
    def pricing_rules(self, request: Request, pk: str) -> Response:
        if request.method == "PATCH":
            kwargs, problem = self._body(ChangePriceSerializer, request)
            if problem is not None:
                return problem
            assert kwargs is not None
            return self._run(ChangePriceHandler, ChangePriceCommand(competition_id=pk, **kwargs), request)
        kwargs, problem = self._body(AddPricingRuleSerializer, request)
        if problem is not None:
            return problem
        assert kwargs is not None
        return self._run(AddPricingRuleHandler, AddPricingRuleCommand(competition_id=pk, **kwargs), request, success=status.HTTP_201_CREATED)

    @extend_schema(tags=[_TAG], operation_id="removePricingRule", request=_AdmissionCombinationSerializer, responses=_detail_ok())
    @action(detail=True, methods=["post"], url_path="pricing-rules/remove")
    def remove_pricing_rule(self, request: Request, pk: str) -> Response:
        kwargs, problem = self._body(_AdmissionCombinationSerializer, request)
        if problem is not None:
            return problem
        assert kwargs is not None
        return self._run(RemovePricingRuleHandler, RemovePricingRuleCommand(competition_id=pk, **kwargs), request)

    # ------------------------------------------------------------------
    # Regulations
    # ------------------------------------------------------------------

    @extend_schema(
        tags=[_TAG],
        operation_id="uploadRegulationFile",
        request={
            "multipart/form-data": {
                "type": "object",
                "properties": {"file": {"type": "string", "format": "binary"}},
                "required": ["file"],
            }
        },
        responses={
            200: OpenApiResponse(description="PDF uploaded; body contains data.fileReference."),
            400: OpenApiResponse(ProblemDetailSerializer, description="Validation failed."),
            403: OpenApiResponse(ProblemDetailSerializer, description="Not organization staff."),
            404: OpenApiResponse(ProblemDetailSerializer, description="Competition or element not found."),
        },
    )
    @action(
        detail=True,
        methods=["post"],
        # Outside `regulations/<id>` so the delete route cannot claim this path.
        url_path="uploads/regulation",
        parser_classes=[MultiPartParser, FormParser],
    )
    def upload_regulation_file(self, request: Request, pk: str) -> Response:
        """Upload a regulation PDF and return a media file reference for drafting."""
        # Ensure the competition exists before accepting an orphan upload.
        try:
            build_get_competition_handler().handle(GetCompetitionQuery(competition_id=pk))
        except (ApplicationError, CompetitionDomainError) as exc:
            return competition_problem(exc, instance=request.path, request=request)

        uploaded = request.FILES.get("file")
        if uploaded is None:
            return validation_problem(
                {"file": ["Выберите PDF-файл положения."]},
                instance=request.path,
                request=request,
            )

        content_type = (uploaded.content_type or "").lower()
        if content_type not in {"application/pdf"}:
            return validation_problem(
                {"file": ["Допустим только PDF."]},
                instance=request.path,
                request=request,
            )

        if uploaded.size > 20 * 1024 * 1024:
            return validation_problem(
                {"file": ["Размер файла не должен превышать 20 МБ."]},
                instance=request.path,
                request=request,
            )

        relative_path = default_storage.save(
            f"competitions/{pk}/regulations/{uuid.uuid4().hex}.pdf",
            uploaded,
        )
        file_reference = f"/{settings.MEDIA_URL.strip('/')}/{relative_path}"
        correlation_id = request_id(request)
        return Response(
            {
                "data": {"fileReference": file_reference},
                "meta": {"requestId": correlation_id},
            },
            status=status.HTTP_200_OK,
            headers={"X-Request-ID": correlation_id},
        )

    @extend_schema(tags=[_TAG], operation_id="addRegulation", request=AddRegulationSerializer, responses=_detail_ok(status.HTTP_201_CREATED))
    @action(detail=True, methods=["post"], url_path="regulations")
    def regulations(self, request: Request, pk: str) -> Response:
        kwargs, problem = self._body(AddRegulationSerializer, request)
        if problem is not None:
            return problem
        assert kwargs is not None
        return self._run(AddRegulationHandler, AddRegulationCommand(competition_id=pk, **kwargs), request, success=status.HTTP_201_CREATED)

    @extend_schema(tags=[_TAG], operation_id="makeRegulationCurrent", request=None, responses=_detail_ok())
    @action(detail=True, methods=["post"], url_path=r"regulations/(?P<regulation_id>[^/.]+)/current")
    def make_regulation_current(self, request: Request, pk: str, regulation_id: str) -> Response:
        return self._run(MakeRegulationCurrentHandler, MakeRegulationCurrentCommand(competition_id=pk, regulation_id=regulation_id), request)

    @extend_schema(tags=[_TAG], operation_id="removeRegulation", request=None, responses=_detail_ok())
    @action(detail=True, methods=["delete"], url_path=r"regulations/(?P<regulation_id>[^/.]+)")
    def regulation_detail(self, request: Request, pk: str, regulation_id: str) -> Response:
        return self._run(RemoveRegulationHandler, RemoveRegulationCommand(competition_id=pk, regulation_id=regulation_id), request)

    # ------------------------------------------------------------------
    # Documents
    # ------------------------------------------------------------------

    @extend_schema(tags=[_TAG], operation_id="addDocument", request=AddDocumentSerializer, responses=_detail_ok(status.HTTP_201_CREATED))
    @action(detail=True, methods=["post"], url_path="documents")
    def documents(self, request: Request, pk: str) -> Response:
        kwargs, problem = self._body(AddDocumentSerializer, request)
        if problem is not None:
            return problem
        assert kwargs is not None
        return self._run(AddDocumentHandler, AddDocumentCommand(competition_id=pk, **kwargs), request, success=status.HTTP_201_CREATED)

    @extend_schema(methods=["PATCH"], tags=[_TAG], operation_id="updateDocument", request=UpdateDocumentSerializer, responses=_detail_ok())
    @extend_schema(methods=["DELETE"], tags=[_TAG], operation_id="removeDocument", request=None, responses=_detail_ok())
    @action(detail=True, methods=["patch", "delete"], url_path=r"documents/(?P<document_id>[^/.]+)")
    def document_detail(self, request: Request, pk: str, document_id: str) -> Response:
        if request.method == "DELETE":
            return self._run(RemoveDocumentHandler, RemoveDocumentCommand(competition_id=pk, document_id=document_id), request)
        kwargs, problem = self._body(UpdateDocumentSerializer, request)
        if problem is not None:
            return problem
        assert kwargs is not None
        return self._run(UpdateDocumentHandler, UpdateDocumentCommand(competition_id=pk, document_id=document_id, **kwargs), request)

    @extend_schema(tags=[_TAG], operation_id="publishDocument", request=None, responses=_detail_ok())
    @action(detail=True, methods=["post"], url_path=r"documents/(?P<document_id>[^/.]+)/publish")
    def publish_document(self, request: Request, pk: str, document_id: str) -> Response:
        return self._run(PublishDocumentHandler, PublishDocumentCommand(competition_id=pk, document_id=document_id), request)

    @extend_schema(tags=[_TAG], operation_id="unpublishDocument", request=None, responses=_detail_ok())
    @action(detail=True, methods=["post"], url_path=r"documents/(?P<document_id>[^/.]+)/unpublish")
    def unpublish_document(self, request: Request, pk: str, document_id: str) -> Response:
        return self._run(UnpublishDocumentHandler, UnpublishDocumentCommand(competition_id=pk, document_id=document_id), request)

    # ------------------------------------------------------------------
    # Additional services
    # ------------------------------------------------------------------

    @extend_schema(
        tags=[_TAG], operation_id="addAdditionalService", request=AddAdditionalServiceSerializer, responses=_detail_ok(status.HTTP_201_CREATED)
    )
    @action(detail=True, methods=["post"], url_path="services")
    def services(self, request: Request, pk: str) -> Response:
        kwargs, problem = self._body(AddAdditionalServiceSerializer, request)
        if problem is not None:
            return problem
        assert kwargs is not None
        return self._run(
            AddAdditionalServiceHandler, AddAdditionalServiceCommand(competition_id=pk, **kwargs), request, success=status.HTTP_201_CREATED
        )

    @extend_schema(
        methods=["PATCH"], tags=[_TAG], operation_id="updateAdditionalService", request=UpdateAdditionalServiceSerializer, responses=_detail_ok()
    )
    @extend_schema(methods=["DELETE"], tags=[_TAG], operation_id="removeAdditionalService", request=None, responses=_detail_ok())
    @action(detail=True, methods=["patch", "delete"], url_path=r"services/(?P<service_id>[^/.]+)")
    def service_detail(self, request: Request, pk: str, service_id: str) -> Response:
        if request.method == "DELETE":
            return self._run(RemoveAdditionalServiceHandler, RemoveAdditionalServiceCommand(competition_id=pk, service_id=service_id), request)
        kwargs, problem = self._body(UpdateAdditionalServiceSerializer, request)
        if problem is not None:
            return problem
        assert kwargs is not None
        return self._run(UpdateAdditionalServiceHandler, UpdateAdditionalServiceCommand(competition_id=pk, service_id=service_id, **kwargs), request)

    @extend_schema(tags=[_TAG], operation_id="enableAdditionalService", request=None, responses=_detail_ok())
    @action(detail=True, methods=["post"], url_path=r"services/(?P<service_id>[^/.]+)/enable")
    def enable_service(self, request: Request, pk: str, service_id: str) -> Response:
        return self._run(EnableAdditionalServiceHandler, EnableAdditionalServiceCommand(competition_id=pk, service_id=service_id), request)

    @extend_schema(tags=[_TAG], operation_id="disableAdditionalService", request=None, responses=_detail_ok())
    @action(detail=True, methods=["post"], url_path=r"services/(?P<service_id>[^/.]+)/disable")
    def disable_service(self, request: Request, pk: str, service_id: str) -> Response:
        return self._run(DisableAdditionalServiceHandler, DisableAdditionalServiceCommand(competition_id=pk, service_id=service_id), request)

    # ------------------------------------------------------------------
    # Contacts
    # ------------------------------------------------------------------

    @extend_schema(tags=[_TAG], operation_id="addContact", request=AddContactSerializer, responses=_detail_ok(status.HTTP_201_CREATED))
    @action(detail=True, methods=["post"], url_path="contacts")
    def contacts(self, request: Request, pk: str) -> Response:
        kwargs, problem = self._body(AddContactSerializer, request)
        if problem is not None:
            return problem
        assert kwargs is not None
        return self._run(AddContactHandler, AddContactCommand(competition_id=pk, **kwargs), request, success=status.HTTP_201_CREATED)

    @extend_schema(tags=[_TAG], operation_id="setPrimaryContact", request=None, responses=_detail_ok())
    @action(detail=True, methods=["post"], url_path=r"contacts/(?P<contact_id>[^/.]+)/primary")
    def set_primary_contact(self, request: Request, pk: str, contact_id: str) -> Response:
        return self._run(SetPrimaryContactHandler, SetPrimaryContactCommand(competition_id=pk, contact_id=contact_id), request)

    @extend_schema(tags=[_TAG], operation_id="removeContact", request=None, responses=_detail_ok())
    @action(detail=True, methods=["delete"], url_path=r"contacts/(?P<contact_id>[^/.]+)")
    def contact_detail(self, request: Request, pk: str, contact_id: str) -> Response:
        return self._run(RemoveContactHandler, RemoveContactCommand(competition_id=pk, contact_id=contact_id), request)

    # ------------------------------------------------------------------
    # Public information blocks
    # ------------------------------------------------------------------

    @extend_schema(
        tags=[_TAG], operation_id="addInformationBlock", request=AddInformationBlockSerializer, responses=_detail_ok(status.HTTP_201_CREATED)
    )
    @action(detail=True, methods=["post"], url_path="information-blocks")
    def information_blocks(self, request: Request, pk: str) -> Response:
        kwargs, problem = self._body(AddInformationBlockSerializer, request)
        if problem is not None:
            return problem
        assert kwargs is not None
        return self._run(
            AddInformationBlockHandler, AddInformationBlockCommand(competition_id=pk, **kwargs), request, success=status.HTTP_201_CREATED
        )

    @extend_schema(
        methods=["PATCH"], tags=[_TAG], operation_id="updateInformationBlock", request=UpdateInformationBlockSerializer, responses=_detail_ok()
    )
    @extend_schema(methods=["DELETE"], tags=[_TAG], operation_id="removeInformationBlock", request=None, responses=_detail_ok())
    @action(detail=True, methods=["patch", "delete"], url_path=r"information-blocks/(?P<block_id>[^/.]+)")
    def information_block_detail(self, request: Request, pk: str, block_id: str) -> Response:
        if request.method == "DELETE":
            return self._run(RemoveInformationBlockHandler, RemoveInformationBlockCommand(competition_id=pk, block_id=block_id), request)
        kwargs, problem = self._body(UpdateInformationBlockSerializer, request)
        if problem is not None:
            return problem
        assert kwargs is not None
        return self._run(UpdateInformationBlockHandler, UpdateInformationBlockCommand(competition_id=pk, block_id=block_id, **kwargs), request)

    @extend_schema(tags=[_TAG], operation_id="publishInformationBlock", request=None, responses=_detail_ok())
    @action(detail=True, methods=["post"], url_path=r"information-blocks/(?P<block_id>[^/.]+)/publish")
    def publish_information_block(self, request: Request, pk: str, block_id: str) -> Response:
        return self._run(PublishInformationBlockHandler, PublishInformationBlockCommand(competition_id=pk, block_id=block_id), request)

    @extend_schema(tags=[_TAG], operation_id="hideInformationBlock", request=None, responses=_detail_ok())
    @action(detail=True, methods=["post"], url_path=r"information-blocks/(?P<block_id>[^/.]+)/hide")
    def hide_information_block(self, request: Request, pk: str, block_id: str) -> Response:
        return self._run(HideInformationBlockHandler, HideInformationBlockCommand(competition_id=pk, block_id=block_id), request)
