"""Request/response serializers for the Diplomas workspace REST surface.

Hand-written ``serializers.Serializer`` classes (not ``ModelSerializer``) with
camelCase fields, matching the platform's API contract (API-000). The response
serializers exist only to document the OpenAPI schema drf-spectacular emits; the
views build their payload dicts directly in :mod:`composition`.
"""

from __future__ import annotations

from rest_framework import serializers

from apps.diplomas.domain.document_types import DocumentType, policy_for

__all__ = [
    "DOCUMENT_TYPES",
    "GENERATED_DOCUMENT_TYPES",
    "AssignmentResponseSerializer",
    "CreateAssignmentRequestSerializer",
    "CreateDiplomaRequestSerializer",
    "CreateTemplateRequestSerializer",
    "DiplomaResponseSerializer",
    "DiplomaSnapshotSerializer",
    "DocumentSlotSerializer",
    "GenerateDocumentsRequestSerializer",
    "GenerateDocumentsResponseSerializer",
    "GenerationRunResponseSerializer",
    "LayoutResponseSerializer",
    "PreviewApplicationSerializer",
    "PreviewBindingsSerializer",
    "PrintJobResponseSerializer",
    "PrintPackageRequestSerializer",
    "PrintPackageSummaryResponseSerializer",
    "SaveLayoutRequestSerializer",
    "SlotDisciplineSerializer",
    "TemplateDocumentResponseSerializer",
    "TemplateFieldResponseSerializer",
    "TemplateResponseSerializer",
    "UploadTemplateDocumentRequestSerializer",
]


class PreviewApplicationSerializer(serializers.Serializer[dict[str, object]]):
    """An application selectable for diploma preview."""

    id = serializers.UUIDField()
    # "label" shadows the base Field.label attribute name — safe at runtime.
    label = serializers.CharField(allow_blank=True)  # type: ignore[assignment]


class PreviewBindingsSerializer(serializers.Serializer[dict[str, object]]):
    """Resolved binding→value map for a previewed application."""

    bindings = serializers.DictField(child=serializers.CharField(allow_blank=True))


# Element kinds the editor can place (mirrors the frontend field-type catalogue).
# The nomination axes (nomination/discipline/group/age category) are one composite
# "nomination_block" field whose chosen parts live in ``config``.
_FIELD_TYPES = [
    "participant_name",
    # Only an individual diploma may place this; the per-kind policy is what rejects
    # it on any other layout (see ``composition.replace_template_layout``).
    "member_name",
    "participant_age",
    "teacher",
    "organization",
    "nomination_block",
    "work",
    "competition_name",
    "competition_date",
    "competition_city",
    "award_degree",
    "diploma_issue_date",
    "qr_block",
    "free_text",
]


class FieldStyleSerializer(serializers.Serializer[dict[str, object]]):
    """A field's appearance. fontSize/letterSpacing are PDF points."""

    fontFamily = serializers.CharField(max_length=100, default="Montserrat")
    fontSize = serializers.FloatField(min_value=1, max_value=500, default=24)
    fontWeight = serializers.ChoiceField(choices=["normal", "bold"], default="normal")
    fontStyle = serializers.ChoiceField(choices=["normal", "italic"], default="normal")
    underline = serializers.BooleanField(default=False)
    textAlign = serializers.ChoiceField(choices=["left", "center", "right"], default="center")
    color = serializers.CharField(max_length=9, default="#000000")
    lineHeight = serializers.FloatField(min_value=0.5, max_value=4, default=1.2)
    letterSpacing = serializers.FloatField(min_value=-20, max_value=100, default=0)
    autoShrink = serializers.BooleanField(default=True)
    wrapText = serializers.BooleanField(default=False)


class FieldConfigSerializer(serializers.Serializer[dict[str, object]]):
    """Composite-field configuration. Currently the nomination block: which parts
    to include (``nomination``/``discipline``/``participant_group``/``age_category``)
    and the leading label. Empty for simple fields."""

    parts = serializers.ListField(child=serializers.CharField(max_length=32), required=False, default=list)
    prefix = serializers.CharField(max_length=120, required=False, allow_blank=True, default="")


class LayoutFieldRequestSerializer(serializers.Serializer[dict[str, object]]):
    """One field in a layout save. Coordinates are normalised (0..1)."""

    page = serializers.IntegerField(min_value=1)
    type = serializers.ChoiceField(choices=_FIELD_TYPES)
    binding = serializers.CharField(max_length=64, required=False, allow_blank=True, default="")
    value = serializers.CharField(required=False, allow_blank=True, default="")
    x = serializers.FloatField(min_value=0, max_value=1)
    y = serializers.FloatField(min_value=0, max_value=1)
    width = serializers.FloatField(min_value=0, max_value=1)
    height = serializers.FloatField(min_value=0, max_value=1)
    rotation = serializers.FloatField(required=False, default=0)
    sortOrder = serializers.IntegerField(required=False, default=0, min_value=0)
    style = FieldStyleSerializer(required=False)  # type: ignore[assignment]
    config = FieldConfigSerializer(required=False)


class SaveLayoutRequestSerializer(serializers.Serializer[dict[str, object]]):
    """Whole-layout save: the full list of fields, persisted atomically."""

    # Declared field named "fields"; DRF's metaclass moves it into
    # ``_declared_fields`` so the base ``Serializer.fields`` property is intact.
    fields = LayoutFieldRequestSerializer(many=True)  # type: ignore[assignment]


class TemplateFieldResponseSerializer(serializers.Serializer[dict[str, object]]):
    """A persisted layout field."""

    id = serializers.UUIDField()
    templateId = serializers.UUIDField()
    page = serializers.IntegerField()
    type = serializers.CharField()
    binding = serializers.CharField(allow_blank=True)
    value = serializers.CharField(allow_blank=True)
    x = serializers.FloatField()
    y = serializers.FloatField()
    width = serializers.FloatField()
    height = serializers.FloatField()
    rotation = serializers.FloatField()
    sortOrder = serializers.IntegerField()
    style = FieldStyleSerializer()  # type: ignore[assignment]
    config = FieldConfigSerializer()
    createdAt = serializers.DateTimeField()
    updatedAt = serializers.DateTimeField()


class LayoutResponseSerializer(serializers.Serializer[dict[str, object]]):
    """A template's saved layout and its revision."""

    fields = TemplateFieldResponseSerializer(many=True)  # type: ignore[assignment]
    revision = serializers.IntegerField()


class UploadTemplateDocumentRequestSerializer(serializers.Serializer[dict[str, object]]):
    """Multipart body for uploading a template's backing PDF."""

    file = serializers.FileField()


class TemplateDocumentResponseSerializer(serializers.Serializer[dict[str, object]]):
    """The PDF attached to a template."""

    id = serializers.UUIDField()
    fileReference = serializers.CharField()
    originalFilename = serializers.CharField(allow_blank=True)
    pageCount = serializers.IntegerField()
    uploadedAt = serializers.DateTimeField()


#: The kinds of document a template can produce, **derived** from the domain
#: ``DocumentType`` rather than restated — a new kind is placeable in the editor the
#: moment it exists, which is the whole point of the policy table.
DOCUMENT_TYPES = [kind.value for kind in DocumentType]

#: The kinds this API generates directly: the unnumbered, unverifiable ones. A
#: registry document (any diploma) draws a permanent number and is issued by
#: publishing the results, so routing one here would bypass numbering entirely — the
#: application service rejects it, and this keeps it out of the contract too.
GENERATED_DOCUMENT_TYPES = [kind.value for kind in DocumentType if not policy_for(kind).is_registry_document]


class CreateTemplateRequestSerializer(serializers.Serializer[dict[str, object]]):
    """Body for creating a template in the library."""

    name = serializers.CharField(max_length=160)
    # Required: a layout is authored for one kind of document (a diploma carries a
    # degree field and a QR block, a thank-you letter carries neither), so a
    # template with no declared kind could not be safely rendered as anything.
    type = serializers.ChoiceField(choices=DOCUMENT_TYPES)
    description = serializers.CharField(max_length=500, required=False, allow_blank=True, default="")


class CreateAssignmentRequestSerializer(serializers.Serializer[dict[str, object]]):
    """Body for assigning one template to genres and/or single nominations.

    Which slot the assignment fills is derived from the template's own ``type``, so
    a mismatch is not expressible. Both id lists are lists because a competition's
    genres usually share a design; a single one is a list of one.

    ``categoryIds`` files the template as a genre's default. ``disciplineIds`` files
    it against single nominations, which print on it instead of their genre's
    default — that is how a festival whose nominations are judged by different
    juries gives each the sheet its jury signs. At least one of the two must be
    non-empty; a request naming neither assigns nothing.
    """

    competitionId = serializers.UUIDField()
    categoryIds = serializers.ListField(child=serializers.UUIDField(), required=False, default=list)
    disciplineIds = serializers.ListField(child=serializers.UUIDField(), required=False, default=list)
    templateId = serializers.UUIDField()

    def validate(self, attrs: dict[str, object]) -> dict[str, object]:
        if not attrs.get("categoryIds") and not attrs.get("disciplineIds"):
            raise serializers.ValidationError({"categoryIds": "Выберите хотя бы один жанр или номинацию."})
        return attrs


class TemplateResponseSerializer(serializers.Serializer[dict[str, object]]):
    """A document template in the library."""

    id = serializers.UUIDField()
    name = serializers.CharField()
    description = serializers.CharField(allow_blank=True)
    type = serializers.ChoiceField(choices=DOCUMENT_TYPES)
    usageCount = serializers.IntegerField()
    document = TemplateDocumentResponseSerializer(allow_null=True, required=False)
    updatedAt = serializers.DateTimeField()


class AssignmentResponseSerializer(serializers.Serializer[dict[str, object]]):
    """A template assignment (competition + genre [+ nomination] + kind -> template)."""

    id = serializers.UUIDField()
    competitionId = serializers.UUIDField()
    competition = serializers.CharField(allow_null=True)
    categoryId = serializers.UUIDField()
    nomination = serializers.CharField(allow_null=True)
    #: The single nomination this assignment is narrowed to; null means the whole
    #: genre, which is what every assignment was before nominations could carry one.
    disciplineId = serializers.UUIDField(allow_null=True)
    discipline = serializers.CharField(allow_null=True)
    templateId = serializers.UUIDField()
    templateName = serializers.CharField()
    #: Which document slot of the nomination this assignment fills.
    documentType = serializers.ChoiceField(choices=DOCUMENT_TYPES)
    createdAt = serializers.DateTimeField()
    updatedAt = serializers.DateTimeField()


class GenerateDocumentsRequestSerializer(serializers.Serializer[dict[str, object]]):
    """Body for generating non-registry documents for chosen nominations.

    Diplomas are **not** generated here — they go through the numbered
    print-package endpoint, which this does not touch.
    """

    competitionId = serializers.UUIDField()
    categoryIds = serializers.ListField(child=serializers.UUIDField(), allow_empty=False)
    # Only unnumbered, unverifiable kinds are accepted; any diploma is rejected.
    documentType = serializers.ChoiceField(choices=GENERATED_DOCUMENT_TYPES)
    # Re-render even for performances that already have this document.
    force = serializers.BooleanField(required=False, default=False)
    #: Also archive the run's documents into one ZIP for offline printing, reported
    #: as ``zipUrl``. Independent of ``publish``.
    bundle = serializers.BooleanField(required=False, default=False)
    #: Show the documents to the participants. Off for a run that only prepares
    #: sheets to print: they are generated and stored, but stay out of the cabinets
    #: until a later run publishes them. Never withdraws an existing publication.
    publish = serializers.BooleanField(required=False, default=True)


class GenerateDocumentsResponseSerializer(serializers.Serializer[dict[str, object]]):
    """Outcome of a generation run.

    Counts documents, not performances: a kind addressed to a person issues one per
    recipient, so an entry naming two teachers contributes two.
    """

    documentType = serializers.ChoiceField(choices=DOCUMENT_TYPES)
    created = serializers.IntegerField()
    regenerated = serializers.IntegerField()
    #: Entries that named nobody to address, so nothing was issued for them.
    withoutRecipient = serializers.IntegerField()
    #: Entries skipped because neither their nomination nor their genre assigns a
    #: template of this kind.
    withoutTemplate = serializers.IntegerField()
    nominations = serializers.IntegerField()
    #: Documents the chosen nominations now hold — what a bundle would contain,
    #: which is more than ``created + regenerated`` on a repeat run.
    documents = serializers.IntegerField()
    #: Documents this run made visible to participants. Zero for a print-only run,
    #: and the only non-zero count when publishing what a print run had rendered.
    published = serializers.IntegerField()
    #: The printable archive's ``/media/…`` path; null unless ``bundle`` was asked
    #: for (or the run produced nothing to archive).
    zipUrl = serializers.CharField(allow_null=True)


class GenerationRunResponseSerializer(serializers.Serializer[dict[str, object]]):
    """One completed generation run, as the archive lists it.

    Covers every kind of run — the numbered diploma package and the thank-you runs —
    so the counts are per document rather than per diploma. ``zipUrl`` is null for a
    run that produced no archive to download (a publish-only thank-you run).
    """

    id = serializers.UUIDField()
    documentType = serializers.ChoiceField(choices=DOCUMENT_TYPES)
    competitionId = serializers.UUIDField()
    #: The competition's current title; null if it has since been deleted.
    competition = serializers.CharField(allow_null=True)
    nominations = serializers.IntegerField()
    documents = serializers.IntegerField()
    created = serializers.IntegerField()
    published = serializers.IntegerField()
    zipUrl = serializers.CharField(allow_null=True)
    #: Who ran it, as named at the time; null when the actor is unknown.
    user = serializers.CharField(allow_null=True)
    createdAt = serializers.DateTimeField()


# --- Diploma registry -------------------------------------------------------


class _ParticipantSnapshotSerializer(serializers.Serializer[dict[str, object]]):
    display_name = serializers.CharField(allow_blank=True)
    age = serializers.IntegerField(allow_null=True)


class _TeacherSnapshotSerializer(serializers.Serializer[dict[str, object]]):
    name = serializers.CharField(allow_blank=True)
    role = serializers.CharField(allow_null=True)


class _OrganizationSnapshotSerializer(serializers.Serializer[dict[str, object]]):
    name = serializers.CharField(allow_null=True)


class _NominationSnapshotSerializer(serializers.Serializer[dict[str, object]]):
    title = serializers.CharField(allow_null=True)
    discipline = serializers.CharField(allow_null=True)
    participant_group = serializers.CharField(allow_null=True)
    age_category = serializers.CharField(allow_null=True)


class _PerformanceSnapshotSerializer(serializers.Serializer[dict[str, object]]):
    title = serializers.CharField(allow_null=True)


class _CompetitionSnapshotSerializer(serializers.Serializer[dict[str, object]]):
    title = serializers.CharField(allow_null=True)
    date = serializers.CharField(allow_null=True)
    city = serializers.CharField(allow_null=True)


class _AwardSnapshotSerializer(serializers.Serializer[dict[str, object]]):
    # Null until the jury has decided — a normal state.
    degree = serializers.CharField(allow_null=True)


class DiplomaSnapshotSerializer(serializers.Serializer[dict[str, object]]):
    """The frozen dataset a diploma is printed from (values only, no ids)."""

    participant = _ParticipantSnapshotSerializer()
    teachers = _TeacherSnapshotSerializer(many=True)
    organization = _OrganizationSnapshotSerializer()
    nomination = _NominationSnapshotSerializer()
    performance = _PerformanceSnapshotSerializer()
    competition = _CompetitionSnapshotSerializer()
    award = _AwardSnapshotSerializer()


class DiplomaResponseSerializer(serializers.Serializer[dict[str, object]]):
    """A diploma in the registry."""

    id = serializers.UUIDField()
    number = serializers.CharField()
    verificationToken = serializers.CharField()
    competitionId = serializers.UUIDField()
    submissionId = serializers.UUIDField()
    templateId = serializers.UUIDField()
    status = serializers.ChoiceField(choices=["DRAFT", "GENERATED", "ISSUED", "CANCELLED"])
    snapshot = DiplomaSnapshotSerializer()
    printPdfPath = serializers.CharField(allow_null=True, allow_blank=True)
    officialPdfPath = serializers.CharField(allow_null=True, allow_blank=True)
    issuedAt = serializers.DateTimeField(allow_null=True)
    createdAt = serializers.DateTimeField()
    updatedAt = serializers.DateTimeField()


class CreateDiplomaRequestSerializer(serializers.Serializer[dict[str, object]]):
    """Body for creating one diploma from a submission (no PDF, no bulk)."""

    submissionId = serializers.UUIDField()
    templateId = serializers.UUIDField()


class PrintPackageRequestSerializer(serializers.Serializer[dict[str, object]]):
    """Body for starting a mass print-package generation for a competition.

    ``categoryIds`` selects nominations; empty means every nomination that has an
    assigned template."""

    competitionId = serializers.UUIDField()
    categoryIds = serializers.ListField(child=serializers.UUIDField(), required=False, default=list)
    # Re-render print PDFs even for diplomas that already have one.
    force = serializers.BooleanField(required=False, default=False)


class PrintJobResponseSerializer(serializers.Serializer[dict[str, object]]):
    """A print-package job's status and result (poll until COMPLETED/FAILED)."""

    jobId = serializers.UUIDField()
    competitionId = serializers.UUIDField()
    categoryIds = serializers.ListField(child=serializers.UUIDField())
    force = serializers.BooleanField()
    status = serializers.ChoiceField(choices=["PENDING", "RUNNING", "COMPLETED", "FAILED"])
    created = serializers.IntegerField()
    skipped = serializers.IntegerField()
    zipUrl = serializers.CharField(allow_null=True)
    error = serializers.CharField(allow_null=True)
    createdAt = serializers.DateTimeField()
    updatedAt = serializers.DateTimeField()


class SlotDisciplineSerializer(serializers.Serializer[dict[str, object]]):
    """One nomination that prints this kind on a template of its own."""

    disciplineId = serializers.UUIDField()
    discipline = serializers.CharField(allow_null=True)
    templateId = serializers.UUIDField()
    templateName = serializers.CharField()
    # True when that template also has an uploaded PDF.
    ready = serializers.BooleanField()


class DocumentSlotSerializer(serializers.Serializer[dict[str, object]]):
    """One genre's readiness and forecast for a single document type."""

    #: The genre's default template; null when only its nominations assign one.
    templateId = serializers.UUIDField(allow_null=True)
    templateName = serializers.CharField(allow_null=True)
    # True when a template of this type is assigned at either level AND it has an
    # uploaded PDF.
    ready = serializers.BooleanField()
    existing = serializers.IntegerField()
    willCreate = serializers.IntegerField()
    # Entries a per-teacher type cannot address (no teacher named); else 0.
    withoutRecipient = serializers.IntegerField()
    #: Entries this kind cannot be printed for: their nomination resolves to no
    #: template, or to one with no PDF behind it.
    withoutTemplate = serializers.IntegerField()
    #: The nominations printing on something other than the genre's default.
    disciplines = SlotDisciplineSerializer(many=True)


class PrintPackageNominationSerializer(serializers.Serializer[dict[str, object]]):
    """One genre's stats, with a slot per document type.

    Readiness is per type because assignment is: a genre can be ready to print
    diplomas and have no thank-you template at all.
    """

    categoryId = serializers.UUIDField()
    nomination = serializers.CharField(allow_null=True)
    submissions = serializers.IntegerField()
    diploma = DocumentSlotSerializer()
    #: One per person the applicants named inside their collectives — nought where
    #: nobody was named, which is how an entry opts out.
    individualDiploma = DocumentSlotSerializer()
    thankYou = DocumentSlotSerializer()


class PrintPackageSummaryResponseSerializer(serializers.Serializer[dict[str, object]]):
    """Per-nomination print-package summary for a competition."""

    competitionId = serializers.UUIDField()
    nominations = PrintPackageNominationSerializer(many=True)
