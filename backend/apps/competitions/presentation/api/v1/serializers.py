"""REST API serializers for Competition management.

Two families live here, both speaking the platform's **camelCase** wire contract
(API-000 §7): *request* serializers validate inbound bodies and expose their
``validated_data`` under the command DTOs' field names (via ``source=``), and
*response* serializers project the application view DTOs onto the wire. The
response serializers double as the drf-spectacular schema source, so the
documented shape and the emitted body cannot drift.
"""

from __future__ import annotations

from typing import Any

from drf_spectacular.utils import inline_serializer
from rest_framework import serializers

__all__ = [
    "AddAdditionalServiceSerializer",
    "AddAdmissionRuleSerializer",
    "AddAgeCategorySerializer",
    "AddCategorySerializer",
    "AddContactSerializer",
    "AddDisciplineSerializer",
    "AddDocumentSerializer",
    "AddInformationBlockSerializer",
    "AddParticipantGroupSerializer",
    "AddParticipationFormatSerializer",
    "AddPricingRuleSerializer",
    "AddRegulationSerializer",
    "ChangePriceSerializer",
    "CompetitionDetailEnvelopeSerializer",
    "CompetitionListEnvelopeSerializer",
    "CreateCompetitionSerializer",
    "ProblemDetailSerializer",
    "RenameCategorySerializer",
    "RenameDisciplineSerializer",
    "UpdateAdditionalServiceSerializer",
    "UpdateAgeCategorySerializer",
    "UpdateCompetitionBrandingSerializer",
    "UpdateCompetitionDeadlinesSerializer",
    "UpdateCompetitionGeneralInformationSerializer",
    "UpdateCompetitionSettingsSerializer",
    "UpdateContactsConfigSerializer",
    "UpdateDocumentSerializer",
    "UpdateInformationBlockSerializer",
    "UpdateParticipantGroupSerializer",
    "UpdateParticipationFormatSerializer",
]


# ============================================================================
# Request serializers  (camelCase wire ⇄ snake_case command fields via source)
# ============================================================================


class CreateCompetitionSerializer(serializers.Serializer[dict[str, object]]):
    organizerId = serializers.UUIDField(source="organizer_id")
    title = serializers.CharField(max_length=200)
    season = serializers.CharField(max_length=50)
    description = serializers.CharField(required=False, allow_blank=True, allow_null=True)


class UpdateCompetitionGeneralInformationSerializer(serializers.Serializer[dict[str, object]]):
    title = serializers.CharField(max_length=200)
    season = serializers.CharField(max_length=50)
    description = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    logo = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    banner = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    venueName = serializers.CharField(source="venue_name", required=False, allow_blank=True, allow_null=True)
    venueAddress = serializers.CharField(source="venue_address", required=False, allow_blank=True, allow_null=True)
    registrationStart = serializers.DateField(source="registration_start", required=False, allow_null=True)
    registrationEnd = serializers.DateField(source="registration_end", required=False, allow_null=True)
    competitionStart = serializers.DateField(source="competition_start", required=False, allow_null=True)
    competitionEnd = serializers.DateField(source="competition_end", required=False, allow_null=True)


class UpdateCompetitionBrandingSerializer(serializers.Serializer[dict[str, object]]):
    logo = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    banner = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    poster = serializers.CharField(required=False, allow_blank=True, allow_null=True)


class _MusicRequirementsInputSerializer(serializers.Serializer[dict[str, object]]):
    requireUpload = serializers.BooleanField(source="require_upload")
    allowReplacement = serializers.BooleanField(source="allow_replacement")
    allowedFormats = serializers.ListField(child=serializers.CharField(), source="allowed_formats")
    maxUploadSizeMb = serializers.IntegerField(source="max_upload_size_mb", min_value=1, max_value=512)


class _VideoRequirementsInputSerializer(serializers.Serializer[dict[str, object]]):
    mode = serializers.ChoiceField(choices=["NOT_REQUIRED", "URL_ONLY", "FILE_ONLY", "URL_OR_FILE"])
    allowedProviders = serializers.ListField(
        child=serializers.ChoiceField(choices=["YOUTUBE", "VK_VIDEO", "RUTUBE", "VIMEO"]),
        source="allowed_providers",
    )
    allowReplacement = serializers.BooleanField(source="allow_replacement")


class _PaymentReceiptRequirementsInputSerializer(serializers.Serializer[dict[str, object]]):
    requireReceipt = serializers.BooleanField(source="require_receipt")
    allowUploadLater = serializers.BooleanField(source="allow_upload_later")
    allowReplacement = serializers.BooleanField(source="allow_replacement")


class _FormatRequirementsInputSerializer(serializers.Serializer[dict[str, object]]):
    participationFormatId = serializers.UUIDField(source="participation_format_id")
    music = _MusicRequirementsInputSerializer()
    video = _VideoRequirementsInputSerializer()
    paymentReceipt = _PaymentReceiptRequirementsInputSerializer(source="payment_receipt")


class UpdateCompetitionSettingsSerializer(serializers.Serializer[dict[str, object]]):
    allowMultipleApplications = serializers.BooleanField(source="allow_multiple_applications")
    allowApplicationEditing = serializers.BooleanField(source="allow_application_editing")
    allowWithdrawingApplications = serializers.BooleanField(source="allow_withdrawing_applications")
    allowCopyingPreviousApplications = serializers.BooleanField(source="allow_copying_previous_applications")
    requireTeacher = serializers.BooleanField(source="require_teacher")
    requireParentGuardian = serializers.BooleanField(source="require_parent_guardian")
    participantCommentEnabled = serializers.BooleanField(source="participant_comment_enabled")
    requireDocumentUpload = serializers.BooleanField(source="require_document_upload")
    allowAdditionalDocumentsLater = serializers.BooleanField(source="allow_additional_documents_later")
    allowReplacingDocuments = serializers.BooleanField(source="allow_replacing_documents")
    paymentRequired = serializers.BooleanField(source="payment_required")
    paymentTiming = serializers.ChoiceField(
        source="payment_timing",
        choices=["BEFORE_REVIEW", "BEFORE_APPROVAL", "BEFORE_COMPETITION"],
    )
    paymentMethods = serializers.ListField(
        child=serializers.ChoiceField(choices=["ONLINE", "BANK_TRANSFER", "CASH"]),
        source="payment_methods",
    )
    requirePersonalDataConsent = serializers.BooleanField(source="require_personal_data_consent")
    requireMediaConsent = serializers.BooleanField(source="require_media_consent")
    requireRegulationsAcceptance = serializers.BooleanField(source="require_regulations_acceptance")
    emailNotifications = serializers.BooleanField(source="email_notifications")
    cabinetNotifications = serializers.BooleanField(source="cabinet_notifications")
    smsNotifications = serializers.BooleanField(source="sms_notifications", required=False, default=False)
    pushNotifications = serializers.BooleanField(source="push_notifications", required=False, default=False)
    manualApplicationApproval = serializers.BooleanField(source="manual_application_approval")
    automaticApprovalAfterPayment = serializers.BooleanField(source="automatic_approval_after_payment")
    allowReturningForCorrection = serializers.BooleanField(source="allow_returning_for_correction")
    formatRequirements = _FormatRequirementsInputSerializer(source="format_requirements", many=True)


class UpdateCompetitionDeadlinesSerializer(serializers.Serializer[dict[str, object]]):
    application = serializers.DateTimeField(required=False, allow_null=True)
    payment = serializers.DateTimeField(required=False, allow_null=True)
    musicUpload = serializers.DateTimeField(source="music_upload", required=False, allow_null=True)
    documentUpload = serializers.DateTimeField(source="document_upload", required=False, allow_null=True)
    correction = serializers.DateTimeField(required=False, allow_null=True)


class _ContactProfileOverrideInputSerializer(serializers.Serializer[dict[str, object]]):
    organizationName = serializers.CharField(
        source="organization_name", required=False, allow_blank=True, allow_null=True
    )
    phone = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    email = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    website = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    address = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    vk = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    instagram = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    telegram = serializers.CharField(required=False, allow_blank=True, allow_null=True)


class _TeamContactInputSerializer(serializers.Serializer[dict[str, object]]):
    id = serializers.UUIDField()
    name = serializers.CharField(max_length=200)
    position = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    phone = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    email = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    description = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    sortOrder = serializers.IntegerField(source="sort_order", required=False, default=0, min_value=0)


class _EmergencyContactsInputSerializer(serializers.Serializer[dict[str, object]]):
    phone = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    email = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    notes = serializers.CharField(required=False, allow_blank=True, allow_null=True)


class _VenueDetailsInputSerializer(serializers.Serializer[dict[str, object]]):
    city = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    country = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    googleMapsUrl = serializers.CharField(source="google_maps_url", required=False, allow_blank=True, allow_null=True)
    yandexMapsUrl = serializers.CharField(source="yandex_maps_url", required=False, allow_blank=True, allow_null=True)
    directions = serializers.CharField(required=False, allow_blank=True, allow_null=True)


class UpdateContactsConfigSerializer(serializers.Serializer[dict[str, object]]):
    useOrganizationContacts = serializers.BooleanField(source="use_organization_contacts")
    override = _ContactProfileOverrideInputSerializer()
    teamContacts = _TeamContactInputSerializer(source="team_contacts", many=True)
    emergency = _EmergencyContactsInputSerializer()
    venueDetails = _VenueDetailsInputSerializer(source="venue_details")


class AddCategorySerializer(serializers.Serializer[dict[str, object]]):
    name = serializers.CharField(max_length=120)
    description = serializers.CharField(required=False, allow_blank=True, allow_null=True, max_length=2000)
    sortOrder = serializers.IntegerField(source="sort_order", required=False, allow_null=True, min_value=0)


class RenameCategorySerializer(serializers.Serializer[dict[str, object]]):
    name = serializers.CharField(required=False, allow_null=True, max_length=120)
    description = serializers.CharField(required=False, allow_blank=True, allow_null=True, max_length=2000)
    sortOrder = serializers.IntegerField(source="sort_order", required=False, allow_null=True, min_value=0)

    def validate(self, attrs: dict[str, Any]) -> dict[str, Any]:
        if not any(k in attrs for k in ("name", "description", "sort_order")):
            raise serializers.ValidationError("At least one of name, description, or sortOrder must be provided.")
        return attrs


class AddDisciplineSerializer(serializers.Serializer[dict[str, object]]):
    categoryId = serializers.UUIDField(source="category_id")
    name = serializers.CharField(max_length=120)
    sortOrder = serializers.IntegerField(source="sort_order", required=False, allow_null=True, min_value=0)


class RenameDisciplineSerializer(serializers.Serializer[dict[str, object]]):
    name = serializers.CharField(required=False, allow_null=True, max_length=120)
    sortOrder = serializers.IntegerField(source="sort_order", required=False, allow_null=True, min_value=0)

    def validate(self, attrs: dict[str, Any]) -> dict[str, Any]:
        if not any(k in attrs for k in ("name", "sort_order")):
            raise serializers.ValidationError("At least one of name or sortOrder must be provided.")
        return attrs


class AddAgeCategorySerializer(serializers.Serializer[dict[str, object]]):
    categoryId = serializers.UUIDField(source="category_id")
    name = serializers.CharField(max_length=120)
    minAge = serializers.IntegerField(source="min_age", min_value=0)
    maxAge = serializers.IntegerField(source="max_age", min_value=0)
    sortOrder = serializers.IntegerField(source="sort_order", required=False, allow_null=True, min_value=0)
    type = serializers.ChoiceField(source="age_category_type", choices=["STANDARD", "MIXED"], default="STANDARD")
    mixedCalculationMethod = serializers.ChoiceField(
        source="mixed_calculation_method",
        choices=["AVERAGE", "OLDEST", "YOUNGEST"],
        required=False,
        allow_null=True,
        default=None,
    )

    def validate(self, attrs: dict[str, Any]) -> dict[str, Any]:
        if attrs["min_age"] > attrs["max_age"]:
            raise serializers.ValidationError("minAge must not exceed maxAge.")
        ac_type = attrs.get("age_category_type", "STANDARD")
        method = attrs.get("mixed_calculation_method")
        if ac_type == "MIXED" and method is None:
            raise serializers.ValidationError("mixedCalculationMethod is required when type is MIXED.")
        if ac_type == "STANDARD" and method is not None:
            raise serializers.ValidationError("mixedCalculationMethod must be null when type is STANDARD.")
        return attrs


class UpdateAgeCategorySerializer(serializers.Serializer[dict[str, object]]):
    name = serializers.CharField(required=False, allow_null=True, max_length=120)
    minAge = serializers.IntegerField(source="min_age", required=False, allow_null=True, min_value=0)
    maxAge = serializers.IntegerField(source="max_age", required=False, allow_null=True, min_value=0)
    sortOrder = serializers.IntegerField(source="sort_order", required=False, allow_null=True, min_value=0)
    type = serializers.ChoiceField(source="age_category_type", choices=["STANDARD", "MIXED"], required=False, allow_null=True)
    mixedCalculationMethod = serializers.ChoiceField(
        source="mixed_calculation_method",
        choices=["AVERAGE", "OLDEST", "YOUNGEST"],
        required=False,
        allow_null=True,
    )

    def validate(self, attrs: dict[str, Any]) -> dict[str, Any]:
        if not any(k in attrs for k in ("name", "min_age", "max_age", "sort_order", "age_category_type", "mixed_calculation_method")):
            raise serializers.ValidationError(
                "At least one of name, minAge, maxAge, sortOrder, type, or mixedCalculationMethod must be provided."
            )
        has_min = attrs.get("min_age") is not None
        has_max = attrs.get("max_age") is not None
        if has_min != has_max:
            raise serializers.ValidationError("Both minAge and maxAge must be provided together.")
        if has_min and has_max and attrs["min_age"] > attrs["max_age"]:
            raise serializers.ValidationError("minAge must not exceed maxAge.")
        ac_type = attrs.get("age_category_type")
        method = attrs.get("mixed_calculation_method")
        if ac_type == "MIXED" and method is None:
            raise serializers.ValidationError("mixedCalculationMethod is required when type is MIXED.")
        if ac_type == "STANDARD" and method is not None:
            raise serializers.ValidationError("mixedCalculationMethod must be null when type is STANDARD.")
        return attrs


class AddParticipantGroupSerializer(serializers.Serializer[dict[str, object]]):
    categoryId = serializers.UUIDField(source="category_id")
    name = serializers.CharField(max_length=120)
    minCount = serializers.IntegerField(source="min_count", min_value=1)
    maxCount = serializers.IntegerField(source="max_count", required=False, allow_null=True, min_value=1)
    description = serializers.CharField(required=False, allow_blank=True, allow_null=True, max_length=2000)
    sortOrder = serializers.IntegerField(source="sort_order", required=False, allow_null=True, min_value=0)

    def validate(self, attrs: dict[str, Any]) -> dict[str, Any]:
        max_count = attrs.get("max_count")
        if max_count is not None and attrs["min_count"] > max_count:
            raise serializers.ValidationError("minCount must not exceed maxCount.")
        return attrs


class UpdateParticipantGroupSerializer(serializers.Serializer[dict[str, object]]):
    name = serializers.CharField(required=False, allow_null=True, max_length=120)
    minCount = serializers.IntegerField(source="min_count", required=False, allow_null=True, min_value=1)
    maxCount = serializers.IntegerField(source="max_count", required=False, allow_null=True, min_value=1)
    description = serializers.CharField(required=False, allow_blank=True, allow_null=True, max_length=2000)
    sortOrder = serializers.IntegerField(source="sort_order", required=False, allow_null=True, min_value=0)

    def validate(self, attrs: dict[str, Any]) -> dict[str, Any]:
        if not any(k in attrs for k in ("name", "min_count", "max_count", "description", "sort_order")):
            raise serializers.ValidationError(
                "At least one of name, minCount, maxCount, description, or sortOrder must be provided."
            )
        if "min_count" in attrs and attrs["min_count"] is None:
            raise serializers.ValidationError("minCount cannot be null.")
        if "min_count" in attrs:
            max_count = attrs.get("max_count")
            if max_count is not None and attrs["min_count"] > max_count:
                raise serializers.ValidationError("minCount must not exceed maxCount.")
        elif "max_count" in attrs:
            raise serializers.ValidationError("maxCount requires minCount.")
        return attrs


class AddParticipationFormatSerializer(serializers.Serializer[dict[str, object]]):
    name = serializers.CharField(max_length=120)
    description = serializers.CharField(required=False, allow_blank=True, allow_null=True, max_length=2000)
    enabled = serializers.BooleanField(required=False, default=True)
    sortOrder = serializers.IntegerField(source="sort_order", required=False, allow_null=True, min_value=0)


class UpdateParticipationFormatSerializer(serializers.Serializer[dict[str, object]]):
    name = serializers.CharField(required=False, allow_null=True, max_length=120)
    description = serializers.CharField(required=False, allow_blank=True, allow_null=True, max_length=2000)
    enabled = serializers.BooleanField(required=False, allow_null=True)
    sortOrder = serializers.IntegerField(source="sort_order", required=False, allow_null=True, min_value=0)

    def validate(self, attrs: dict[str, Any]) -> dict[str, Any]:
        if not any(k in attrs for k in ("name", "description", "enabled", "sort_order")):
            raise serializers.ValidationError(
                "At least one of name, description, enabled, or sortOrder must be provided."
            )
        return attrs


class _AdmissionCombinationSerializer(serializers.Serializer[dict[str, object]]):
    categoryId = serializers.UUIDField(source="category_id")
    disciplineId = serializers.UUIDField(source="discipline_id")
    ageCategoryId = serializers.UUIDField(source="age_category_id")
    participantGroupId = serializers.UUIDField(source="participant_group_id")
    participationFormatId = serializers.UUIDField(source="participation_format_id")


class AddAdmissionRuleSerializer(_AdmissionCombinationSerializer):
    pass


class AddPricingRuleSerializer(_AdmissionCombinationSerializer):
    amount = serializers.DecimalField(max_digits=12, decimal_places=2, min_value=0)
    currency = serializers.CharField(max_length=3, required=False, default="BYN")
    calculationType = serializers.ChoiceField(
        source="calculation_type",
        choices=["PER_PARTICIPANT", "PER_PERFORMANCE"],
        required=False,
        default="PER_PARTICIPANT",
    )


class ChangePriceSerializer(_AdmissionCombinationSerializer):
    amount = serializers.DecimalField(max_digits=12, decimal_places=2, min_value=0)
    currency = serializers.CharField(max_length=3, required=False, default="BYN")
    calculationType = serializers.ChoiceField(
        source="calculation_type",
        choices=["PER_PARTICIPANT", "PER_PERFORMANCE"],
        required=False,
        allow_null=True,
    )


class AddRegulationSerializer(serializers.Serializer[dict[str, object]]):
    title = serializers.CharField(max_length=200)
    version = serializers.CharField(max_length=50)
    publicationDate = serializers.DateField(source="publication_date")
    fileReference = serializers.CharField(source="file_reference", max_length=1024)


class AddDocumentSerializer(serializers.Serializer[dict[str, object]]):
    title = serializers.CharField(max_length=200)
    category = serializers.CharField(max_length=32)
    visibility = serializers.CharField(max_length=16)
    fileReference = serializers.CharField(source="file_reference", max_length=1024)
    description = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    sortOrder = serializers.IntegerField(source="sort_order", required=False, default=0, min_value=0)
    published = serializers.BooleanField(required=False, default=False)


class UpdateDocumentSerializer(serializers.Serializer[dict[str, object]]):
    title = serializers.CharField(max_length=200)
    category = serializers.CharField(max_length=32)
    visibility = serializers.CharField(max_length=16)
    fileReference = serializers.CharField(source="file_reference", max_length=1024)
    description = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    sortOrder = serializers.IntegerField(source="sort_order", required=False, default=0, min_value=0)


class AddAdditionalServiceSerializer(serializers.Serializer[dict[str, object]]):
    name = serializers.CharField(max_length=120)
    amount = serializers.DecimalField(max_digits=12, decimal_places=2, min_value=0)
    currency = serializers.CharField(max_length=3, required=False, default="BYN")
    description = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    billingModel = serializers.ChoiceField(
        source="billing_model",
        choices=["PER_PARTICIPANT", "PER_PERFORMANCE"],
        required=False,
        default="PER_PARTICIPANT",
    )
    participationFormatIds = serializers.ListField(
        child=serializers.UUIDField(),
        source="participation_format_ids",
        allow_empty=False,
        min_length=1,
    )
    required = serializers.BooleanField(required=False, default=False)
    enabled = serializers.BooleanField(required=False, default=True)
    sortOrder = serializers.IntegerField(source="sort_order", required=False, default=0, min_value=0)


class UpdateAdditionalServiceSerializer(serializers.Serializer[dict[str, object]]):
    name = serializers.CharField(max_length=120)
    amount = serializers.DecimalField(max_digits=12, decimal_places=2, min_value=0)
    currency = serializers.CharField(max_length=3, required=False, default="BYN")
    description = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    billingModel = serializers.ChoiceField(
        source="billing_model",
        choices=["PER_PARTICIPANT", "PER_PERFORMANCE"],
        required=False,
        default="PER_PARTICIPANT",
    )
    participationFormatIds = serializers.ListField(
        child=serializers.UUIDField(),
        source="participation_format_ids",
        allow_empty=False,
        min_length=1,
    )
    required = serializers.BooleanField(required=False, default=False)
    sortOrder = serializers.IntegerField(source="sort_order", required=False, default=0, min_value=0)


class AddContactSerializer(serializers.Serializer[dict[str, object]]):
    contactType = serializers.CharField(source="contact_type", max_length=32)
    value = serializers.CharField(max_length=500)
    isPrimary = serializers.BooleanField(source="is_primary", required=False, default=False)


class AddInformationBlockSerializer(serializers.Serializer[dict[str, object]]):
    title = serializers.CharField(max_length=200)
    content = serializers.CharField()
    contentFormat = serializers.CharField(source="content_format", required=False, default="PLAIN", max_length=16)
    sortOrder = serializers.IntegerField(source="sort_order", required=False, default=0, min_value=0)
    published = serializers.BooleanField(required=False, default=False)


class UpdateInformationBlockSerializer(serializers.Serializer[dict[str, object]]):
    title = serializers.CharField(max_length=200)
    content = serializers.CharField()
    contentFormat = serializers.CharField(source="content_format", required=False, default="PLAIN", max_length=16)
    sortOrder = serializers.IntegerField(source="sort_order", required=False, default=0, min_value=0)


# ============================================================================
# Response serializers  (project the application view DTOs onto camelCase wire)
# ============================================================================


class _VenueSerializer(serializers.Serializer[dict[str, object]]):
    name = serializers.CharField()
    address = serializers.CharField(allow_null=True)


class _PeriodSerializer(serializers.Serializer[dict[str, object]]):
    start = serializers.DateField()
    end = serializers.DateField()


class _BrandingSerializer(serializers.Serializer[dict[str, object]]):
    logo = serializers.CharField(allow_null=True)
    banner = serializers.CharField(allow_null=True)
    poster = serializers.CharField(allow_null=True)


class _DeadlinesSerializer(serializers.Serializer[dict[str, object]]):
    application = serializers.DateTimeField(allow_null=True)
    payment = serializers.DateTimeField(allow_null=True)
    musicUpload = serializers.DateTimeField(source="music_upload", allow_null=True)
    documentUpload = serializers.DateTimeField(source="document_upload", allow_null=True)
    correction = serializers.DateTimeField(allow_null=True)


class _MusicRequirementsSerializer(serializers.Serializer[dict[str, object]]):
    requireUpload = serializers.BooleanField(source="require_upload")
    allowReplacement = serializers.BooleanField(source="allow_replacement")
    allowedFormats = serializers.ListField(child=serializers.CharField(), source="allowed_formats")
    maxUploadSizeMb = serializers.IntegerField(source="max_upload_size_mb")


class _VideoRequirementsSerializer(serializers.Serializer[dict[str, object]]):
    mode = serializers.CharField()
    allowedProviders = serializers.ListField(child=serializers.CharField(), source="allowed_providers")
    allowReplacement = serializers.BooleanField(source="allow_replacement")


class _PaymentReceiptRequirementsSerializer(serializers.Serializer[dict[str, object]]):
    requireReceipt = serializers.BooleanField(source="require_receipt")
    allowUploadLater = serializers.BooleanField(source="allow_upload_later")
    allowReplacement = serializers.BooleanField(source="allow_replacement")


class _FormatRequirementsSerializer(serializers.Serializer[dict[str, object]]):
    participationFormatId = serializers.CharField(source="participation_format_id")
    music = _MusicRequirementsSerializer()
    video = _VideoRequirementsSerializer()
    paymentReceipt = _PaymentReceiptRequirementsSerializer(source="payment_receipt")


class _SettingsSerializer(serializers.Serializer[dict[str, object]]):
    allowMultipleApplications = serializers.BooleanField(source="allow_multiple_applications")
    allowApplicationEditing = serializers.BooleanField(source="allow_application_editing")
    allowWithdrawingApplications = serializers.BooleanField(source="allow_withdrawing_applications")
    allowCopyingPreviousApplications = serializers.BooleanField(source="allow_copying_previous_applications")
    requireTeacher = serializers.BooleanField(source="require_teacher")
    requireParentGuardian = serializers.BooleanField(source="require_parent_guardian")
    participantCommentEnabled = serializers.BooleanField(source="participant_comment_enabled")
    requireDocumentUpload = serializers.BooleanField(source="require_document_upload")
    allowAdditionalDocumentsLater = serializers.BooleanField(source="allow_additional_documents_later")
    allowReplacingDocuments = serializers.BooleanField(source="allow_replacing_documents")
    paymentRequired = serializers.BooleanField(source="payment_required")
    paymentTiming = serializers.CharField(source="payment_timing")
    paymentMethods = serializers.ListField(child=serializers.CharField(), source="payment_methods")
    requirePersonalDataConsent = serializers.BooleanField(source="require_personal_data_consent")
    requireMediaConsent = serializers.BooleanField(source="require_media_consent")
    requireRegulationsAcceptance = serializers.BooleanField(source="require_regulations_acceptance")
    emailNotifications = serializers.BooleanField(source="email_notifications")
    cabinetNotifications = serializers.BooleanField(source="cabinet_notifications")
    smsNotifications = serializers.BooleanField(source="sms_notifications")
    pushNotifications = serializers.BooleanField(source="push_notifications")
    manualApplicationApproval = serializers.BooleanField(source="manual_application_approval")
    automaticApprovalAfterPayment = serializers.BooleanField(source="automatic_approval_after_payment")
    allowReturningForCorrection = serializers.BooleanField(source="allow_returning_for_correction")
    formatRequirements = _FormatRequirementsSerializer(source="format_requirements", many=True)


class _ContactProfileOverrideSerializer(serializers.Serializer[dict[str, object]]):
    organizationName = serializers.CharField(source="organization_name", allow_null=True)
    phone = serializers.CharField(allow_null=True)
    email = serializers.CharField(allow_null=True)
    website = serializers.CharField(allow_null=True)
    address = serializers.CharField(allow_null=True)
    vk = serializers.CharField(allow_null=True)
    instagram = serializers.CharField(allow_null=True)
    telegram = serializers.CharField(allow_null=True)


class _TeamContactSerializer(serializers.Serializer[dict[str, object]]):
    id = serializers.CharField()
    name = serializers.CharField()
    position = serializers.CharField(allow_null=True)
    phone = serializers.CharField(allow_null=True)
    email = serializers.CharField(allow_null=True)
    description = serializers.CharField(allow_null=True)
    sortOrder = serializers.IntegerField(source="sort_order")


class _EmergencyContactsSerializer(serializers.Serializer[dict[str, object]]):
    phone = serializers.CharField(allow_null=True)
    email = serializers.CharField(allow_null=True)
    notes = serializers.CharField(allow_null=True)


class _VenueDetailsSerializer(serializers.Serializer[dict[str, object]]):
    city = serializers.CharField(allow_null=True)
    country = serializers.CharField(allow_null=True)
    googleMapsUrl = serializers.CharField(source="google_maps_url", allow_null=True)
    yandexMapsUrl = serializers.CharField(source="yandex_maps_url", allow_null=True)
    directions = serializers.CharField(allow_null=True)


class _ContactsConfigSerializer(serializers.Serializer[dict[str, object]]):
    useOrganizationContacts = serializers.BooleanField(source="use_organization_contacts")
    override = _ContactProfileOverrideSerializer()
    teamContacts = _TeamContactSerializer(source="team_contacts", many=True)
    emergency = _EmergencyContactsSerializer()
    venueDetails = _VenueDetailsSerializer(source="venue_details")


class _CategorySerializer(serializers.Serializer[dict[str, object]]):
    id = serializers.CharField()
    name = serializers.CharField()
    description = serializers.CharField(allow_null=True)
    sortOrder = serializers.IntegerField(source="sort_order")


class _DisciplineSerializer(serializers.Serializer[dict[str, object]]):
    id = serializers.CharField()
    categoryId = serializers.CharField(source="category_id")
    name = serializers.CharField()
    sortOrder = serializers.IntegerField(source="sort_order")


class _AgeCategorySerializer(serializers.Serializer[dict[str, object]]):
    id = serializers.CharField()
    categoryId = serializers.CharField(source="category_id")
    name = serializers.CharField()
    minAge = serializers.IntegerField(source="min_age")
    maxAge = serializers.IntegerField(source="max_age")
    sortOrder = serializers.IntegerField(source="sort_order")
    type = serializers.CharField()
    mixedCalculationMethod = serializers.CharField(source="mixed_calculation_method", allow_null=True)


class _ParticipantGroupSerializer(serializers.Serializer[dict[str, object]]):
    id = serializers.CharField()
    categoryId = serializers.CharField(source="category_id")
    name = serializers.CharField()
    minCount = serializers.IntegerField(source="min_count")
    maxCount = serializers.IntegerField(source="max_count", allow_null=True)
    description = serializers.CharField(allow_null=True)
    sortOrder = serializers.IntegerField(source="sort_order")


class _ParticipationFormatSerializer(serializers.Serializer[dict[str, object]]):
    id = serializers.CharField()
    name = serializers.CharField()
    description = serializers.CharField(allow_null=True)
    enabled = serializers.BooleanField()
    sortOrder = serializers.IntegerField(source="sort_order")


class _AdmissionRuleSerializer(serializers.Serializer[dict[str, object]]):
    categoryId = serializers.CharField(source="category_id")
    disciplineId = serializers.CharField(source="discipline_id")
    ageCategoryId = serializers.CharField(source="age_category_id")
    participantGroupId = serializers.CharField(source="participant_group_id")
    participationFormatId = serializers.CharField(source="participation_format_id")


class _PricingRuleSerializer(_AdmissionRuleSerializer):
    amount = serializers.CharField()
    currency = serializers.CharField()
    calculationType = serializers.CharField(source="calculation_type")


class _RegulationSerializer(serializers.Serializer[dict[str, object]]):
    id = serializers.CharField()
    title = serializers.CharField()
    version = serializers.CharField()
    publicationDate = serializers.DateField(source="publication_date")
    fileReference = serializers.CharField(source="file_reference")
    isCurrent = serializers.BooleanField(source="is_current")


class _DocumentSerializer(serializers.Serializer[dict[str, object]]):
    id = serializers.CharField()
    title = serializers.CharField()
    category = serializers.CharField()
    visibility = serializers.CharField()
    fileReference = serializers.CharField(source="file_reference")
    description = serializers.CharField(allow_null=True)
    sortOrder = serializers.IntegerField(source="sort_order")
    published = serializers.BooleanField()


class _AdditionalServiceSerializer(serializers.Serializer[dict[str, object]]):
    id = serializers.CharField()
    name = serializers.CharField()
    amount = serializers.CharField()
    currency = serializers.CharField()
    description = serializers.CharField(allow_null=True)
    billingModel = serializers.CharField(source="billing_model")
    participationFormatIds = serializers.ListField(child=serializers.CharField(), source="participation_format_ids")
    required = serializers.BooleanField()
    enabled = serializers.BooleanField()
    sortOrder = serializers.IntegerField(source="sort_order")


class _ContactSerializer(serializers.Serializer[dict[str, object]]):
    id = serializers.CharField()
    type = serializers.CharField()
    value = serializers.CharField()
    isPrimary = serializers.BooleanField(source="is_primary")


class _InformationBlockSerializer(serializers.Serializer[dict[str, object]]):
    id = serializers.CharField()
    title = serializers.CharField()
    content = serializers.CharField()
    contentFormat = serializers.CharField(source="content_format")
    published = serializers.BooleanField()
    sortOrder = serializers.IntegerField(source="sort_order")


class CompetitionSummarySerializer(serializers.Serializer[dict[str, object]]):
    id = serializers.CharField()
    title = serializers.CharField()
    season = serializers.CharField()
    status = serializers.CharField()
    organizerId = serializers.CharField(source="organizer_id")
    description = serializers.CharField(allow_null=True)
    createdAt = serializers.DateTimeField(source="created_at")
    updatedAt = serializers.DateTimeField(source="updated_at")
    version = serializers.IntegerField()


class CompetitionDetailSerializer(serializers.Serializer[dict[str, object]]):
    id = serializers.CharField()
    title = serializers.CharField()
    season = serializers.CharField()
    status = serializers.CharField()
    organizerId = serializers.CharField(source="organizer_id")
    description = serializers.CharField(allow_null=True)
    branding = _BrandingSerializer()
    venue = _VenueSerializer(allow_null=True)
    registrationPeriod = _PeriodSerializer(source="registration_period", allow_null=True)
    competitionPeriod = _PeriodSerializer(source="competition_period", allow_null=True)
    settings = _SettingsSerializer()
    contactsConfig = _ContactsConfigSerializer(source="contacts_config")
    deadlines = _DeadlinesSerializer()
    participationFormats = _ParticipationFormatSerializer(source="participation_formats", many=True)
    categories = _CategorySerializer(many=True)
    disciplines = _DisciplineSerializer(many=True)
    ageCategories = _AgeCategorySerializer(source="age_categories", many=True)
    participantGroups = _ParticipantGroupSerializer(source="participant_groups", many=True)
    admissionRules = _AdmissionRuleSerializer(source="admission_rules", many=True)
    pricingRules = _PricingRuleSerializer(source="pricing_rules", many=True)
    regulations = _RegulationSerializer(many=True)
    currentRegulationId = serializers.CharField(source="current_regulation_id", allow_null=True)
    documents = _DocumentSerializer(many=True)
    additionalServices = _AdditionalServiceSerializer(source="additional_services", many=True)
    contacts = _ContactSerializer(many=True)
    informationBlocks = _InformationBlockSerializer(source="information_blocks", many=True)
    createdAt = serializers.DateTimeField(source="created_at")
    updatedAt = serializers.DateTimeField(source="updated_at")
    version = serializers.IntegerField()


class _MetaSerializer(serializers.Serializer[dict[str, object]]):
    requestId = serializers.CharField()


# Envelope + problem schemas use ``inline_serializer`` so the reserved wire key
# ``data`` is a field, not a class attribute shadowing ``Serializer.data``.
CompetitionDetailEnvelopeSerializer = inline_serializer(
    name="CompetitionDetailResponse",
    fields={"data": CompetitionDetailSerializer(), "meta": _MetaSerializer()},
)

CompetitionListEnvelopeSerializer = inline_serializer(
    name="CompetitionListResponse",
    fields={"data": CompetitionSummarySerializer(many=True), "meta": _MetaSerializer()},
)

ProblemDetailSerializer = inline_serializer(
    name="CompetitionProblemDetail",
    fields={
        "type": serializers.URLField(),
        "title": serializers.CharField(),
        "status": serializers.IntegerField(),
        "detail": serializers.CharField(),
        "instance": serializers.CharField(),
        "requestId": serializers.CharField(),
        "code": serializers.CharField(required=False),
    },
)
