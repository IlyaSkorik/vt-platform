"""Unit tests for the Participants domain events.

Framework-free (ARCH-001 §28.2). Covers the shared :class:`DomainEvent` envelope
(UUID-v7 id, timezone-aware UTC ``occurred_at``, positive version), the JSON-safe
``to_dict`` projection for every event, and the ``_serialize`` helper's mapping of
each value-object type (including its loud failure on an unmapped type).
"""

from __future__ import annotations

import uuid
from datetime import UTC, date, datetime

import pytest

from apps.participants.domain.events import (
    GuardianLinked,
    ParticipantActivated,
    ParticipantArchived,
    ParticipantCreated,
    ParticipantErasureRequested,
    ParticipantVerified,
    _serialize,
)
from apps.participants.domain.value_objects import (
    ActorReference,
    ActorType,
    AgeGroup,
    ConsentReference,
    DateOfBirth,
    DisplayAlias,
    GuardianId,
    GuardianRelationshipType,
    ParticipantId,
    PersonName,
    _generate_uuid7,
)

NOW = datetime(2026, 7, 7, 12, 0, tzinfo=UTC)


def _created() -> ParticipantCreated:
    return ParticipantCreated(
        aggregate_id=ParticipantId.generate(),
        name=PersonName("Ivan", "Petrov", "Sergeevich"),
        date_of_birth=DateOfBirth(date(2015, 3, 4)),
        display_alias=DisplayAlias("Falcon-99"),
        created_by=ActorReference.of(_generate_uuid7(), ActorType.GUARDIAN),
        occurred_at=NOW,
    )


# ---------------------------------------------------------------------------
# Envelope
# ---------------------------------------------------------------------------


def test_event_id_defaults_to_uuid7_and_type_is_class_name() -> None:
    event = ParticipantVerified(aggregate_id=ParticipantId.generate())
    assert event.event_id.version == 7
    assert event.event_type == "ParticipantVerified"
    assert event.event_version == 1


def test_occurred_at_normalized_to_utc() -> None:
    tz = datetime(2026, 7, 7, 15, 0, tzinfo=UTC).astimezone()
    event = ParticipantActivated(aggregate_id=ParticipantId.generate(), occurred_at=tz)
    assert event.occurred_at.tzinfo == UTC


def test_rejects_non_uuid_event_id() -> None:
    with pytest.raises(TypeError):
        ParticipantVerified(aggregate_id=ParticipantId.generate(), event_id="x")  # type: ignore[arg-type]


def test_rejects_non_v7_event_id() -> None:
    with pytest.raises(ValueError, match="UUID v7"):
        ParticipantVerified(aggregate_id=ParticipantId.generate(), event_id=uuid.uuid4())


def test_rejects_naive_occurred_at() -> None:
    with pytest.raises(ValueError, match="timezone-aware"):
        ParticipantVerified(aggregate_id=ParticipantId.generate(), occurred_at=datetime(2026, 7, 7, 12, 0))


def test_rejects_non_positive_version() -> None:
    with pytest.raises(ValueError, match="positive integer"):
        ParticipantVerified(aggregate_id=ParticipantId.generate(), event_version=0)


# ---------------------------------------------------------------------------
# to_dict for each event
# ---------------------------------------------------------------------------


def test_participant_created_to_dict() -> None:
    event = _created()
    payload = event.to_dict()
    assert payload["event_type"] == "ParticipantCreated"
    assert payload["name"] == {
        "first_name": "Ivan",
        "last_name": "Petrov",
        "middle_name": "Sergeevich",
    }
    assert payload["date_of_birth"] == "2015-03-04"
    assert payload["display_alias"] == "Falcon-99"
    assert payload["created_by"] == {
        "actor_id": str(event.created_by.actor_id),
        "actor_type": "guardian",
    }
    assert payload["occurred_at"] == NOW.isoformat()


def test_guardian_linked_to_dict() -> None:
    gid = GuardianId.generate()
    event = GuardianLinked(
        aggregate_id=ParticipantId.generate(),
        guardian_id=gid,
        relationship_type=GuardianRelationshipType.MOTHER,
        occurred_at=NOW,
    )
    payload = event.to_dict()
    assert payload["guardian_id"] == gid.json()
    assert payload["relationship_type"] == "mother"


def test_erasure_requested_to_dict() -> None:
    ref = _generate_uuid7()
    event = ParticipantErasureRequested(aggregate_id=ParticipantId.generate(), request_reference=ref, occurred_at=NOW)
    assert event.to_dict()["request_reference"] == str(ref)


def test_lifecycle_events_carry_aggregate_id() -> None:
    pid = ParticipantId.generate()
    for event in (
        ParticipantVerified(aggregate_id=pid, occurred_at=NOW),
        ParticipantActivated(aggregate_id=pid, occurred_at=NOW),
        ParticipantArchived(aggregate_id=pid, occurred_at=NOW),
    ):
        assert event.to_dict()["aggregate_id"] == pid.json()


# ---------------------------------------------------------------------------
# _serialize helper
# ---------------------------------------------------------------------------


def test_serialize_maps_value_objects() -> None:
    assert _serialize(None) is None
    assert _serialize(ActorType.TEACHER) == "teacher"
    assert _serialize(True) is True
    assert _serialize(7) == 7
    assert _serialize(NOW) == NOW.isoformat()
    raw = _generate_uuid7()
    assert _serialize(raw) == str(raw)


def test_serialize_age_group_and_consent_reference() -> None:
    band = AgeGroup(code="junior", label="Junior", min_age=6, max_age=9)
    assert _serialize(band) == {
        "code": "junior",
        "label": "Junior",
        "min_age": 6,
        "max_age": 9,
    }
    cid = _generate_uuid7()
    ref = ConsentReference.of(cid, "2026-01")
    assert _serialize(ref) == {"consent_id": str(cid), "consent_version": "2026-01"}


def test_serialize_rejects_unmapped_type() -> None:
    with pytest.raises(TypeError):
        _serialize(object())
