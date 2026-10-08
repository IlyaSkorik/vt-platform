"""Domain events emitted by the Competitions bounded context.

Past-tense **business facts** (ARCH-001 §4.8) — something already happened to the
:class:`~apps.competitions.domain.entities.Competition` aggregate; an event names
it, timestamps it, and carries just enough data for a consumer to react without
reaching back into this context.

**Pure domain code** (ARCH-001 §4.1, §7.2): standard library only. There are no
handlers, subscribers, dispatchers, or transport here — publishing is an outer-
layer concern; the domain only *produces* the fact. Every event is a frozen,
slotted, keyword-only dataclass: immutable, self-describing (via
:meth:`DomainEvent.to_dict`), and value-comparable.

Only *meaningful* facts are events. Fine-grained taxonomy edits (add a category,
rename a discipline) stay internal bookkeeping — the aggregate does not emit them.
But the admissibility/pricing structure and the lifecycle milestones are events
that the future Applications/Payments/Scheduling contexts will react to, so
admission/pricing/format/service changes and every lifecycle transition are
published.

Common envelope (:class:`DomainEvent`):

* ``event_id``      — unique **UUID v7** identity of this occurrence (dedup key).
* ``occurred_at``   — timezone-aware **UTC** instant the fact happened.
* ``aggregate_id``  — the UUID of the aggregate the fact is about.
* ``event_version`` — schema version of the payload, for evolution.
"""

from __future__ import annotations

import dataclasses
import uuid
from dataclasses import dataclass, field
from datetime import UTC, date, datetime
from enum import StrEnum

from .value_objects import (
    AgeCategoryId,
    CategoryId,
    CompetitionStatus,
    CompetitionTitle,
    ContactId,
    ContactType,
    ContactValue,
    Currency,
    DisciplineId,
    InformationBlockId,
    InformationBlockTitle,
    OrganizerId,
    ParticipantGroupId,
    ParticipationFormatId,
    PricingCalculationType,
    RegulationId,
    RegulationTitle,
    RegulationVersion,
    Season,
    ServiceBillingModel,
    ServiceId,
    ServiceName,
    _generate_uuid7,
)

__all__ = [
    "AdditionalServiceAdded",
    "AdmissionRuleAdded",
    "AdmissionRuleRemoved",
    "CompetitionBrandingChanged",
    "CompetitionCompleted",
    "CompetitionContactAdded",
    "CompetitionContactRemoved",
    "CompetitionContactsConfigChanged",
    "CompetitionCreated",
    "CompetitionDeadlineChanged",
    "CompetitionGeneralInformationUpdated",
    "CompetitionInformationHidden",
    "CompetitionInformationPublished",
    "CompetitionLandingConfigurationChanged",
    "CompetitionPublished",
    "CompetitionSettingsChanged",
    "CompetitionStarted",
    "DomainEvent",
    "NominationRegistrationResumed",
    "NominationRegistrationScheduled",
    "NominationRegistrationStopped",
    "NominationWaitlistDisabled",
    "NominationWaitlistEnabled",
    "ParticipationFormatDisabled",
    "ParticipationFormatEnabled",
    "PricingRuleAdded",
    "PricingRuleRemoved",
    "RegulationPublished",
]


def _utcnow() -> datetime:
    """The current instant as a timezone-aware **UTC** datetime (default factory)."""
    return datetime.now(UTC)


def _serialize(value: object) -> object:
    """Render a single field value as a JSON-safe primitive.

    Maps domain value objects and stdlib temporal/identity types to strings;
    plain scalars pass through. Raises :class:`TypeError` on anything unmapped so
    a non-serializable payload fails loudly rather than silently producing junk.
    """
    match value:
        case None:
            return None
        case StrEnum():
            return value.value
        case bool() | int() | float() | str():
            return value
        case datetime():
            return value.isoformat()
        case date():
            return value.isoformat()
        case uuid.UUID():
            return str(value)
        case (
            OrganizerId()
            | RegulationId()
            | CategoryId()
            | DisciplineId()
            | AgeCategoryId()
            | ParticipantGroupId()
            | ParticipationFormatId()
            | ServiceId()
            | ContactId()
            | InformationBlockId()
        ):
            return value.json()
        case CompetitionTitle() | Season() | RegulationTitle() | RegulationVersion() | ServiceName() | ContactValue() | InformationBlockTitle():
            return str(value)
    raise TypeError(f"Cannot serialize event field of type {type(value).__name__!r}.")


@dataclass(frozen=True, slots=True, kw_only=True)
class DomainEvent:
    """Common, immutable envelope shared by every Competitions domain event."""

    aggregate_id: uuid.UUID
    event_id: uuid.UUID = field(default_factory=_generate_uuid7)
    occurred_at: datetime = field(default_factory=_utcnow)
    event_version: int = 1

    def to_dict(self) -> dict[str, object]:
        """Render a JSON-safe payload with an ``event_type`` discriminator.

        Every dataclass field is serialized via :func:`_serialize`; the concrete
        event's class name is added as ``event_type`` so a consumer (outbox, log,
        wire) can route without importing the class.
        """
        payload = {name: _serialize(getattr(self, name)) for name in (f.name for f in dataclasses.fields(self))}
        payload["event_type"] = type(self).__name__
        return payload


# ---------------------------------------------------------------------------
# Competition lifecycle events
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True, kw_only=True)
class CompetitionCreated(DomainEvent):
    """A competition was created as a DRAFT by an organizer."""

    title: CompetitionTitle
    season: Season
    organizer_id: OrganizerId


@dataclass(frozen=True, slots=True, kw_only=True)
class CompetitionGeneralInformationUpdated(DomainEvent):
    """A competition's general information (title, dates, media, venue, …) was edited."""


@dataclass(frozen=True, slots=True, kw_only=True)
class CompetitionPublished(DomainEvent):
    """A competition's configuration was finalized and it opened to applicants."""

    previous_status: CompetitionStatus


@dataclass(frozen=True, slots=True, kw_only=True)
class NominationRegistrationScheduled(DomainEvent):
    """A nomination's registration window (open/close instants) was set or changed."""

    category_id: CategoryId
    opens_at: datetime | None
    closes_at: datetime | None


@dataclass(frozen=True, slots=True, kw_only=True)
class NominationRegistrationStopped(DomainEvent):
    """A nomination's registration was stopped early by the organizer."""

    category_id: CategoryId


@dataclass(frozen=True, slots=True, kw_only=True)
class NominationRegistrationResumed(DomainEvent):
    """A previously stopped nomination's registration was resumed."""

    category_id: CategoryId


@dataclass(frozen=True, slots=True, kw_only=True)
class NominationWaitlistEnabled(DomainEvent):
    """A nomination now keeps a waitlist for applicants who missed its registration."""

    category_id: CategoryId


@dataclass(frozen=True, slots=True, kw_only=True)
class NominationWaitlistDisabled(DomainEvent):
    """A nomination stopped taking waitlist entries; those already on it remain."""

    category_id: CategoryId


@dataclass(frozen=True, slots=True, kw_only=True)
class CompetitionStarted(DomainEvent):
    """The competition began running."""


@dataclass(frozen=True, slots=True, kw_only=True)
class CompetitionCompleted(DomainEvent):
    """The competition finished."""


@dataclass(frozen=True, slots=True, kw_only=True)
class RegulationPublished(DomainEvent):
    """A new version of the competition regulations was published (and made current)."""

    regulation_id: RegulationId
    title: RegulationTitle
    version: RegulationVersion
    publication_date: date


# ---------------------------------------------------------------------------
# Configuration events (admissibility, pricing, formats, services)
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True, kw_only=True)
class AdmissionRuleAdded(DomainEvent):
    """A combination became admissible (an admission rule was added)."""

    category_id: CategoryId
    discipline_id: DisciplineId
    age_category_id: AgeCategoryId
    participant_group_id: ParticipantGroupId
    participation_format_id: ParticipationFormatId


@dataclass(frozen=True, slots=True, kw_only=True)
class AdmissionRuleRemoved(DomainEvent):
    """A combination is no longer admissible (an admission rule was removed)."""

    category_id: CategoryId
    discipline_id: DisciplineId
    age_category_id: AgeCategoryId
    participant_group_id: ParticipantGroupId
    participation_format_id: ParticipationFormatId


@dataclass(frozen=True, slots=True, kw_only=True)
class PricingRuleAdded(DomainEvent):
    """A unit price was set for a combination."""

    category_id: CategoryId
    discipline_id: DisciplineId
    age_category_id: AgeCategoryId
    participant_group_id: ParticipantGroupId
    participation_format_id: ParticipationFormatId
    amount: str
    currency: Currency
    calculation_type: PricingCalculationType = PricingCalculationType.PER_PARTICIPANT


@dataclass(frozen=True, slots=True, kw_only=True)
class PricingRuleRemoved(DomainEvent):
    """A per-participant price was removed for a combination."""

    category_id: CategoryId
    discipline_id: DisciplineId
    age_category_id: AgeCategoryId
    participant_group_id: ParticipantGroupId
    participation_format_id: ParticipationFormatId


@dataclass(frozen=True, slots=True, kw_only=True)
class ParticipationFormatEnabled(DomainEvent):
    """A participation format was enabled for the competition."""

    participation_format_id: ParticipationFormatId


@dataclass(frozen=True, slots=True, kw_only=True)
class ParticipationFormatDisabled(DomainEvent):
    """A participation format was disabled for the competition."""

    participation_format_id: ParticipationFormatId


@dataclass(frozen=True, slots=True, kw_only=True)
class AdditionalServiceAdded(DomainEvent):
    """An optional paid service was added to the competition."""

    service_id: ServiceId
    name: ServiceName
    amount: str
    currency: Currency
    enabled: bool
    billing_model: ServiceBillingModel = ServiceBillingModel.PER_PARTICIPANT
    required: bool = False
    sort_order: int = 0


# ---------------------------------------------------------------------------
# Settings, deadlines, contacts, public information, branding
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True, kw_only=True)
class CompetitionSettingsChanged(DomainEvent):
    """The competition's behaviour settings were replaced."""


@dataclass(frozen=True, slots=True, kw_only=True)
class CompetitionContactsConfigChanged(DomainEvent):
    """The competition's contacts-module configuration was replaced."""


@dataclass(frozen=True, slots=True, kw_only=True)
class CompetitionLandingConfigurationChanged(DomainEvent):
    """The competition's public-landing configuration was replaced."""


@dataclass(frozen=True, slots=True, kw_only=True)
class CompetitionDeadlineChanged(DomainEvent):
    """The competition's registration deadlines were changed."""


@dataclass(frozen=True, slots=True, kw_only=True)
class CompetitionContactAdded(DomainEvent):
    """An official contact was added to the competition."""

    contact_id: ContactId
    contact_type: ContactType
    value: ContactValue
    is_primary: bool


@dataclass(frozen=True, slots=True, kw_only=True)
class CompetitionContactRemoved(DomainEvent):
    """An official contact was removed from the competition."""

    contact_id: ContactId


@dataclass(frozen=True, slots=True, kw_only=True)
class CompetitionInformationPublished(DomainEvent):
    """A public-information block was published (made visible)."""

    block_id: InformationBlockId
    title: InformationBlockTitle


@dataclass(frozen=True, slots=True, kw_only=True)
class CompetitionInformationHidden(DomainEvent):
    """A public-information block was hidden (unpublished)."""

    block_id: InformationBlockId


@dataclass(frozen=True, slots=True, kw_only=True)
class CompetitionBrandingChanged(DomainEvent):
    """The competition's branding (logo/banner/poster) was changed."""
