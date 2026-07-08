"""Structural-conformance tests for the Participants application ports.

The ports are :func:`~typing.runtime_checkable` :class:`typing.Protocol` seams, so
the in-memory fakes should satisfy them by structure alone (no inheritance). These
tests document that contract and guard against a fake drifting out of shape.
"""

from __future__ import annotations

from apps.participants.application.interfaces import (
    Clock,
    EventPublisher,
    ParticipantRepository,
    UuidGenerator,
)
from tests.application.participants.fakes import (
    FakeClock,
    FakeEventPublisher,
    FakeParticipantRepository,
    FakeUuidGenerator,
)


def test_repository_fake_conforms() -> None:
    assert isinstance(FakeParticipantRepository(), ParticipantRepository)


def test_clock_fake_conforms() -> None:
    assert isinstance(FakeClock(), Clock)


def test_uuid_generator_fake_conforms() -> None:
    assert isinstance(FakeUuidGenerator(), UuidGenerator)


def test_event_publisher_fake_conforms() -> None:
    publisher = FakeEventPublisher()
    assert isinstance(publisher, EventPublisher)
