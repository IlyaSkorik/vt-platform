from __future__ import annotations

from tests.journeys.actors import ActorFactory


def test_organizer_and_participant_sign_up(actors: ActorFactory) -> None:
    organizer, participant = actors.organizer(), actors.participant()
    assert organizer.token and participant.token
