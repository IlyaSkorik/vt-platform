"""Command messages for the Participants bounded context.

A command is an **intent** to change state, expressed as immutable transport data
that crosses the boundary from presentation (or a task/CLI) into the application
layer. Each is a ``frozen``, ``slots`` dataclass carrying only primitives and
stdlib types — **never** domain value objects and **never** behaviour. The matching
handler (``application/handlers``) turns these raw fields into validated domain
value objects and orchestrates the use case; the command itself holds no business
logic.

Design contract for every command here:

* immutable (``frozen=True``) and memory-light (``slots=True``);
* transport data only — strings, optional strings, and ``datetime`` for instants
  the presentation layer already resolved;
* fully typed, no ``Any``.
"""

from __future__ import annotations

from dataclasses import dataclass

__all__ = [
    "ActivateParticipantCommand",
    "ArchiveParticipantCommand",
    "AuthorizeInstitutionCommand",
    "CreateParticipantCommand",
    "ProposeGuardianLinkCommand",
    "ReactivateParticipantCommand",
    "ReassignDisplayAliasCommand",
    "RecordConsentCommand",
    "RenameParticipantCommand",
    "RequestParticipantErasureCommand",
    "RevokeGuardianLinkCommand",
    "VerifyGuardianLinkCommand",
    "VerifyParticipantCommand",
    "WithdrawConsentCommand",
]


@dataclass(frozen=True, slots=True)
class CreateParticipantCommand:
    """Register a brand-new participant from raw creation input.

    ``created_by_type`` is the string value of a domain ``ActorType``
    (``guardian``/``teacher``); ``date_of_birth`` is an ISO-8601 date string.
    """

    first_name: str
    last_name: str
    date_of_birth: str
    display_alias: str
    created_by_id: str
    created_by_type: str
    middle_name: str | None = None


@dataclass(frozen=True, slots=True)
class VerifyParticipantCommand:
    """Verify a participant's details (``Created → Verified``)."""

    participant_id: str


@dataclass(frozen=True, slots=True)
class ActivateParticipantCommand:
    """Activate a participant (``Verified → Active``), subject to PRT-001."""

    participant_id: str


@dataclass(frozen=True, slots=True)
class ArchiveParticipantCommand:
    """Archive a participant (``Active → Archived``)."""

    participant_id: str


@dataclass(frozen=True, slots=True)
class ReactivateParticipantCommand:
    """Reactivate an archived participant (``Archived → Active``)."""

    participant_id: str


@dataclass(frozen=True, slots=True)
class RequestParticipantErasureCommand:
    """Request erasure of a participant (``{Active|Archived} → Erased``).

    ``request_reference`` is the id of the originating DSAR or consent withdrawal.
    """

    participant_id: str
    request_reference: str


@dataclass(frozen=True, slots=True)
class RenameParticipantCommand:
    """Correct a participant's minimized real name."""

    participant_id: str
    first_name: str
    last_name: str
    middle_name: str | None = None


@dataclass(frozen=True, slots=True)
class ReassignDisplayAliasCommand:
    """Change a participant's pseudonymized judging alias (JDG-006)."""

    participant_id: str
    display_alias: str


@dataclass(frozen=True, slots=True)
class ProposeGuardianLinkCommand:
    """Propose a guardian relationship for a participant (awaiting verification).

    ``relationship_type`` is the string value of a domain ``GuardianRelationshipType``.
    """

    participant_id: str
    guardian_id: str
    relationship_type: str


@dataclass(frozen=True, slots=True)
class VerifyGuardianLinkCommand:
    """Verify a proposed guardian relationship (makes it active)."""

    participant_id: str
    guardian_id: str


@dataclass(frozen=True, slots=True)
class RevokeGuardianLinkCommand:
    """Revoke a guardian relationship."""

    participant_id: str
    guardian_id: str


@dataclass(frozen=True, slots=True)
class AuthorizeInstitutionCommand:
    """Record an authorizing institution (and optional teacher) link (PRT-001)."""

    participant_id: str
    institution_id: str
    teacher_id: str | None = None


@dataclass(frozen=True, slots=True)
class RecordConsentCommand:
    """Record that an active Identity consent authorizes this participant (PRT-001)."""

    participant_id: str
    consent_id: str
    consent_version: str


@dataclass(frozen=True, slots=True)
class WithdrawConsentCommand:
    """Clear the recorded consent for a participant."""

    participant_id: str
