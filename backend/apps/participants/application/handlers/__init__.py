"""Command & query handlers (use cases) for the Participants bounded context.

One handler per command, plus a read handler for retrieval: thin orchestrators
over the application ports and the ``Participant`` aggregate (ARCH-001 §7.2, §7.4).
Implementations live in
:mod:`apps.participants.application.handlers.participant_handlers`; the re-exports
below are the package's public surface.
"""

from apps.participants.application.handlers.participant_handlers import (
    ActivateParticipantHandler,
    ArchiveParticipantHandler,
    AuthorizeInstitutionHandler,
    CreateParticipantHandler,
    GetParticipantHandler,
    ProposeGuardianLinkHandler,
    ReactivateParticipantHandler,
    ReassignDisplayAliasHandler,
    RecordConsentHandler,
    RenameParticipantHandler,
    RequestParticipantErasureHandler,
    RevokeGuardianLinkHandler,
    VerifyGuardianLinkHandler,
    VerifyParticipantHandler,
    WithdrawConsentHandler,
)

__all__ = [
    "ActivateParticipantHandler",
    "ArchiveParticipantHandler",
    "AuthorizeInstitutionHandler",
    "CreateParticipantHandler",
    "GetParticipantHandler",
    "ProposeGuardianLinkHandler",
    "ReactivateParticipantHandler",
    "ReassignDisplayAliasHandler",
    "RecordConsentHandler",
    "RenameParticipantHandler",
    "RequestParticipantErasureHandler",
    "RevokeGuardianLinkHandler",
    "VerifyGuardianLinkHandler",
    "VerifyParticipantHandler",
    "WithdrawConsentHandler",
]
