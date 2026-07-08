"""Command messages for the Participants bounded context.

One command = one intent to change state = one transaction boundary
(ARCH-001 §7.2, §7.4). Immutable, transport-only dataclasses; see
:mod:`apps.participants.application.commands.participant_commands`. The re-exports
below are the package's public surface.
"""

from apps.participants.application.commands.participant_commands import (
    ActivateParticipantCommand,
    ArchiveParticipantCommand,
    AuthorizeInstitutionCommand,
    CreateParticipantCommand,
    ProposeGuardianLinkCommand,
    ReactivateParticipantCommand,
    ReassignDisplayAliasCommand,
    RecordConsentCommand,
    RenameParticipantCommand,
    RequestParticipantErasureCommand,
    RevokeGuardianLinkCommand,
    VerifyGuardianLinkCommand,
    VerifyParticipantCommand,
    WithdrawConsentCommand,
)

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
