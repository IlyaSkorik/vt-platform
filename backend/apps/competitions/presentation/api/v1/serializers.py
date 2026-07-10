"""REST API serializers for Competition management."""

from __future__ import annotations

from rest_framework import serializers

__all__ = [
    # Competition
    "CreateCompetitionSerializer",
    "UpdateCompetitionGeneralInformationSerializer",
    "UpdateCompetitionBrandingSerializer",
    "UpdateCompetitionSettingsSerializer",
    "UpdateCompetitionDeadlinesSerializer",

    # Taxonomy
    "AddCategorySerializer",
    "RenameCategorySerializer",
    "AddDisciplineSerializer",
    "RenameDisciplineSerializer",
    "AddAgeCategorySerializer",
    "AddParticipantGroupSerializer",

    # Participation formats
    "EnableParticipationFormatSerializer",
    "DisableParticipationFormatSerializer",

    # Rules
    "AddAdmissionRuleSerializer",
    "RemoveAdmissionRuleSerializer",
    "AddPricingRuleSerializer",
    "ChangePriceSerializer",
    "RemovePricingRuleSerializer",

    # Regulations
    "AddRegulationSerializer",
    "MakeRegulationCurrentSerializer",

    # Documents
    "AddDocumentSerializer",
    "UpdateDocumentSerializer",
    "PublishDocumentSerializer",
    "UnpublishDocumentSerializer",

    # Services
    "AddAdditionalServiceSerializer",
    "UpdateAdditionalServiceSerializer",
    "EnableAdditionalServiceSerializer",
    "DisableAdditionalServiceSerializer",

    # Contacts
    "AddContactSerializer",
    "SetPrimaryContactSerializer",

    # Information blocks
    "AddInformationBlockSerializer",
    "UpdateInformationBlockSerializer",
]


# ============================================================================
# Competition
# ============================================================================


class CreateCompetitionSerializer(serializers.Serializer):
    """POST /competitions"""

    title = serializers.CharField(max_length=200)
    season = serializers.CharField(max_length=50)
    organizer_id = serializers.UUIDField()
    description = serializers.CharField(
        required=False,
        allow_blank=True,
        allow_null=True,
    )


class UpdateCompetitionGeneralInformationSerializer(serializers.Serializer):
    """PATCH /competitions/{id}"""

    title = serializers.CharField(max_length=200)
    season = serializers.CharField(max_length=50)

    description = serializers.CharField(
        required=False,
        allow_blank=True,
        allow_null=True,
    )

    logo = serializers.CharField(
        required=False,
        allow_blank=True,
        allow_null=True,
    )

    banner = serializers.CharField(
        required=False,
        allow_blank=True,
        allow_null=True,
    )

    venue_name = serializers.CharField(
        required=False,
        allow_blank=True,
        allow_null=True,
    )

    venue_address = serializers.CharField(
        required=False,
        allow_blank=True,
        allow_null=True,
    )

    registration_start = serializers.DateField(
        required=False,
        allow_null=True,
    )

    registration_end = serializers.DateField(
        required=False,
        allow_null=True,
    )

    competition_start = serializers.DateField(
        required=False,
        allow_null=True,
    )

    competition_end = serializers.DateField(
        required=False,
        allow_null=True,
    )


class UpdateCompetitionBrandingSerializer(serializers.Serializer):
    """PATCH /competitions/{id}/branding"""

    logo = serializers.CharField(
        required=False,
        allow_blank=True,
        allow_null=True,
    )

    banner = serializers.CharField(
        required=False,
        allow_blank=True,
        allow_null=True,
    )

    poster = serializers.CharField(
        required=False,
        allow_blank=True,
        allow_null=True,
    )


class UpdateCompetitionSettingsSerializer(serializers.Serializer):
    """PATCH /competitions/{id}/settings"""

    settings = serializers.JSONField()


class UpdateCompetitionDeadlinesSerializer(serializers.Serializer):
    """PATCH /competitions/{id}/deadlines"""

    application = serializers.DateTimeField(
        required=False,
        allow_null=True,
    )

    payment = serializers.DateTimeField(
        required=False,
        allow_null=True,
    )

    music_upload = serializers.DateTimeField(
        required=False,
        allow_null=True,
    )

    document_upload = serializers.DateTimeField(
        required=False,
        allow_null=True,
    )

    correction = serializers.DateTimeField(
        required=False,
        allow_null=True,
    )

# ============================================================================
# Taxonomy
# ============================================================================


class AddCategorySerializer(serializers.Serializer):
    """POST /competitions/{id}/categories"""

    name = serializers.CharField(
        max_length=120,
    )


class RenameCategorySerializer(serializers.Serializer):
    """PATCH /competitions/{id}/categories/{category_id}"""

    name = serializers.CharField(
        max_length=120,
    )


class AddDisciplineSerializer(serializers.Serializer):
    """POST /competitions/{id}/disciplines"""

    category_id = serializers.UUIDField()

    name = serializers.CharField(
        max_length=120,
    )


class RenameDisciplineSerializer(serializers.Serializer):
    """PATCH /competitions/{id}/disciplines/{discipline_id}"""

    name = serializers.CharField(
        max_length=120,
    )


class AddAgeCategorySerializer(serializers.Serializer):
    """POST /competitions/{id}/age-categories"""

    min_age = serializers.IntegerField(
        min_value=0,
    )

    max_age = serializers.IntegerField(
        min_value=0,
    )


class AddParticipantGroupSerializer(serializers.Serializer):
    """POST /competitions/{id}/participant-groups"""

    category_id = serializers.UUIDField()

    name = serializers.CharField(
        max_length=120,
    )

    min_count = serializers.IntegerField(
        min_value=1,
    )

    max_count = serializers.IntegerField(
        required=False,
        allow_null=True,
        min_value=1,
    )


# ============================================================================
# Participation formats
# ============================================================================


class EnableParticipationFormatSerializer(serializers.Serializer):
    """POST /competitions/{id}/participation-formats"""

    participation_format = serializers.CharField(
        max_length=32,
    )


class DisableParticipationFormatSerializer(serializers.Serializer):
    """DELETE /competitions/{id}/participation-formats"""

    participation_format = serializers.CharField(
        max_length=32,
    )

# ============================================================================
# Admission & Pricing Rules
# ============================================================================


class AddAdmissionRuleSerializer(serializers.Serializer):
    """POST /competitions/{id}/admission-rules"""

    category_id = serializers.UUIDField()
    discipline_id = serializers.UUIDField()
    age_category_id = serializers.UUIDField()
    participant_group_id = serializers.UUIDField()

    participation_format = serializers.CharField(
        max_length=32,
    )


class RemoveAdmissionRuleSerializer(serializers.Serializer):
    """DELETE /competitions/{id}/admission-rules"""

    category_id = serializers.UUIDField()
    discipline_id = serializers.UUIDField()
    age_category_id = serializers.UUIDField()
    participant_group_id = serializers.UUIDField()

    participation_format = serializers.CharField(
        max_length=32,
    )


class AddPricingRuleSerializer(serializers.Serializer):
    """POST /competitions/{id}/pricing-rules"""

    category_id = serializers.UUIDField()
    discipline_id = serializers.UUIDField()
    age_category_id = serializers.UUIDField()
    participant_group_id = serializers.UUIDField()

    participation_format = serializers.CharField(
        max_length=32,
    )

    amount = serializers.DecimalField(
        max_digits=12,
        decimal_places=2,
        min_value=0,
    )

    currency = serializers.CharField(
        max_length=3,
    )


class ChangePriceSerializer(serializers.Serializer):
    """PATCH /competitions/{id}/pricing-rules"""

    category_id = serializers.UUIDField()
    discipline_id = serializers.UUIDField()
    age_category_id = serializers.UUIDField()
    participant_group_id = serializers.UUIDField()

    participation_format = serializers.CharField(
        max_length=32,
    )

    amount = serializers.DecimalField(
        max_digits=12,
        decimal_places=2,
        min_value=0,
    )

    currency = serializers.CharField(
        max_length=3,
    )


class RemovePricingRuleSerializer(serializers.Serializer):
    """DELETE /competitions/{id}/pricing-rules"""

    category_id = serializers.UUIDField()
    discipline_id = serializers.UUIDField()
    age_category_id = serializers.UUIDField()
    participant_group_id = serializers.UUIDField()

    participation_format = serializers.CharField(
        max_length=32,
    )

# ============================================================================
# Regulations
# ============================================================================


class AddRegulationSerializer(serializers.Serializer):
    """POST /competitions/{id}/regulations"""

    title = serializers.CharField(
        max_length=200,
    )

    version = serializers.CharField(
        max_length=50,
    )

    publication_date = serializers.DateField()

    file_reference = serializers.CharField(
        max_length=1024,
    )


class MakeRegulationCurrentSerializer(serializers.Serializer):
    """POST /competitions/{id}/regulations/current"""

    regulation_id = serializers.UUIDField()


# ============================================================================
# Documents
# ============================================================================


class AddDocumentSerializer(serializers.Serializer):
    """POST /competitions/{id}/documents"""

    title = serializers.CharField(
        max_length=200,
    )

    category = serializers.CharField(
        max_length=32,
    )

    visibility = serializers.CharField(
        max_length=16,
    )

    file_reference = serializers.CharField(
        max_length=1024,
    )

    description = serializers.CharField(
        required=False,
        allow_blank=True,
        allow_null=True,
    )

    sort_order = serializers.IntegerField(
        required=False,
        default=0,
        min_value=0,
    )

    published = serializers.BooleanField(
        required=False,
        default=False,
    )


class UpdateDocumentSerializer(serializers.Serializer):
    """PATCH /competitions/{id}/documents/{document_id}"""

    title = serializers.CharField(
        max_length=200,
    )

    category = serializers.CharField(
        max_length=32,
    )

    visibility = serializers.CharField(
        max_length=16,
    )

    file_reference = serializers.CharField(
        max_length=1024,
    )

    description = serializers.CharField(
        required=False,
        allow_blank=True,
        allow_null=True,
    )

    sort_order = serializers.IntegerField(
        min_value=0,
    )


class PublishDocumentSerializer(serializers.Serializer):
    """POST /competitions/{id}/documents/{document_id}/publish"""

    document_id = serializers.UUIDField()


class UnpublishDocumentSerializer(serializers.Serializer):
    """POST /competitions/{id}/documents/{document_id}/unpublish"""

    document_id = serializers.UUIDField()

# ============================================================================
# Additional Services
# ============================================================================


class AddAdditionalServiceSerializer(serializers.Serializer):
    """POST /competitions/{id}/additional-services"""

    name = serializers.CharField(
        max_length=120,
    )

    amount = serializers.DecimalField(
        max_digits=12,
        decimal_places=2,
        min_value=0,
    )

    currency = serializers.CharField(
        max_length=3,
    )

    description = serializers.CharField(
        required=False,
        allow_blank=True,
        allow_null=True,
    )

    enabled = serializers.BooleanField(
        required=False,
        default=True,
    )


class UpdateAdditionalServiceSerializer(serializers.Serializer):
    """PATCH /competitions/{id}/additional-services/{service_id}"""

    name = serializers.CharField(
        max_length=120,
    )

    amount = serializers.DecimalField(
        max_digits=12,
        decimal_places=2,
        min_value=0,
    )

    currency = serializers.CharField(
        max_length=3,
    )

    description = serializers.CharField(
        required=False,
        allow_blank=True,
        allow_null=True,
    )


class EnableAdditionalServiceSerializer(serializers.Serializer):
    """POST /competitions/{id}/additional-services/{service_id}/enable"""

    service_id = serializers.UUIDField()


class DisableAdditionalServiceSerializer(serializers.Serializer):
    """POST /competitions/{id}/additional-services/{service_id}/disable"""

    service_id = serializers.UUIDField()


# ============================================================================
# Contacts
# ============================================================================


class AddContactSerializer(serializers.Serializer):
    """POST /competitions/{id}/contacts"""

    contact_type = serializers.CharField(
        max_length=32,
    )

    value = serializers.CharField(
        max_length=500,
    )

    is_primary = serializers.BooleanField(
        required=False,
        default=False,
    )


class SetPrimaryContactSerializer(serializers.Serializer):
    """POST /competitions/{id}/contacts/{contact_id}/primary"""

    contact_id = serializers.UUIDField()

# ============================================================================
# Information Blocks
# ============================================================================


class AddInformationBlockSerializer(serializers.Serializer):
    """POST /competitions/{id}/information-blocks"""

    title = serializers.CharField(
        max_length=200,
    )

    content = serializers.CharField()

    sort_order = serializers.IntegerField(
        required=False,
        default=0,
        min_value=0,
    )

    published = serializers.BooleanField(
        required=False,
        default=False,
    )


class UpdateInformationBlockSerializer(serializers.Serializer):
    """PATCH /competitions/{id}/information-blocks/{block_id}"""

    title = serializers.CharField(
        max_length=200,
    )

    content = serializers.CharField()

    sort_order = serializers.IntegerField(
        min_value=0,
    )


class PublishInformationBlockSerializer(serializers.Serializer):
    """POST /competitions/{id}/information-blocks/{block_id}/publish"""

    block_id = serializers.UUIDField()


class HideInformationBlockSerializer(serializers.Serializer):
    """POST /competitions/{id}/information-blocks/{block_id}/hide"""

    block_id = serializers.UUIDField()


# ============================================================================
# Competition Lifecycle
# ============================================================================


class MarkCompetitionConfiguredSerializer(serializers.Serializer):
    """POST /competitions/{id}/configured"""

    pass


class RevertCompetitionToDraftSerializer(serializers.Serializer):
    """POST /competitions/{id}/draft"""

    pass


class MarkCompetitionReadySerializer(serializers.Serializer):
    """POST /competitions/{id}/ready"""

    pass


class RevertCompetitionToConfiguredSerializer(serializers.Serializer):
    """POST /competitions/{id}/configured/revert"""

    pass


class PublishCompetitionSerializer(serializers.Serializer):
    """POST /competitions/{id}/publish"""

    pass


class OpenRegistrationSerializer(serializers.Serializer):
    """POST /competitions/{id}/registration/open"""

    pass


class CloseRegistrationSerializer(serializers.Serializer):
    """POST /competitions/{id}/registration/close"""

    pass


class StartCompetitionSerializer(serializers.Serializer):
    """POST /competitions/{id}/start"""

    pass


class CompleteCompetitionSerializer(serializers.Serializer):
    """POST /competitions/{id}/complete"""

    pass


class ArchiveCompetitionSerializer(serializers.Serializer):
    """POST /competitions/{id}/archive"""

    pass
