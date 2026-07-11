"""Command DTOs for the Competitions bounded context.

Input shapes for state-changing use cases. Framework-neutral, frozen, slotted
dataclasses carrying only primitives — no domain value objects (handlers build
those, translating validation errors) and no framework types. Optional fields use
``None`` sentinels; the corresponding domain methods replace the field wholesale,
so a ``None`` clears it.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime

__all__ = [
    "AddAdditionalServiceCommand",
    "AddAdmissionRuleCommand",
    "AddAgeCategoryCommand",
    "AddCategoryCommand",
    "AddContactCommand",
    "AddDisciplineCommand",
    "AddDocumentCommand",
    "AddInformationBlockCommand",
    "AddParticipantGroupCommand",
    "AddPricingRuleCommand",
    "AddRegulationCommand",
    "ArchiveCompetitionCommand",
    "ChangePriceCommand",
    "CloseRegistrationCommand",
    "CompleteCompetitionCommand",
    "CreateCompetitionCommand",
    "DisableAdditionalServiceCommand",
    "DisableFormatCommand",
    "EnableAdditionalServiceCommand",
    "EnableFormatCommand",
    "HideInformationBlockCommand",
    "MakeRegulationCurrentCommand",
    "MarkConfiguredCommand",
    "MarkReadyCommand",
    "OpenRegistrationCommand",
    "PublishCompetitionCommand",
    "PublishDocumentCommand",
    "PublishInformationBlockCommand",
    "RemoveAdditionalServiceCommand",
    "RemoveAdmissionRuleCommand",
    "RemoveAgeCategoryCommand",
    "RemoveCategoryCommand",
    "RemoveContactCommand",
    "RemoveDisciplineCommand",
    "RemoveDocumentCommand",
    "RemoveInformationBlockCommand",
    "RemoveParticipantGroupCommand",
    "RemovePricingRuleCommand",
    "RemoveRegulationCommand",
    "RenameCategoryCommand",
    "RenameDisciplineCommand",
    "RevertToConfiguredCommand",
    "RevertToDraftCommand",
    "SetPrimaryContactCommand",
    "StartCompetitionCommand",
    "UnpublishDocumentCommand",
    "UpdateAdditionalServiceCommand",
    "UpdateAgeCategoryCommand",
    "UpdateBrandingCommand",
    "UpdateDeadlinesCommand",
    "UpdateDocumentCommand",
    "UpdateGeneralInformationCommand",
    "UpdateInformationBlockCommand",
    "UpdateSettingsCommand",
]


# ---------------------------------------------------------------------------
# Creation & general information
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class CreateCompetitionCommand:
    """Create a new DRAFT competition owned by ``organizer_id``."""

    organizer_id: str
    title: str
    season: str
    description: str | None = None


@dataclass(frozen=True, slots=True)
class UpdateGeneralInformationCommand:
    """Replace the competition's general information wholesale."""

    competition_id: str
    title: str
    season: str
    description: str | None = None
    logo: str | None = None
    banner: str | None = None
    venue_name: str | None = None
    venue_address: str | None = None
    registration_start: date | None = None
    registration_end: date | None = None
    competition_start: date | None = None
    competition_end: date | None = None


@dataclass(frozen=True, slots=True)
class UpdateBrandingCommand:
    """Replace the competition's branding assets (logo, banner, poster)."""

    competition_id: str
    logo: str | None = None
    banner: str | None = None
    poster: str | None = None


@dataclass(frozen=True, slots=True)
class UpdateSettingsCommand:
    """Replace the competition's behaviour settings wholesale (all flags supplied)."""

    competition_id: str
    allow_multiple_applications: bool
    allow_application_editing: bool
    allow_music_replacement: bool
    allow_video_replacement: bool
    allow_participant_changes: bool
    require_music_upload: bool
    require_video_upload: bool
    require_photo_upload: bool
    require_identity_document: bool
    require_parent_consent: bool
    require_teacher: bool
    require_comment_for_application: bool


@dataclass(frozen=True, slots=True)
class UpdateDeadlinesCommand:
    """Replace the competition's registration deadlines wholesale."""

    competition_id: str
    application: datetime | None = None
    payment: datetime | None = None
    music_upload: datetime | None = None
    document_upload: datetime | None = None
    correction: datetime | None = None


# ---------------------------------------------------------------------------
# Taxonomy (nominations = categories, disciplines, age categories, groups)
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class AddCategoryCommand:
    competition_id: str
    name: str
    description: str | None = None
    sort_order: int | None = None


@dataclass(frozen=True, slots=True)
class RenameCategoryCommand:
    competition_id: str
    category_id: str
    name: str | None = None
    description: str | None = None
    sort_order: int | None = None


@dataclass(frozen=True, slots=True)
class RemoveCategoryCommand:
    competition_id: str
    category_id: str


@dataclass(frozen=True, slots=True)
class AddDisciplineCommand:
    competition_id: str
    category_id: str
    name: str
    sort_order: int | None = None


@dataclass(frozen=True, slots=True)
class RenameDisciplineCommand:
    competition_id: str
    discipline_id: str
    name: str | None = None
    sort_order: int | None = None


@dataclass(frozen=True, slots=True)
class RemoveDisciplineCommand:
    competition_id: str
    discipline_id: str


@dataclass(frozen=True, slots=True)
class AddAgeCategoryCommand:
    competition_id: str
    category_id: str
    name: str
    min_age: int
    max_age: int
    age_category_type: str = "STANDARD"
    mixed_calculation_method: str | None = None
    sort_order: int | None = None


@dataclass(frozen=True, slots=True)
class UpdateAgeCategoryCommand:
    competition_id: str
    age_category_id: str
    name: str | None = None
    min_age: int | None = None
    max_age: int | None = None
    age_category_type: str | None = None
    mixed_calculation_method: str | None = None
    sort_order: int | None = None


@dataclass(frozen=True, slots=True)
class RemoveAgeCategoryCommand:
    competition_id: str
    age_category_id: str


@dataclass(frozen=True, slots=True)
class AddParticipantGroupCommand:
    competition_id: str
    category_id: str
    name: str
    min_count: int
    max_count: int | None = None


@dataclass(frozen=True, slots=True)
class RemoveParticipantGroupCommand:
    competition_id: str
    participant_group_id: str


# ---------------------------------------------------------------------------
# Participation formats
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class EnableFormatCommand:
    competition_id: str
    participation_format: str


@dataclass(frozen=True, slots=True)
class DisableFormatCommand:
    competition_id: str
    participation_format: str


# ---------------------------------------------------------------------------
# Admission & pricing rules
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class AddAdmissionRuleCommand:
    competition_id: str
    category_id: str
    discipline_id: str
    age_category_id: str
    participant_group_id: str
    participation_format: str


@dataclass(frozen=True, slots=True)
class RemoveAdmissionRuleCommand:
    competition_id: str
    category_id: str
    discipline_id: str
    age_category_id: str
    participant_group_id: str
    participation_format: str


@dataclass(frozen=True, slots=True)
class AddPricingRuleCommand:
    competition_id: str
    category_id: str
    discipline_id: str
    age_category_id: str
    participant_group_id: str
    participation_format: str
    amount: str
    currency: str = "BYN"


@dataclass(frozen=True, slots=True)
class ChangePriceCommand:
    competition_id: str
    category_id: str
    discipline_id: str
    age_category_id: str
    participant_group_id: str
    participation_format: str
    amount: str
    currency: str = "BYN"


@dataclass(frozen=True, slots=True)
class RemovePricingRuleCommand:
    competition_id: str
    category_id: str
    discipline_id: str
    age_category_id: str
    participant_group_id: str
    participation_format: str


# ---------------------------------------------------------------------------
# Regulations & documents
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class AddRegulationCommand:
    competition_id: str
    title: str
    version: str
    publication_date: date
    file_reference: str


@dataclass(frozen=True, slots=True)
class MakeRegulationCurrentCommand:
    competition_id: str
    regulation_id: str


@dataclass(frozen=True, slots=True)
class RemoveRegulationCommand:
    competition_id: str
    regulation_id: str


@dataclass(frozen=True, slots=True)
class AddDocumentCommand:
    competition_id: str
    title: str
    category: str
    visibility: str
    file_reference: str
    description: str | None = None
    sort_order: int = 0
    published: bool = False


@dataclass(frozen=True, slots=True)
class UpdateDocumentCommand:
    competition_id: str
    document_id: str
    title: str
    category: str
    visibility: str
    file_reference: str
    description: str | None = None
    sort_order: int = 0


@dataclass(frozen=True, slots=True)
class PublishDocumentCommand:
    competition_id: str
    document_id: str


@dataclass(frozen=True, slots=True)
class UnpublishDocumentCommand:
    competition_id: str
    document_id: str


@dataclass(frozen=True, slots=True)
class RemoveDocumentCommand:
    competition_id: str
    document_id: str


# ---------------------------------------------------------------------------
# Additional services
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class AddAdditionalServiceCommand:
    competition_id: str
    name: str
    amount: str
    currency: str = "BYN"
    description: str | None = None
    enabled: bool = True


@dataclass(frozen=True, slots=True)
class UpdateAdditionalServiceCommand:
    competition_id: str
    service_id: str
    name: str
    amount: str
    currency: str = "BYN"
    description: str | None = None


@dataclass(frozen=True, slots=True)
class EnableAdditionalServiceCommand:
    competition_id: str
    service_id: str


@dataclass(frozen=True, slots=True)
class DisableAdditionalServiceCommand:
    competition_id: str
    service_id: str


@dataclass(frozen=True, slots=True)
class RemoveAdditionalServiceCommand:
    competition_id: str
    service_id: str


# ---------------------------------------------------------------------------
# Contacts
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class AddContactCommand:
    competition_id: str
    contact_type: str
    value: str
    is_primary: bool = False


@dataclass(frozen=True, slots=True)
class SetPrimaryContactCommand:
    competition_id: str
    contact_id: str


@dataclass(frozen=True, slots=True)
class RemoveContactCommand:
    competition_id: str
    contact_id: str


# ---------------------------------------------------------------------------
# Public information blocks
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class AddInformationBlockCommand:
    competition_id: str
    title: str
    content: str
    content_format: str = "PLAIN"
    published: bool = False
    sort_order: int = 0


@dataclass(frozen=True, slots=True)
class UpdateInformationBlockCommand:
    competition_id: str
    block_id: str
    title: str
    content: str
    content_format: str = "PLAIN"
    sort_order: int = 0


@dataclass(frozen=True, slots=True)
class PublishInformationBlockCommand:
    competition_id: str
    block_id: str


@dataclass(frozen=True, slots=True)
class HideInformationBlockCommand:
    competition_id: str
    block_id: str


@dataclass(frozen=True, slots=True)
class RemoveInformationBlockCommand:
    competition_id: str
    block_id: str


# ---------------------------------------------------------------------------
# Lifecycle
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class MarkConfiguredCommand:
    competition_id: str


@dataclass(frozen=True, slots=True)
class RevertToDraftCommand:
    competition_id: str


@dataclass(frozen=True, slots=True)
class MarkReadyCommand:
    competition_id: str


@dataclass(frozen=True, slots=True)
class RevertToConfiguredCommand:
    competition_id: str


@dataclass(frozen=True, slots=True)
class PublishCompetitionCommand:
    competition_id: str


@dataclass(frozen=True, slots=True)
class OpenRegistrationCommand:
    competition_id: str


@dataclass(frozen=True, slots=True)
class CloseRegistrationCommand:
    competition_id: str


@dataclass(frozen=True, slots=True)
class StartCompetitionCommand:
    competition_id: str


@dataclass(frozen=True, slots=True)
class CompleteCompetitionCommand:
    competition_id: str


@dataclass(frozen=True, slots=True)
class ArchiveCompetitionCommand:
    competition_id: str
