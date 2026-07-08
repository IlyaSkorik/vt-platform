"""Query use cases for the Participants bounded context.

The **read side**: side-effect-free operations that return DTOs describing
participants and their relationships. Kept separate from commands so reads never
mutate state (ARCH-001 §7.2, §7.4). Query messages live in
:mod:`apps.participants.application.queries.participant_queries`; the re-export
below is the package's public surface.
"""

from apps.participants.application.queries.participant_queries import GetParticipantQuery

__all__ = ["GetParticipantQuery"]
