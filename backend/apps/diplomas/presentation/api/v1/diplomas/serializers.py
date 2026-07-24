"""Request/response serializers for the Diplomas workspace REST surface.

Hand-written ``serializers.Serializer`` classes (not ``ModelSerializer``) with
camelCase fields, matching the platform's API contract (API-000). The response
serializers exist only to document the OpenAPI schema drf-spectacular emits; the
views build their payload dicts directly in :mod:`composition`.
"""

from __future__ import annotations

from rest_framework import serializers

__all__ = [
    "AssignmentResponseSerializer",
    "CreateAssignmentRequestSerializer",
    "CreateDiplomaRequestSerializer",
    "CreateTemplateRequestSerializer",
    "DiplomaResponseSerializer",
    "DiplomaSnapshotSerializer",
    "LayoutResponseSerializer",
    "PreviewApplicationSerializer",
    "PreviewBindingsSerializer",
    "PrintJobResponseSerializer",
    "PrintPackageRequestSerializer",
    "PrintPackageSummaryResponseSerializer",
    "SaveLayoutRequestSerializer",
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
    config = FieldConfigSerializer(required=False)  # type: ignore[assignment]


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
    config = FieldConfigSerializer()  # type: ignore[assignment]
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


class CreateTemplateRequestSerializer(serializers.Serializer[dict[str, object]]):
    """Body for creating a template in the library."""

    name = serializers.CharField(max_length=160)
    description = serializers.CharField(max_length=500, required=False, allow_blank=True, default="")


class CreateAssignmentRequestSerializer(serializers.Serializer[dict[str, object]]):
    """Body for creating a template assignment."""

    competitionId = serializers.UUIDField()
    categoryId = serializers.UUIDField()
    templateId = serializers.UUIDField()


class TemplateResponseSerializer(serializers.Serializer[dict[str, object]]):
    """A diploma template in the library."""

    id = serializers.UUIDField()
    name = serializers.CharField()
    description = serializers.CharField(allow_blank=True)
    usageCount = serializers.IntegerField()
    document = TemplateDocumentResponseSerializer(allow_null=True, required=False)
    updatedAt = serializers.DateTimeField()


class AssignmentResponseSerializer(serializers.Serializer[dict[str, object]]):
    """A template assignment (competition + nomination -> template)."""

    id = serializers.UUIDField()
    competitionId = serializers.UUIDField()
    competition = serializers.CharField(allow_null=True)
    categoryId = serializers.UUIDField()
    nomination = serializers.CharField(allow_null=True)
    templateId = serializers.UUIDField()
    templateName = serializers.CharField()
    createdAt = serializers.DateTimeField()
    updatedAt = serializers.DateTimeField()


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
    teachers = _TeacherSnapshotSerializer(many=True)  # type: ignore[assignment]
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
    snapshot = DiplomaSnapshotSerializer()  # type: ignore[assignment]
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


class PrintPackageNominationSerializer(serializers.Serializer[dict[str, object]]):
    """One nomination's print-package stats."""

    categoryId = serializers.UUIDField()
    nomination = serializers.CharField(allow_null=True)
    templateId = serializers.UUIDField(allow_null=True)
    templateName = serializers.CharField(allow_null=True)
    # True when a template is assigned AND it has an uploaded PDF.
    ready = serializers.BooleanField()
    submissions = serializers.IntegerField()
    existing = serializers.IntegerField()
    willCreate = serializers.IntegerField()


class PrintPackageSummaryResponseSerializer(serializers.Serializer[dict[str, object]]):
    """Per-nomination print-package summary for a competition."""

    competitionId = serializers.UUIDField()
    nominations = PrintPackageNominationSerializer(many=True)  # type: ignore[assignment]
