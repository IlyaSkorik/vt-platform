"""Domain entities for the Participants bounded context.

The :class:`Participant` aggregate root (ARCH-001 §7.2, §13.4; DIA-001 §4.2) — the
framework-free business core of a child participant. It **owns all state and
behaviour** and is the sole guardian of the participant's invariants: every rule
about when a participant may be verified, activated, archived, or erased, and how
guardian relationships and consent gate activation, lives here — not in a service,
serializer, or model.

This is **pure domain code** (ARCH-001 §4.1, §7.2): standard library only — no
Django, no DRF, no ORM, no clock, no IO, no global state. Time is always supplied
by the caller (``now``) so the aggregate is deterministic and trivially testable.

Design contract (mirrors the Identity reference aggregate):

* **No direct construction.** Build a ``Participant`` only via
  :meth:`Participant.create` (a brand-new participant, which validates invariants
  and emits :class:`~apps.participants.domain.events.ParticipantCreated`) or
  :meth:`Participant.rehydrate` (reconstruction from persistence, which
  re-validates nothing and emits nothing).
* **Encapsulated state.** All fields are private; only read-only properties are
  exposed. Guardian relationships are held as an immutable tuple of
  :class:`~apps.participants.domain.value_objects.GuardianLink` value objects.
* **Behaviour returns events, never publishes them.** Each business method
  validates invariants, consults the relevant policy where one applies, mutates
  internal state, bumps ``updated_at`` and the optimistic-concurrency ``version``,
  and returns the ``list`` of domain events describing what happened.
* **Invalid transitions raise** typed
  :class:`~apps.participants.domain.exceptions.ParticipantStateError` subclasses.

Lifecycle (DATA-004 §4.3): ``Created → Verified → Active → Archived → Erased``,
with ``Archived → Active`` reactivation and ``Erased`` terminal.

Policy boundaries: activation consults
:class:`~apps.participants.domain.policies.GuardianshipPolicy` (PRT-001), whose
inputs the aggregate owns; alias assignment consults
:class:`~apps.participants.domain.policies.PseudonymizationPolicy` (JDG-006); age
group is derived on demand via
:class:`~apps.participants.domain.policies.AgeGroupPolicy` (PRT-002) and never
stored, since it is always relative to a competition's reference date.
"""

from __future__ import annotations

import uuid
from dataclasses import InitVar, dataclass
from datetime import datetime
from typing import Final

from .events import (
    DomainEvent,
    GuardianLinked,
    ParticipantActivated,
    ParticipantArchived,
    ParticipantCreated,
    ParticipantErasureRequested,
    ParticipantVerified,
)
from .exceptions import (
    ActivationRequirementsError,
    AliasRevealsIdentityError,
    ConsentNotRecordedError,
    DirectConstructionError,
    GuardianAlreadyLinkedError,
    GuardianLinkNotFoundError,
    GuardianLinkNotPendingError,
    InvalidDateOfBirthError,
    InvalidParticipantTransitionError,
    ParticipantErasedError,
    ParticipantNotArchivedError,
)
from .policies import AgeGroupPolicy, GuardianshipPolicy, PseudonymizationPolicy
from .value_objects import (
    ActorReference,
    AgeGroup,
    ConsentReference,
    DateOfBirth,
    DisplayAlias,
    GuardianId,
    GuardianLink,
    GuardianRelationshipType,
    InstitutionAuthority,
    InstitutionId,
    ParticipantId,
    ParticipantStatus,
    PersonName,
    TeacherId,
)

__all__ = ["Participant"]

#: Opaque capability token proving construction went through a factory. Held only
#: by this module, so :meth:`Participant.create`/:meth:`Participant.rehydrate` can
#: pass it and nobody else can (short of importing a private name).
_CREATION_TOKEN: Final = object()


@dataclass(slots=True, eq=False, repr=False)
class Participant:
    """The participant aggregate root of the Participants context (DIA-001 §4.2).

    Construct via :meth:`create` or :meth:`rehydrate` only — never directly. State
    is private and exposed through read-only properties; behaviour is the guardian
    link, consent, and lifecycle methods, each of which returns the domain events
    it produced. Equality and hashing are by :class:`ParticipantId` alone: two
    ``Participant`` objects denote the same participant iff they share an identity.
    """

    # ``_token`` is an InitVar (never stored): it reaches __post_init__ to prove
    # the instance came from a factory, then is discarded.
    _token: InitVar[object]
    _id: ParticipantId
    _name: PersonName
    _date_of_birth: DateOfBirth
    _display_alias: DisplayAlias
    _created_by: ActorReference
    _created_at: datetime
    _updated_at: datetime
    _status: ParticipantStatus = ParticipantStatus.CREATED
    _guardian_links: tuple[GuardianLink, ...] = ()
    _institution_authority: InstitutionAuthority | None = None
    _consent: ConsentReference | None = None
    _verified_at: datetime | None = None
    _activated_at: datetime | None = None
    _archived_at: datetime | None = None
    _erased_at: datetime | None = None
    _version: int = 1

    def __post_init__(self, _token: object) -> None:
        if _token is not _CREATION_TOKEN:
            raise DirectConstructionError(
                "Participant must be created via Participant.create() or Participant.rehydrate(), not by calling the constructor directly."
            )

    # ------------------------------------------------------------------
    # Factories
    # ------------------------------------------------------------------

    @classmethod
    def create(
        cls,
        *,
        participant_id: ParticipantId,
        name: PersonName,
        date_of_birth: DateOfBirth,
        display_alias: DisplayAlias,
        created_by: ActorReference,
        now: datetime,
        pseudonymization_policy: PseudonymizationPolicy,
    ) -> tuple[Participant, list[DomainEvent]]:
        """Create a brand-new participant and the fact that it was created (EVT-PRT-001).

        Enforces the two invariants that hold at creation: the date of birth may
        not lie in the future (relative to ``now``), and the pseudonymized display
        alias must not leak the real name (JDG-006, via ``pseudonymization_policy``).
        The participant starts in ``Created`` — activation waits on verified
        guardianship/authority and active consent (PRT-001).

        Returns the new aggregate together with ``[ParticipantCreated]`` — the
        caller persists the aggregate and dispatches the events atomically.
        """
        if date_of_birth.is_after(now.date()):
            raise InvalidDateOfBirthError("Date of birth must not be in the future.")
        if pseudonymization_policy.reveals_identity(display_alias, name=name):
            raise AliasRevealsIdentityError("Display alias must not embed the participant's real name (JDG-006).")
        participant = cls(
            _token=_CREATION_TOKEN,
            _id=participant_id,
            _name=name,
            _date_of_birth=date_of_birth,
            _display_alias=display_alias,
            _created_by=created_by,
            _created_at=now,
            _updated_at=now,
        )
        events: list[DomainEvent] = [
            ParticipantCreated(
                aggregate_id=participant_id,
                name=name,
                date_of_birth=date_of_birth,
                display_alias=display_alias,
                created_by=created_by,
                occurred_at=now,
            )
        ]
        return participant, events

    @classmethod
    def rehydrate(
        cls,
        *,
        participant_id: ParticipantId,
        name: PersonName,
        date_of_birth: DateOfBirth,
        display_alias: DisplayAlias,
        created_by: ActorReference,
        status: ParticipantStatus,
        created_at: datetime,
        updated_at: datetime,
        version: int,
        guardian_links: tuple[GuardianLink, ...] = (),
        institution_authority: InstitutionAuthority | None = None,
        consent: ConsentReference | None = None,
        verified_at: datetime | None = None,
        activated_at: datetime | None = None,
        archived_at: datetime | None = None,
        erased_at: datetime | None = None,
    ) -> Participant:
        """Reconstruct an existing aggregate from persisted state.

        A pure hydration step: it re-runs **no** business workflow, enforces **no**
        transition rule, emits **no** events, and leaves ``version`` exactly as
        stored (never incremented). The invariants were established when the state
        was first written; replaying them here would be wrong and would fabricate
        spurious events.
        """
        return cls(
            _token=_CREATION_TOKEN,
            _id=participant_id,
            _name=name,
            _date_of_birth=date_of_birth,
            _display_alias=display_alias,
            _created_by=created_by,
            _created_at=created_at,
            _updated_at=updated_at,
            _status=status,
            _guardian_links=guardian_links,
            _institution_authority=institution_authority,
            _consent=consent,
            _verified_at=verified_at,
            _activated_at=activated_at,
            _archived_at=archived_at,
            _erased_at=erased_at,
            _version=version,
        )

    # ------------------------------------------------------------------
    # Read-only state
    # ------------------------------------------------------------------

    @property
    def id(self) -> ParticipantId:
        """The participant's immutable identity."""
        return self._id

    @property
    def name(self) -> PersonName:
        """The participant's minimized real name (access-restricted, PRT-006)."""
        return self._name

    @property
    def date_of_birth(self) -> DateOfBirth:
        """The birth date from which the age group is derived (PRT-002)."""
        return self._date_of_birth

    @property
    def display_alias(self) -> DisplayAlias:
        """The pseudonym shown to judging (JDG-006)."""
        return self._display_alias

    @property
    def created_by(self) -> ActorReference:
        """The verified adult who created the participant."""
        return self._created_by

    @property
    def status(self) -> ParticipantStatus:
        """The current lifecycle state (DATA-004 §4.3)."""
        return self._status

    @property
    def guardian_links(self) -> tuple[GuardianLink, ...]:
        """The guardian relationships owned by this participant (DIA-001 §4.2)."""
        return self._guardian_links

    @property
    def institution_authority(self) -> InstitutionAuthority | None:
        """The authorizing institution/teacher link, if any (PRT-001)."""
        return self._institution_authority

    @property
    def consent(self) -> ConsentReference | None:
        """The recorded active consent reference, or ``None`` (PRT-001)."""
        return self._consent

    @property
    def created_at(self) -> datetime:
        """When the participant was created."""
        return self._created_at

    @property
    def updated_at(self) -> datetime:
        """When the aggregate last changed."""
        return self._updated_at

    @property
    def verified_at(self) -> datetime | None:
        """When the participant's details were verified, or ``None``."""
        return self._verified_at

    @property
    def activated_at(self) -> datetime | None:
        """When the participant most recently became active, or ``None``."""
        return self._activated_at

    @property
    def archived_at(self) -> datetime | None:
        """When the participant was archived, or ``None``."""
        return self._archived_at

    @property
    def erased_at(self) -> datetime | None:
        """When the participant was erased, or ``None``."""
        return self._erased_at

    @property
    def version(self) -> int:
        """Optimistic-concurrency version; bumped once per successful mutation."""
        return self._version

    # ------------------------------------------------------------------
    # Status helpers
    # ------------------------------------------------------------------

    def is_erased(self) -> bool:
        """Whether the participant has been erased (terminal, DATA-004 §4.3)."""
        return self._status is ParticipantStatus.ERASED

    def is_active(self) -> bool:
        """Whether the participant is active and may enter competitions."""
        return self._status is ParticipantStatus.ACTIVE

    def active_guardian_count(self) -> int:
        """How many verified (active) guardian relationships exist (PRT-001)."""
        return sum(1 for link in self._guardian_links if link.is_active())

    def has_active_guardian(self) -> bool:
        """Whether at least one verified guardian relationship exists (PRT-001)."""
        return self.active_guardian_count() > 0

    def has_institutional_authority(self) -> bool:
        """Whether an authorizing institution/teacher link is present (PRT-001)."""
        return self._institution_authority is not None

    def has_active_consent(self) -> bool:
        """Whether an active consent reference is recorded (PRT-001)."""
        return self._consent is not None

    def derived_age_group(self, policy: AgeGroupPolicy, *, reference_date: datetime) -> AgeGroup:
        """Derive the age group at a competition's ``reference_date`` (PRT-002).

        A pure query — no state changes. Age group is always relative to the
        competition and never stored, so it is computed on demand from the
        participant's date of birth through the injected :class:`AgeGroupPolicy`.
        """
        return policy.derive(self._date_of_birth, reference_date=reference_date.date())

    # ------------------------------------------------------------------
    # Guardian relationships (DIA-001 §4.2; PRT-001, PRT-003, PRT-008)
    # ------------------------------------------------------------------

    def propose_guardian_link(
        self,
        *,
        guardian_id: GuardianId,
        relationship_type: GuardianRelationshipType,
        now: datetime,
    ) -> list[DomainEvent]:
        """Propose a guardian relationship (awaiting verification).

        A straightforward duplicate — an existing non-revoked link to the same
        guardian — is refused (PRT-008); a previously revoked link may be
        re-proposed. Proposing carries no domain event; the relationship becomes a
        published fact only when it is verified (:meth:`verify_guardian_link`).
        """
        self._ensure_not_erased()
        existing = self._find_link(guardian_id)
        if existing is not None and not existing.is_revoked():
            raise GuardianAlreadyLinkedError(f"Guardian {guardian_id} is already linked to this participant.")
        new_link = GuardianLink(guardian_id=guardian_id, relationship_type=relationship_type)
        self._guardian_links = (*self._without_link(guardian_id), new_link)
        self._touch(now)
        return []

    def verify_guardian_link(self, *, guardian_id: GuardianId, now: datetime) -> list[DomainEvent]:
        """Verify a proposed guardian link, making it an active relationship (EVT-PRT-002).

        Emits :class:`GuardianLinked`: the responsible-adult link now enables
        consent and management (PRT-001, PRT-003). Refuses a missing or
        already-verified link.
        """
        self._ensure_not_erased()
        link = self._find_link(guardian_id)
        if link is None:
            raise GuardianLinkNotFoundError(f"Guardian {guardian_id} is not linked.")
        if not link.is_proposed():
            raise GuardianLinkNotPendingError(f"Guardian link {guardian_id} is not proposed (status {link.status.value}).")
        self._guardian_links = (*self._without_link(guardian_id), link.verified(now=now))
        events: list[DomainEvent] = [
            GuardianLinked(
                aggregate_id=self._id,
                guardian_id=guardian_id,
                relationship_type=link.relationship_type,
                occurred_at=now,
            )
        ]
        self._touch(now)
        return events

    def revoke_guardian_link(self, *, guardian_id: GuardianId, now: datetime) -> list[DomainEvent]:
        """Revoke a guardian relationship (no published event; internal state change)."""
        self._ensure_not_erased()
        link = self._find_link(guardian_id)
        if link is None:
            raise GuardianLinkNotFoundError(f"Guardian {guardian_id} is not linked.")
        self._guardian_links = (*self._without_link(guardian_id), link.revoked())
        self._touch(now)
        return []

    # ------------------------------------------------------------------
    # Institutional authority & consent (PRT-001, PRT-004, PRT-005)
    # ------------------------------------------------------------------

    def authorize_institution(
        self,
        *,
        institution_id: InstitutionId,
        teacher_id: TeacherId | None = None,
        now: datetime,
    ) -> list[DomainEvent]:
        """Record an authorizing institution (and optional teacher) link (PRT-001).

        The alternative activation path to guardian relationships. Teacher scoping
        (PRT-004) and the still-required guardian consent (PRT-005) are enforced by
        the application/presentation layers, not weakened here.
        """
        self._ensure_not_erased()
        self._institution_authority = InstitutionAuthority(institution_id=institution_id, teacher_id=teacher_id)
        self._touch(now)
        return []

    def record_consent(self, *, consent: ConsentReference, now: datetime) -> list[DomainEvent]:
        """Record that an active consent authorizes this participant (PRT-001).

        Reacts to the Identity context's ``ConsentGranted`` (DATA-003 EVT-IDN-003):
        the participant keeps only a by-id reference (never the consent text) so
        activation can check the consent gate.
        """
        self._ensure_not_erased()
        self._consent = consent
        self._touch(now)
        return []

    def withdraw_consent(self, *, now: datetime) -> list[DomainEvent]:
        """Clear the recorded consent (reacts to Identity ``ConsentWithdrawn``).

        The erasure/retention cascade the withdrawal may trigger (IDN-006, PRT-007)
        is an outer-layer decision; this only drops the reference.
        """
        self._ensure_not_erased()
        if self._consent is None:
            raise ConsentNotRecordedError("There is no active consent to withdraw.")
        self._consent = None
        self._touch(now)
        return []

    # ------------------------------------------------------------------
    # Profile
    # ------------------------------------------------------------------

    def rename(self, new_name: PersonName, *, now: datetime) -> list[DomainEvent]:
        """Correct the participant's minimized real name (no published event)."""
        self._ensure_not_erased()
        self._name = new_name
        self._touch(now)
        return []

    def reassign_display_alias(
        self,
        new_alias: DisplayAlias,
        *,
        pseudonymization_policy: PseudonymizationPolicy,
        now: datetime,
    ) -> list[DomainEvent]:
        """Change the judging alias, keeping it non-identifying (JDG-006)."""
        self._ensure_not_erased()
        if pseudonymization_policy.reveals_identity(new_alias, name=self._name):
            raise AliasRevealsIdentityError("Display alias must not embed the participant's real name (JDG-006).")
        self._display_alias = new_alias
        self._touch(now)
        return []

    # ------------------------------------------------------------------
    # Lifecycle (DATA-004 §4.3)
    # ------------------------------------------------------------------

    def verify(self, *, now: datetime) -> list[DomainEvent]:
        """Verify the participant's details: ``Created → Verified`` (EVT-PRT-003, PRT-002).

        The required minimized details and a valid date of birth are guaranteed by
        the value objects, so verification records the milestone toward activation.
        """
        self._ensure_not_erased()
        if self._status is not ParticipantStatus.CREATED:
            raise InvalidParticipantTransitionError(f"Cannot verify a participant in state {self._status.value}; expected 'created'.")
        self._status = ParticipantStatus.VERIFIED
        self._verified_at = now
        events: list[DomainEvent] = [ParticipantVerified(aggregate_id=self._id, occurred_at=now)]
        self._touch(now)
        return events

    def activate(self, *, policy: GuardianshipPolicy, now: datetime) -> list[DomainEvent]:
        """Activate the participant: ``Verified → Active`` (EVT-PRT-004, PRT-001).

        Consults :class:`GuardianshipPolicy`: activation requires a verified
        guardian relationship *or* an authorized institution/teacher link, **and**
        an active recorded consent. A blocked assessment raises
        :class:`ActivationRequirementsError` carrying the machine-readable reason.
        """
        self._ensure_not_erased()
        if self._status is not ParticipantStatus.VERIFIED:
            raise InvalidParticipantTransitionError(f"Cannot activate a participant in state {self._status.value}; expected 'verified'.")
        self._guard_activation(policy)
        self._status = ParticipantStatus.ACTIVE
        self._activated_at = now
        events: list[DomainEvent] = [ParticipantActivated(aggregate_id=self._id, occurred_at=now)]
        self._touch(now)
        return events

    def archive(self, *, now: datetime) -> list[DomainEvent]:
        """Archive the participant: ``Active → Archived`` (EVT-PRT-005, PRT-007).

        Archival is not erasure — the record is retained and may be reactivated
        (DATA-004 §4.3).
        """
        self._ensure_not_erased()
        if self._status is not ParticipantStatus.ACTIVE:
            raise InvalidParticipantTransitionError(f"Cannot archive a participant in state {self._status.value}; expected 'active'.")
        self._status = ParticipantStatus.ARCHIVED
        self._archived_at = now
        events: list[DomainEvent] = [ParticipantArchived(aggregate_id=self._id, occurred_at=now)]
        self._touch(now)
        return events

    def reactivate(self, *, policy: GuardianshipPolicy, now: datetime) -> list[DomainEvent]:
        """Reactivate an archived participant: ``Archived → Active`` (DATA-004 §4.3).

        Re-checks the activation preconditions (subject to valid consent, PRT-001)
        and re-emits :class:`ParticipantActivated`.
        """
        self._ensure_not_erased()
        if self._status is not ParticipantStatus.ARCHIVED:
            raise ParticipantNotArchivedError(f"Cannot reactivate a participant in state {self._status.value}; expected 'archived'.")
        self._guard_activation(policy)
        self._status = ParticipantStatus.ACTIVE
        self._activated_at = now
        self._archived_at = None
        events: list[DomainEvent] = [ParticipantActivated(aggregate_id=self._id, occurred_at=now)]
        self._touch(now)
        return events

    def request_erasure(self, *, request_reference: uuid.UUID, now: datetime) -> list[DomainEvent]:
        """Request erasure: ``{Active|Archived} → Erased`` (EVT-PRT-006, PRT-007).

        Terminal and irreversible. Emits :class:`ParticipantErasureRequested` to
        drive the privacy-critical cascade; financial/audit records are retained
        under an independent lawful basis (FIN-008), handled downstream.
        """
        self._ensure_not_erased()
        if self._status not in (ParticipantStatus.ACTIVE, ParticipantStatus.ARCHIVED):
            raise InvalidParticipantTransitionError(f"Cannot erase a participant in state {self._status.value}; expected 'active' or 'archived'.")
        self._status = ParticipantStatus.ERASED
        self._erased_at = now
        events: list[DomainEvent] = [ParticipantErasureRequested(aggregate_id=self._id, request_reference=request_reference, occurred_at=now)]
        self._touch(now)
        return events

    # ------------------------------------------------------------------
    # Identity semantics
    # ------------------------------------------------------------------

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Participant):
            return NotImplemented
        return self._id == other._id

    def __hash__(self) -> int:
        return hash(self._id)

    def __repr__(self) -> str:
        return f"Participant(id={self._id.json()!r}, alias={self._display_alias.value!r}, status={self._status.value!r}, version={self._version})"

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    def _guard_activation(self, policy: GuardianshipPolicy) -> None:
        """Raise :class:`ActivationRequirementsError` if activation is not permitted (PRT-001)."""
        assessment = policy.evaluate(
            active_guardian_count=self.active_guardian_count(),
            has_institutional_authority=self.has_institutional_authority(),
            has_active_consent=self.has_active_consent(),
        )
        if not assessment.allowed:
            reason = assessment.reason.value if assessment.reason is not None else "unknown"
            raise ActivationRequirementsError(f"Participant cannot be activated: {reason} (PRT-001).", reason=reason)

    def _find_link(self, guardian_id: GuardianId) -> GuardianLink | None:
        """Return the guardian link for ``guardian_id``, or ``None``."""
        return next((link for link in self._guardian_links if link.guardian_id == guardian_id), None)

    def _without_link(self, guardian_id: GuardianId) -> tuple[GuardianLink, ...]:
        """The guardian links with any link for ``guardian_id`` removed."""
        return tuple(link for link in self._guardian_links if link.guardian_id != guardian_id)

    def _ensure_not_erased(self) -> None:
        """Guard: forbid mutating an erased participant (terminal state)."""
        if self._status is ParticipantStatus.ERASED:
            raise ParticipantErasedError(f"Participant {self._id} is erased; operation not permitted.")

    def _touch(self, now: datetime) -> None:
        """Stamp the mutation time and advance the optimistic-concurrency version."""
        self._updated_at = now
        self._version += 1
