"""Unit tests for the Participants ambient-dependency adapters.

The system clock and UUID generator are the concrete
:class:`~apps.participants.application.interfaces.Clock` and
:class:`~apps.participants.application.interfaces.UuidGenerator` adapters; these
tests confirm they satisfy those ports and behave as specified (timezone-aware
instants, UUID v7 identifiers).
"""

from __future__ import annotations

from apps.participants.application.interfaces import Clock, UuidGenerator
from apps.participants.infrastructure.system import SystemClock, Uuid7Generator


def test_system_clock_conforms_and_is_aware() -> None:
    clock = SystemClock()
    assert isinstance(clock, Clock)
    assert clock.utcnow().tzinfo is not None
    assert clock.now().tzinfo is not None


def test_uuid_generator_conforms_and_yields_v7() -> None:
    uuids = Uuid7Generator()
    assert isinstance(uuids, UuidGenerator)
    value = uuids.new()
    assert value.version == 7
    assert uuids.new() != value
