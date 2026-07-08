"""Composition root for the Participants API edge.

The one place where the framework-free use cases are wired to their concrete
infrastructure adapters and domain policies (ARCH-001 §7.3, Dependency Inversion).
Views ask this module for a fully-assembled handler and stay ignorant of *which*
repository, clock, uuid source, or policy sits behind the port — swapping an
adapter (or a fake, in tests) changes only this file.

Every adapter here is stateless and cheap to build, so handlers are assembled per
request rather than cached; there is no shared mutable state to reason about.
"""

from __future__ import annotations

from apps.participants.application.handlers import (
    ActivateParticipantHandler,
    CreateParticipantHandler,
    GetParticipantHandler,
    ProposeGuardianLinkHandler,
    VerifyGuardianLinkHandler,
    VerifyParticipantHandler,
)
from apps.participants.domain.policies import GuardianshipPolicy, PseudonymizationPolicy
from apps.participants.infrastructure.repositories import DjangoParticipantRepository
from apps.participants.infrastructure.system import SystemClock, Uuid7Generator

__all__ = [
    "build_activate_participant_handler",
    "build_create_participant_handler",
    "build_get_participant_handler",
    "build_propose_guardian_link_handler",
    "build_verify_guardian_link_handler",
    "build_verify_participant_handler",
]


def build_create_participant_handler() -> CreateParticipantHandler:
    """Assemble the create-participant use case with its adapters."""
    return CreateParticipantHandler(
        participants=DjangoParticipantRepository(),
        clock=SystemClock(),
        uuids=Uuid7Generator(),
        pseudonymization_policy=PseudonymizationPolicy(),
    )


def build_get_participant_handler() -> GetParticipantHandler:
    """Assemble the retrieve-participant read use case."""
    return GetParticipantHandler(participants=DjangoParticipantRepository())


def build_propose_guardian_link_handler() -> ProposeGuardianLinkHandler:
    """Assemble the propose-guardian-link use case."""
    return ProposeGuardianLinkHandler(
        participants=DjangoParticipantRepository(), clock=SystemClock()
    )


def build_verify_guardian_link_handler() -> VerifyGuardianLinkHandler:
    """Assemble the verify-guardian-link use case."""
    return VerifyGuardianLinkHandler(
        participants=DjangoParticipantRepository(), clock=SystemClock()
    )


def build_verify_participant_handler() -> VerifyParticipantHandler:
    """Assemble the verify-participant use case."""
    return VerifyParticipantHandler(
        participants=DjangoParticipantRepository(), clock=SystemClock()
    )


def build_activate_participant_handler() -> ActivateParticipantHandler:
    """Assemble the activate-participant use case with the guardianship policy (PRT-001)."""
    return ActivateParticipantHandler(
        participants=DjangoParticipantRepository(),
        clock=SystemClock(),
        guardianship_policy=GuardianshipPolicy(),
    )
