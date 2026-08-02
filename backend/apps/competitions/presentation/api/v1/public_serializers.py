"""Serializers for the Public Festival Catalog edge.

Output-only, read-model serializers: they render the flat
:class:`PublicFestivalView` DTOs into the platform's ``{data, meta}`` envelope
with camelCase field names (API-000 §5). They validate no input — the catalog is
a GET with no body — and are deliberately independent of the organizer control
panel's serializers.
"""

from __future__ import annotations

from rest_framework import serializers

__all__ = [
    "PublicFestivalDetailEnvelopeSerializer",
    "PublicFestivalDetailSerializer",
    "PublicFestivalListEnvelopeSerializer",
    "PublicFestivalSerializer",
    "RegistrationEnvelopeSerializer",
    "RegistrationSerializer",
]


class PublicCatalogMetaSerializer(serializers.Serializer):
    """Response envelope metadata (API-000 §5)."""

    requestId = serializers.CharField()


class PublicFestivalOrganizerSerializer(serializers.Serializer):
    """Organizer identity for a catalog card."""

    id = serializers.CharField()
    name = serializers.CharField()
    logo = serializers.CharField(allow_null=True)


class PublicFestivalFormatSerializer(serializers.Serializer):
    """A participation format with its normalized display mode."""

    name = serializers.CharField()
    mode = serializers.CharField(allow_null=True)


class PublicFestivalPricingSerializer(serializers.Serializer):
    """The "from X" price summary."""

    amountFrom = serializers.DecimalField(source="amount_from", max_digits=12, decimal_places=2, allow_null=True)
    currency = serializers.CharField(allow_null=True)
    multiple = serializers.BooleanField()


class PublicFestivalSerializer(serializers.Serializer):
    """One competition as rendered in the public catalog."""

    id = serializers.CharField()
    # The address the site links this competition at. Nullable: a competition
    # predating slugs is still reachable — and still linkable — by its id.
    slug = serializers.CharField(allow_null=True)
    title = serializers.CharField()
    season = serializers.CharField()
    description = serializers.CharField(allow_null=True)
    status = serializers.CharField()
    organizer = PublicFestivalOrganizerSerializer()
    city = serializers.CharField(allow_null=True)
    venueName = serializers.CharField(source="venue_name", allow_null=True)
    venueAddress = serializers.CharField(source="venue_address", allow_null=True)
    coverImage = serializers.CharField(source="cover_image", allow_null=True)
    competitionStart = serializers.DateField(source="competition_start", allow_null=True)
    competitionEnd = serializers.DateField(source="competition_end", allow_null=True)
    registrationStart = serializers.DateField(source="registration_start", allow_null=True)
    registrationEnd = serializers.DateField(source="registration_end", allow_null=True)
    applicationDeadline = serializers.DateTimeField(source="application_deadline", allow_null=True)
    pricing = PublicFestivalPricingSerializer()
    formats = PublicFestivalFormatSerializer(many=True)
    modes = serializers.ListField(child=serializers.CharField())
    categories = serializers.ListField(child=serializers.CharField())
    createdAt = serializers.DateTimeField(source="created_at", allow_null=True)
    updatedAt = serializers.DateTimeField(source="updated_at", allow_null=True)


class PublicFestivalListEnvelopeSerializer(serializers.Serializer):
    """The full ``GET /public/festivals`` response envelope."""

    data = PublicFestivalSerializer(many=True)
    meta = PublicCatalogMetaSerializer()


# --- Detail (landing page) ----------------------------------------------------


class PublicFestivalJuryCardSerializer(serializers.Serializer):
    """A jury/expert card in a landing JURY block."""

    id = serializers.CharField()
    name = serializers.CharField()
    photo = serializers.CharField(allow_null=True)
    position = serializers.CharField(allow_null=True)
    description = serializers.CharField(allow_null=True)


class PublicFestivalPartnerCardSerializer(serializers.Serializer):
    """A partner/sponsor card in a landing PARTNERS block."""

    id = serializers.CharField()
    name = serializers.CharField()
    logo = serializers.CharField(allow_null=True)
    website = serializers.CharField(allow_null=True)


class PublicFestivalGalleryImageSerializer(serializers.Serializer):
    """An image in a landing GALLERY block."""

    id = serializers.CharField()
    url = serializers.CharField()
    caption = serializers.CharField(allow_null=True)


class PublicFestivalFaqItemSerializer(serializers.Serializer):
    """A question/answer pair in a landing FAQ block."""

    id = serializers.CharField()
    question = serializers.CharField()
    answer = serializers.CharField()


class PublicFestivalLandingBlockSerializer(serializers.Serializer):
    """One enabled landing block, in display order, with its typed payload."""

    id = serializers.CharField()
    type = serializers.CharField()
    sortOrder = serializers.IntegerField(source="sort_order")
    title = serializers.CharField(allow_null=True)
    subtitle = serializers.CharField(allow_null=True)
    coverImage = serializers.CharField(source="cover_image", allow_null=True)
    body = serializers.CharField(allow_null=True)
    contentFormat = serializers.CharField(source="content_format", allow_null=True)
    jury = PublicFestivalJuryCardSerializer(many=True)
    partners = PublicFestivalPartnerCardSerializer(many=True)
    images = PublicFestivalGalleryImageSerializer(many=True)
    faq = PublicFestivalFaqItemSerializer(many=True)


class PublicFestivalLandingSerializer(serializers.Serializer):
    """The public landing page: enabled blocks in display order."""

    blocks = PublicFestivalLandingBlockSerializer(many=True)


class PublicFestivalSocialLinksSerializer(serializers.Serializer):
    """Public social links for the footer."""

    vk = serializers.CharField(allow_null=True)
    instagram = serializers.CharField(allow_null=True)
    telegram = serializers.CharField(allow_null=True)


class PublicFestivalTeamMemberSerializer(serializers.Serializer):
    """A named contact person shown on the public page."""

    id = serializers.CharField()
    name = serializers.CharField()
    position = serializers.CharField(allow_null=True)
    phone = serializers.CharField(allow_null=True)
    email = serializers.CharField(allow_null=True)
    description = serializers.CharField(allow_null=True)


class PublicFestivalEmergencySerializer(serializers.Serializer):
    """Optional emergency/urgent contact line."""

    phone = serializers.CharField(allow_null=True)
    email = serializers.CharField(allow_null=True)
    notes = serializers.CharField(allow_null=True)


class PublicFestivalVenueSerializer(serializers.Serializer):
    """The venue section — competition venue merged with contact details."""

    name = serializers.CharField(allow_null=True)
    address = serializers.CharField(allow_null=True)
    city = serializers.CharField(allow_null=True)
    country = serializers.CharField(allow_null=True)
    googleMapsUrl = serializers.CharField(source="google_maps_url", allow_null=True)
    yandexMapsUrl = serializers.CharField(source="yandex_maps_url", allow_null=True)
    directions = serializers.CharField(allow_null=True)


class PublicFestivalContactsSerializer(serializers.Serializer):
    """The public contacts module: organizer identity, channels, team, venue."""

    organizationName = serializers.CharField(source="organization_name", allow_null=True)
    phone = serializers.CharField(allow_null=True)
    email = serializers.CharField(allow_null=True)
    website = serializers.CharField(allow_null=True)
    address = serializers.CharField(allow_null=True)
    social = PublicFestivalSocialLinksSerializer()
    team = PublicFestivalTeamMemberSerializer(many=True)
    emergency = PublicFestivalEmergencySerializer()
    venue = PublicFestivalVenueSerializer()
    legalInformation = serializers.CharField(source="legal_information", allow_null=True)


class PublicFestivalRegulationSerializer(serializers.Serializer):
    """The competition's current regulation ("Положение фестиваля")."""

    title = serializers.CharField()
    version = serializers.CharField()
    publicationDate = serializers.DateField(source="publication_date")
    fileReference = serializers.CharField(source="file_reference")


class PublicFestivalDocumentSerializer(serializers.Serializer):
    """One publicly-visible competition document shown on the landing page."""

    id = serializers.CharField()
    title = serializers.CharField()
    category = serializers.CharField()
    description = serializers.CharField(allow_null=True)
    fileReference = serializers.CharField(source="file_reference")


class PublicFestivalDetailSerializer(PublicFestivalSerializer):
    """One competition's full public landing view (catalog facts + landing + contacts)."""

    landing = PublicFestivalLandingSerializer()
    contacts = PublicFestivalContactsSerializer()
    regulation = PublicFestivalRegulationSerializer(allow_null=True)
    documents = PublicFestivalDocumentSerializer(many=True)


class PublicFestivalDetailEnvelopeSerializer(serializers.Serializer):
    """The full ``GET /public/festivals/{id}`` response envelope."""

    data = PublicFestivalDetailSerializer()
    meta = PublicCatalogMetaSerializer()


# ---------------------------------------------------------------------------
# Registration read model (the Registration Wizard's single projection)
# ---------------------------------------------------------------------------


class RegistrationCompetitionSerializer(serializers.Serializer):
    """Competition summary for the registration flow."""

    id = serializers.CharField()
    title = serializers.CharField()
    season = serializers.CharField()
    status = serializers.CharField()
    venueName = serializers.CharField(source="venue_name", allow_null=True)
    venueAddress = serializers.CharField(source="venue_address", allow_null=True)


class RegistrationDeadlinesSerializer(serializers.Serializer):
    """Independent registration deadlines (null = no cut-off)."""

    application = serializers.DateTimeField(allow_null=True)
    payment = serializers.DateTimeField(allow_null=True)
    musicUpload = serializers.DateTimeField(source="music_upload", allow_null=True)
    documentUpload = serializers.DateTimeField(source="document_upload", allow_null=True)
    correction = serializers.DateTimeField(allow_null=True)


class RegistrationNominationSerializer(serializers.Serializer):
    id = serializers.CharField()
    name = serializers.CharField()
    description = serializers.CharField(allow_null=True)
    sortOrder = serializers.IntegerField(source="sort_order")
    registrationOpen = serializers.BooleanField(source="registration_open")
    registrationStopped = serializers.BooleanField(source="registration_stopped")
    registrationOpensAt = serializers.DateTimeField(source="registration_opens_at", allow_null=True)
    registrationClosesAt = serializers.DateTimeField(source="registration_closes_at", allow_null=True)


class RegistrationDisciplineSerializer(serializers.Serializer):
    id = serializers.CharField()
    nominationId = serializers.CharField(source="nomination_id")
    name = serializers.CharField()
    sortOrder = serializers.IntegerField(source="sort_order")


class RegistrationAgeCategorySerializer(serializers.Serializer):
    id = serializers.CharField()
    participantGroupId = serializers.CharField(source="participant_group_id")
    name = serializers.CharField()
    minAge = serializers.IntegerField(source="min_age")
    maxAge = serializers.IntegerField(source="max_age")
    sortOrder = serializers.IntegerField(source="sort_order")


class RegistrationParticipantGroupSerializer(serializers.Serializer):
    id = serializers.CharField()
    name = serializers.CharField()
    minCount = serializers.IntegerField(source="min_count")
    maxCount = serializers.IntegerField(source="max_count", allow_null=True)
    sortOrder = serializers.IntegerField(source="sort_order")


class RegistrationFormatSerializer(serializers.Serializer):
    id = serializers.CharField()
    name = serializers.CharField()
    sortOrder = serializers.IntegerField(source="sort_order")


class RegistrationAdmissionRuleSerializer(serializers.Serializer):
    nominationId = serializers.CharField(source="nomination_id")
    disciplineId = serializers.CharField(source="discipline_id")
    ageCategoryId = serializers.CharField(source="age_category_id")
    participantGroupId = serializers.CharField(source="participant_group_id")
    participationFormatId = serializers.CharField(source="participation_format_id")


class RegistrationServiceSerializer(serializers.Serializer):
    id = serializers.CharField()
    name = serializers.CharField()
    amount = serializers.CharField()
    currency = serializers.CharField()
    billingModel = serializers.CharField(source="billing_model")
    required = serializers.BooleanField()
    availableFormatIds = serializers.ListField(source="available_format_ids", child=serializers.CharField())
    description = serializers.CharField(allow_null=True)


class RegistrationConsentRequirementSerializer(serializers.Serializer):
    code = serializers.CharField()
    label = serializers.CharField()
    required = serializers.BooleanField()


class RegistrationUploadRequirementSerializer(serializers.Serializer):
    participationFormatId = serializers.CharField(source="participation_format_id")
    musicRequired = serializers.BooleanField(source="music_required")
    musicAllowedFormats = serializers.ListField(source="music_allowed_formats", child=serializers.CharField())
    musicMaxUploadSizeMb = serializers.IntegerField(source="music_max_upload_size_mb")
    videoMode = serializers.CharField(source="video_mode")
    receiptRequired = serializers.BooleanField(source="receipt_required")


class RegistrationSerializer(serializers.Serializer):
    """The single Registration projection consumed by the wizard."""

    competition = RegistrationCompetitionSerializer()
    registrationOpen = serializers.BooleanField(source="registration_open")
    deadlines = RegistrationDeadlinesSerializer()
    nominations = RegistrationNominationSerializer(many=True)
    disciplines = RegistrationDisciplineSerializer(many=True)
    ageCategories = RegistrationAgeCategorySerializer(source="age_categories", many=True)
    participantGroups = RegistrationParticipantGroupSerializer(source="participant_groups", many=True)
    participationFormats = RegistrationFormatSerializer(source="participation_formats", many=True)
    admissionRules = RegistrationAdmissionRuleSerializer(source="admission_rules", many=True)
    additionalServices = RegistrationServiceSerializer(source="additional_services", many=True)
    requiredConsents = RegistrationConsentRequirementSerializer(source="required_consents", many=True)
    uploadRequirements = RegistrationUploadRequirementSerializer(source="upload_requirements", many=True)


class RegistrationEnvelopeSerializer(serializers.Serializer):
    """The ``{data, meta}`` envelope for the registration projection."""

    data = RegistrationSerializer()
    meta = PublicCatalogMetaSerializer()
