"""REST API for Competition management."""

from __future__ import annotations

from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.competitions.application.dto.commands import (
    ArchiveCompetitionCommand,
    CloseRegistrationCommand,
    CreateCompetitionCommand,
    OpenRegistrationCommand,
    PublishCompetitionCommand,
    UpdateCompetitionGeneralInformationCommand,
)
from apps.competitions.application.dto.queries import (
    GetCompetitionQuery,
    ListCompetitionsQuery,
)
from apps.competitions.application.handlers import (
    ArchiveCompetitionHandler,
    CloseRegistrationHandler,
    CreateCompetitionHandler,
    GetCompetitionHandler,
    ListCompetitionsHandler,
    OpenRegistrationHandler,
    PublishCompetitionHandler,
    UpdateCompetitionGeneralInformationHandler,
)

from .serializers import (
    CreateCompetitionSerializer,
    PublishCompetitionSerializer,
    UpdateCompetitionGeneralInformationSerializer,
)

from apps.competitions.application.dto.commands import (
    AddCategoryCommand,
    RenameCategoryCommand,
    RemoveCategoryCommand,
    AddDisciplineCommand,
    RenameDisciplineCommand,
    RemoveDisciplineCommand,
)

from apps.competitions.application.handlers import (
    AddCategoryHandler,
    RenameCategoryHandler,
    RemoveCategoryHandler,
    AddDisciplineHandler,
    RenameDisciplineHandler,
    RemoveDisciplineHandler,
)

from .serializers import (
    AddCategorySerializer,
    RenameCategorySerializer,
    AddDisciplineSerializer,
    RenameDisciplineSerializer,
)

from apps.competitions.application.dto.commands import (
    AddAgeCategoryCommand,
    RemoveAgeCategoryCommand,
    AddParticipantGroupCommand,
    RemoveParticipantGroupCommand,
    EnableFormatCommand,
    DisableFormatCommand,
)

from apps.competitions.application.handlers import (
    AddAgeCategoryHandler,
    RemoveAgeCategoryHandler,
    AddParticipantGroupHandler,
    RemoveParticipantGroupHandler,
    EnableFormatHandler,
    DisableFormatHandler,
)

from .serializers import (
    AddAgeCategorySerializer,
    AddParticipantGroupSerializer,
    EnableParticipationFormatSerializer,
    DisableParticipationFormatSerializer,
)

from apps.competitions.application.dto.commands import (
    AddAdmissionRuleCommand,
    RemoveAdmissionRuleCommand,
    AddPricingRuleCommand,
    ChangePriceCommand,
    RemovePricingRuleCommand,
)

from apps.competitions.application.handlers import (
    AddAdmissionRuleHandler,
    RemoveAdmissionRuleHandler,
    AddPricingRuleHandler,
    ChangePriceHandler,
    RemovePricingRuleHandler,
)

from .serializers import (
    AddAdmissionRuleSerializer,
    AddPricingRuleSerializer,
    ChangePriceSerializer,
    RemoveAdmissionRuleSerializer,
    RemovePricingRuleSerializer,
)

from apps.competitions.application.dto.commands import (
    AddRegulationCommand,
    MakeRegulationCurrentCommand,
    RemoveRegulationCommand,
    AddDocumentCommand,
    UpdateDocumentCommand,
    PublishDocumentCommand,
    UnpublishDocumentCommand,
    RemoveDocumentCommand,
)

from apps.competitions.application.handlers import (
    AddRegulationHandler,
    MakeRegulationCurrentHandler,
    RemoveRegulationHandler,
    AddDocumentHandler,
    UpdateDocumentHandler,
    PublishDocumentHandler,
    UnpublishDocumentHandler,
    RemoveDocumentHandler,
)

from .serializers import (
    AddRegulationSerializer,
    AddDocumentSerializer,
    UpdateDocumentSerializer,
    PublishDocumentSerializer,
    UnpublishDocumentSerializer,
)

from apps.competitions.application.dto.commands import (
    AddAdditionalServiceCommand,
    UpdateAdditionalServiceCommand,
    EnableAdditionalServiceCommand,
    DisableAdditionalServiceCommand,
    RemoveAdditionalServiceCommand,
    AddContactCommand,
    SetPrimaryContactCommand,
    RemoveContactCommand,
    AddInformationBlockCommand,
    UpdateInformationBlockCommand,
    PublishInformationBlockCommand,
    HideInformationBlockCommand,
    RemoveInformationBlockCommand,
)

from apps.competitions.application.handlers import (
    AddAdditionalServiceHandler,
    UpdateAdditionalServiceHandler,
    EnableAdditionalServiceHandler,
    DisableAdditionalServiceHandler,
    RemoveAdditionalServiceHandler,
    AddContactHandler,
    SetPrimaryContactHandler,
    RemoveContactHandler,
    AddInformationBlockHandler,
    UpdateInformationBlockHandler,
    PublishInformationBlockHandler,
    HideInformationBlockHandler,
    RemoveInformationBlockHandler,
)

from .serializers import (
    AddAdditionalServiceSerializer,
    UpdateAdditionalServiceSerializer,
    AddContactSerializer,
    AddInformationBlockSerializer,
    UpdateInformationBlockSerializer,
)

__all__ = [
    "CompetitionViewSet",
]


class CompetitionViewSet(viewsets.ViewSet):
    """Organizer Competition API."""

    create_handler: CreateCompetitionHandler
    list_handler: ListCompetitionsHandler
    retrieve_handler: GetCompetitionHandler
    update_handler: UpdateCompetitionGeneralInformationHandler

    publish_handler: PublishCompetitionHandler
    open_registration_handler: OpenRegistrationHandler
    close_registration_handler: CloseRegistrationHandler
    archive_handler: ArchiveCompetitionHandler

    add_category_handler: AddCategoryHandler
    rename_category_handler: RenameCategoryHandler
    remove_category_handler: RemoveCategoryHandler

    add_discipline_handler: AddDisciplineHandler
    rename_discipline_handler: RenameDisciplineHandler
    remove_discipline_handler: RemoveDisciplineHandler

    add_age_category_handler: AddAgeCategoryHandler
    remove_age_category_handler: RemoveAgeCategoryHandler

    add_participant_group_handler: AddParticipantGroupHandler
    remove_participant_group_handler: RemoveParticipantGroupHandler

    enable_format_handler: EnableFormatHandler
    disable_format_handler: DisableFormatHandler

    add_admission_rule_handler: AddAdmissionRuleHandler
    remove_admission_rule_handler: RemoveAdmissionRuleHandler

    add_pricing_rule_handler: AddPricingRuleHandler
    change_price_handler: ChangePriceHandler
    remove_pricing_rule_handler: RemovePricingRuleHandler

    add_regulation_handler: AddRegulationHandler
    make_regulation_current_handler: MakeRegulationCurrentHandler
    remove_regulation_handler: RemoveRegulationHandler

    add_document_handler: AddDocumentHandler
    update_document_handler: UpdateDocumentHandler
    publish_document_handler: PublishDocumentHandler
    unpublish_document_handler: UnpublishDocumentHandler
    remove_document_handler: RemoveDocumentHandler

    add_service_handler: AddAdditionalServiceHandler
    update_service_handler: UpdateAdditionalServiceHandler
    enable_service_handler: EnableAdditionalServiceHandler
    disable_service_handler: DisableAdditionalServiceHandler
    remove_service_handler: RemoveAdditionalServiceHandler

    add_contact_handler: AddContactHandler
    set_primary_contact_handler: SetPrimaryContactHandler
    remove_contact_handler: RemoveContactHandler

    add_information_block_handler: AddInformationBlockHandler
    update_information_block_handler: UpdateInformationBlockHandler
    publish_information_block_handler: PublishInformationBlockHandler
    hide_information_block_handler: HideInformationBlockHandler
    remove_information_block_handler: RemoveInformationBlockHandler

    # ------------------------------------------------------------------
    # CRUD
    # ------------------------------------------------------------------

    def list(self, request):
        """GET /competitions"""

        result = self.list_handler.handle(
            ListCompetitionsQuery(
                season=request.query_params.get("season"),
            )
        )

        return Response(
            result,
            status=status.HTTP_200_OK,
        )

    def retrieve(self, request, pk: str):
        """GET /competitions/{id}"""

        result = self.retrieve_handler.handle(
            GetCompetitionQuery(
                competition_id=pk,
            )
        )

        return Response(
            result,
            status=status.HTTP_200_OK,
        )

    def create(self, request):
        """POST /competitions"""

        serializer = CreateCompetitionSerializer(
            data=request.data,
        )

        serializer.is_valid(
            raise_exception=True,
        )

        result = self.create_handler.handle(
            CreateCompetitionCommand(
                **serializer.validated_data,
            )
        )

        return Response(
            result,
            status=status.HTTP_201_CREATED,
        )

    def partial_update(self, request, pk: str):
        """PATCH /competitions/{id}"""

        serializer = UpdateCompetitionGeneralInformationSerializer(
            data=request.data,
        )

        serializer.is_valid(
            raise_exception=True,
        )

        result = self.update_handler.handle(
            UpdateCompetitionGeneralInformationCommand(
                competition_id=pk,
                **serializer.validated_data,
            )
        )

        return Response(
            result,
            status=status.HTTP_200_OK,
        )
    
    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    @action(
        detail=True,
        methods=["post"],
        url_path="publish",
    )
    def publish(self, request, pk: str):
        """POST /competitions/{id}/publish"""

        PublishCompetitionSerializer(
            data=request.data,
        ).is_valid(
            raise_exception=True,
        )

        result = self.publish_handler.handle(
            PublishCompetitionCommand(
                competition_id=pk,
            )
        )

        return Response(
            result,
            status=status.HTTP_200_OK,
        )

    @action(
        detail=True,
        methods=["post"],
        url_path="registration/open",
    )
    def open_registration(self, request, pk: str):
        """POST /competitions/{id}/registration/open"""

        result = self.open_registration_handler.handle(
            OpenRegistrationCommand(
                competition_id=pk,
            )
        )

        return Response(
            result,
            status=status.HTTP_200_OK,
        )

    @action(
        detail=True,
        methods=["post"],
        url_path="registration/close",
    )
    def close_registration(self, request, pk: str):
        """POST /competitions/{id}/registration/close"""

        result = self.close_registration_handler.handle(
            CloseRegistrationCommand(
                competition_id=pk,
            )
        )

        return Response(
            result,
            status=status.HTTP_200_OK,
        )

    @action(
        detail=True,
        methods=["post"],
        url_path="archive",
    )
    def archive(self, request, pk: str):
        """POST /competitions/{id}/archive"""

        result = self.archive_handler.handle(
            ArchiveCompetitionCommand(
                competition_id=pk,
            )
        )

        return Response(
            result,
            status=status.HTTP_200_OK,
        )
    

        # ------------------------------------------------------------------
    # Categories
    # ------------------------------------------------------------------

    @action(
        detail=True,
        methods=["post"],
        url_path="categories",
    )
    def add_category(self, request, pk: str):
        serializer = AddCategorySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        result = self.add_category_handler.handle(
            AddCategoryCommand(
                competition_id=pk,
                **serializer.validated_data,
            )
        )

        return Response(result, status=status.HTTP_200_OK)

    @action(
        detail=True,
        methods=["patch"],
        url_path=r"categories/(?P<category_id>[^/.]+)",
    )
    def rename_category(self, request, pk: str, category_id: str):
        serializer = RenameCategorySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        result = self.rename_category_handler.handle(
            RenameCategoryCommand(
                competition_id=pk,
                category_id=category_id,
                **serializer.validated_data,
            )
        )

        return Response(result)

    @action(
        detail=True,
        methods=["delete"],
        url_path=r"categories/(?P<category_id>[^/.]+)",
    )
    def remove_category(self, request, pk: str, category_id: str):
        result = self.remove_category_handler.handle(
            RemoveCategoryCommand(
                competition_id=pk,
                category_id=category_id,
            )
        )

        return Response(result)
    
        # ------------------------------------------------------------------
    # Disciplines
    # ------------------------------------------------------------------

    @action(
        detail=True,
        methods=["post"],
        url_path="disciplines",
    )
    def add_discipline(self, request, pk: str):
        serializer = AddDisciplineSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        result = self.add_discipline_handler.handle(
            AddDisciplineCommand(
                competition_id=pk,
                **serializer.validated_data,
            )
        )

        return Response(result, status=status.HTTP_200_OK)

    @action(
        detail=True,
        methods=["patch"],
        url_path=r"disciplines/(?P<discipline_id>[^/.]+)",
    )
    def rename_discipline(self, request, pk: str, discipline_id: str):
        serializer = RenameDisciplineSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        result = self.rename_discipline_handler.handle(
            RenameDisciplineCommand(
                competition_id=pk,
                discipline_id=discipline_id,
                **serializer.validated_data,
            )
        )

        return Response(result)

    @action(
        detail=True,
        methods=["delete"],
        url_path=r"disciplines/(?P<discipline_id>[^/.]+)",
    )
    def remove_discipline(self, request, pk: str, discipline_id: str):
        result = self.remove_discipline_handler.handle(
            RemoveDisciplineCommand(
                competition_id=pk,
                discipline_id=discipline_id,
            )
        )

        return Response(result)
    
        # ------------------------------------------------------------------
    # Age Categories
    # ------------------------------------------------------------------

    @action(
        detail=True,
        methods=["post"],
        url_path="age-categories",
    )
    def add_age_category(self, request, pk: str):
        serializer = AddAgeCategorySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        result = self.add_age_category_handler.handle(
            AddAgeCategoryCommand(
                competition_id=pk,
                **serializer.validated_data,
            )
        )

        return Response(result, status=status.HTTP_200_OK)

    @action(
        detail=True,
        methods=["delete"],
        url_path=r"age-categories/(?P<age_category_id>[^/.]+)",
    )
    def remove_age_category(
        self,
        request,
        pk: str,
        age_category_id: str,
    ):
        result = self.remove_age_category_handler.handle(
            RemoveAgeCategoryCommand(
                competition_id=pk,
                age_category_id=age_category_id,
            )
        )

        return Response(result)
    
        # ------------------------------------------------------------------
    # Participant Groups
    # ------------------------------------------------------------------

    @action(
        detail=True,
        methods=["post"],
        url_path="participant-groups",
    )
    def add_participant_group(self, request, pk: str):
        serializer = AddParticipantGroupSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        result = self.add_participant_group_handler.handle(
            AddParticipantGroupCommand(
                competition_id=pk,
                **serializer.validated_data,
            )
        )

        return Response(result, status=status.HTTP_200_OK)

    @action(
        detail=True,
        methods=["delete"],
        url_path=r"participant-groups/(?P<participant_group_id>[^/.]+)",
    )
    def remove_participant_group(
        self,
        request,
        pk: str,
        participant_group_id: str,
    ):
        result = self.remove_participant_group_handler.handle(
            RemoveParticipantGroupCommand(
                competition_id=pk,
                participant_group_id=participant_group_id,
            )
        )

        return Response(result)
    
        # ------------------------------------------------------------------
    # Participation Formats
    # ------------------------------------------------------------------

    @action(
        detail=True,
        methods=["post"],
        url_path="participation-formats",
    )
    def enable_participation_format(self, request, pk: str):
        serializer = EnableParticipationFormatSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        result = self.enable_format_handler.handle(
            EnableFormatCommand(
                competition_id=pk,
                **serializer.validated_data,
            )
        )

        return Response(result)

    @action(
        detail=True,
        methods=["delete"],
        url_path="participation-formats",
    )
    def disable_participation_format(self, request, pk: str):
        serializer = DisableParticipationFormatSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        result = self.disable_format_handler.handle(
            DisableFormatCommand(
                competition_id=pk,
                **serializer.validated_data,
            )
        )

        return Response(result)
    
        # ------------------------------------------------------------------
    # Admission Rules
    # ------------------------------------------------------------------

    @action(
        detail=True,
        methods=["post"],
        url_path="admission-rules",
    )
    def add_admission_rule(self, request, pk: str):
        serializer = AddAdmissionRuleSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        result = self.add_admission_rule_handler.handle(
            AddAdmissionRuleCommand(
                competition_id=pk,
                **serializer.validated_data,
            )
        )

        return Response(result)

    @action(
        detail=True,
        methods=["delete"],
        url_path="admission-rules",
    )
    def remove_admission_rule(self, request, pk: str):
        serializer = RemoveAdmissionRuleSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        result = self.remove_admission_rule_handler.handle(
            RemoveAdmissionRuleCommand(
                competition_id=pk,
                **serializer.validated_data,
            )
        )

        return Response(result)
    
        # ------------------------------------------------------------------
    # Pricing Rules
    # ------------------------------------------------------------------

    @action(
        detail=True,
        methods=["post"],
        url_path="pricing-rules",
    )
    def add_pricing_rule(self, request, pk: str):
        serializer = AddPricingRuleSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        result = self.add_pricing_rule_handler.handle(
            AddPricingRuleCommand(
                competition_id=pk,
                **serializer.validated_data,
            )
        )

        return Response(result)

    @action(
        detail=True,
        methods=["patch"],
        url_path="pricing-rules",
    )
    def change_price(self, request, pk: str):
        serializer = ChangePriceSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        result = self.change_price_handler.handle(
            ChangePriceCommand(
                competition_id=pk,
                **serializer.validated_data,
            )
        )

        return Response(result)

    @action(
        detail=True,
        methods=["delete"],
        url_path="pricing-rules",
    )
    def remove_pricing_rule(self, request, pk: str):
        serializer = RemovePricingRuleSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        result = self.remove_pricing_rule_handler.handle(
            RemovePricingRuleCommand(
                competition_id=pk,
                **serializer.validated_data,
            )
        )

        return Response(result)
    
        # ------------------------------------------------------------------
    # Regulations
    # ------------------------------------------------------------------

    @action(detail=True, methods=["post"], url_path="regulations")
    def add_regulation(self, request, pk: str):
        serializer = AddRegulationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        result = self.add_regulation_handler.handle(
            AddRegulationCommand(
                competition_id=pk,
                **serializer.validated_data,
            )
        )

        return Response(result)

    @action(
        detail=True,
        methods=["post"],
        url_path=r"regulations/(?P<regulation_id>[^/.]+)/current",
    )
    def make_regulation_current(
        self,
        request,
        pk: str,
        regulation_id: str,
    ):
        result = self.make_regulation_current_handler.handle(
            MakeRegulationCurrentCommand(
                competition_id=pk,
                regulation_id=regulation_id,
            )
        )

        return Response(result)

    @action(
        detail=True,
        methods=["delete"],
        url_path=r"regulations/(?P<regulation_id>[^/.]+)",
    )
    def remove_regulation(
        self,
        request,
        pk: str,
        regulation_id: str,
    ):
        result = self.remove_regulation_handler.handle(
            RemoveRegulationCommand(
                competition_id=pk,
                regulation_id=regulation_id,
            )
        )

        return Response(result)
    

        # ------------------------------------------------------------------
    # Documents
    # ------------------------------------------------------------------

    @action(detail=True, methods=["post"], url_path="documents")
    def add_document(self, request, pk: str):
        serializer = AddDocumentSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        result = self.add_document_handler.handle(
            AddDocumentCommand(
                competition_id=pk,
                **serializer.validated_data,
            )
        )

        return Response(result)

    @action(
        detail=True,
        methods=["patch"],
        url_path=r"documents/(?P<document_id>[^/.]+)",
    )
    def update_document(
        self,
        request,
        pk: str,
        document_id: str,
    ):
        serializer = UpdateDocumentSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        result = self.update_document_handler.handle(
            UpdateDocumentCommand(
                competition_id=pk,
                document_id=document_id,
                **serializer.validated_data,
            )
        )

        return Response(result)

    @action(
        detail=True,
        methods=["post"],
        url_path=r"documents/(?P<document_id>[^/.]+)/publish",
    )
    def publish_document(
        self,
        request,
        pk: str,
        document_id: str,
    ):
        PublishDocumentSerializer(data=request.data).is_valid(
            raise_exception=True,
        )

        result = self.publish_document_handler.handle(
            PublishDocumentCommand(
                competition_id=pk,
                document_id=document_id,
            )
        )

        return Response(result)

    @action(
        detail=True,
        methods=["post"],
        url_path=r"documents/(?P<document_id>[^/.]+)/unpublish",
    )
    def unpublish_document(
        self,
        request,
        pk: str,
        document_id: str,
    ):
        UnpublishDocumentSerializer(data=request.data).is_valid(
            raise_exception=True,
        )

        result = self.unpublish_document_handler.handle(
            UnpublishDocumentCommand(
                competition_id=pk,
                document_id=document_id,
            )
        )

        return Response(result)

    @action(
        detail=True,
        methods=["delete"],
        url_path=r"documents/(?P<document_id>[^/.]+)",
    )
    def remove_document(
        self,
        request,
        pk: str,
        document_id: str,
    ):
        result = self.remove_document_handler.handle(
            RemoveDocumentCommand(
                competition_id=pk,
                document_id=document_id,
            )
        )

        return Response(result)


        # ------------------------------------------------------------------
    # Additional Services
    # ------------------------------------------------------------------

    @action(detail=True, methods=["post"], url_path="services")
    def add_service(self, request, pk: str):
        serializer = AddAdditionalServiceSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        result = self.add_service_handler.handle(
            AddAdditionalServiceCommand(
                competition_id=pk,
                **serializer.validated_data,
            )
        )

        return Response(result)

    @action(detail=True, methods=["patch"], url_path=r"services/(?P<service_id>[^/.]+)")
    def update_service(self, request, pk: str, service_id: str):
        serializer = UpdateAdditionalServiceSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        result = self.update_service_handler.handle(
            UpdateAdditionalServiceCommand(
                competition_id=pk,
                service_id=service_id,
                **serializer.validated_data,
            )
        )

        return Response(result)

    @action(detail=True, methods=["post"], url_path=r"services/(?P<service_id>[^/.]+)/enable")
    def enable_service(self, request, pk: str, service_id: str):
        return Response(
            self.enable_service_handler.handle(
                EnableAdditionalServiceCommand(
                    competition_id=pk,
                    service_id=service_id,
                )
            )
        )

    @action(detail=True, methods=["post"], url_path=r"services/(?P<service_id>[^/.]+)/disable")
    def disable_service(self, request, pk: str, service_id: str):
        return Response(
            self.disable_service_handler.handle(
                DisableAdditionalServiceCommand(
                    competition_id=pk,
                    service_id=service_id,
                )
            )
        )

    @action(detail=True, methods=["delete"], url_path=r"services/(?P<service_id>[^/.]+)")
    def remove_service(self, request, pk: str, service_id: str):
        return Response(
            self.remove_service_handler.handle(
                RemoveAdditionalServiceCommand(
                    competition_id=pk,
                    service_id=service_id,
                )
            )
        )
    

        # ------------------------------------------------------------------
    # Contacts
    # ------------------------------------------------------------------

    @action(detail=True, methods=["post"], url_path="contacts")
    def add_contact(self, request, pk: str):
        serializer = AddContactSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        return Response(
            self.add_contact_handler.handle(
                AddContactCommand(
                    competition_id=pk,
                    **serializer.validated_data,
                )
            )
        )

    @action(detail=True, methods=["post"], url_path=r"contacts/(?P<contact_id>[^/.]+)/primary")
    def set_primary_contact(self, request, pk: str, contact_id: str):
        return Response(
            self.set_primary_contact_handler.handle(
                SetPrimaryContactCommand(
                    competition_id=pk,
                    contact_id=contact_id,
                )
            )
        )

    @action(detail=True, methods=["delete"], url_path=r"contacts/(?P<contact_id>[^/.]+)")
    def remove_contact(self, request, pk: str, contact_id: str):
        return Response(
            self.remove_contact_handler.handle(
                RemoveContactCommand(
                    competition_id=pk,
                    contact_id=contact_id,
                )
            )
        )
    
        # ------------------------------------------------------------------
    # Information Blocks
    # ------------------------------------------------------------------

    @action(detail=True, methods=["post"], url_path="information-blocks")
    def add_information_block(self, request, pk: str):
        serializer = AddInformationBlockSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        return Response(
            self.add_information_block_handler.handle(
                AddInformationBlockCommand(
                    competition_id=pk,
                    **serializer.validated_data,
                )
            )
        )

    @action(detail=True, methods=["patch"], url_path=r"information-blocks/(?P<block_id>[^/.]+)")
    def update_information_block(self, request, pk: str, block_id: str):
        serializer = UpdateInformationBlockSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        return Response(
            self.update_information_block_handler.handle(
                UpdateInformationBlockCommand(
                    competition_id=pk,
                    block_id=block_id,
                    **serializer.validated_data,
                )
            )
        )

    @action(detail=True, methods=["post"], url_path=r"information-blocks/(?P<block_id>[^/.]+)/publish")
    def publish_information_block(self, request, pk: str, block_id: str):
        return Response(
            self.publish_information_block_handler.handle(
                PublishInformationBlockCommand(
                    competition_id=pk,
                    block_id=block_id,
                )
            )
        )

    @action(detail=True, methods=["post"], url_path=r"information-blocks/(?P<block_id>[^/.]+)/hide")
    def hide_information_block(self, request, pk: str, block_id: str):
        return Response(
            self.hide_information_block_handler.handle(
                HideInformationBlockCommand(
                    competition_id=pk,
                    block_id=block_id,
                )
            )
        )

    @action(detail=True, methods=["delete"], url_path=r"information-blocks/(?P<block_id>[^/.]+)")
    def remove_information_block(self, request, pk: str, block_id: str):
        return Response(
            self.remove_information_block_handler.handle(
                RemoveInformationBlockCommand(
                    competition_id=pk,
                    block_id=block_id,
                )
            )
        )
