"""Unit tests for the Identity domain events.

Framework-free, database-free (ARCH-001 §28.2). Covers, across the event
hierarchy: construction (auto-generated envelope + explicit business data),
immutability, timestamp semantics (aware, UTC, defaulted), the UUID v7 identity
invariant, equality, and JSON-safe serialization for every event type.
"""

from __future__ import annotations

import dataclasses
import json
import uuid
from datetime import UTC, datetime, timedelta, timezone

import pytest

from apps.identity.domain.events import (
    ConsentGranted,
    ConsentType,
    ConsentWithdrawn,
    DomainEvent,
    EmailVerified,
    PasswordChanged,
    PasswordResetCompleted,
    PasswordResetRequested,
    PhoneVerified,
    SessionEnded,
    SessionEndReason,
    SessionStarted,
    UserLocked,
    UserRegistered,
    UserUnlocked,
    _serialize,
)
from apps.identity.domain.value_objects import (
    ConsentVersion,
    Email,
    FullName,
    Locale,
    PhoneNumber,
    UserId,
)

# ---------------------------------------------------------------------------
# Fixtures / helpers
# ---------------------------------------------------------------------------


@pytest.fixture
def aggregate_id() -> UserId:
    return UserId.generate()


def _uuid7() -> uuid.UUID:
    # A concrete UUID v7 value objects already know how to mint.
    return UserId.generate().value


# The full roster of event classes together with a factory that builds a minimal
# valid instance, so envelope-level behaviour can be asserted for every event.
def _sample_events(aggregate_id: UserId) -> list[DomainEvent]:
    return [
        UserRegistered(
            aggregate_id=aggregate_id,
            email=Email("ivan@example.com"),
            full_name=FullName("Ivan", "Petrov", "Sergeevich"),
            locale=Locale("ru-RU"),
        ),
        EmailVerified(aggregate_id=aggregate_id, email=Email("ivan@example.com")),
        PhoneVerified(aggregate_id=aggregate_id, phone=PhoneNumber("+375291234567")),
        PasswordChanged(aggregate_id=aggregate_id),
        PasswordResetRequested(
            aggregate_id=aggregate_id,
            email=Email("ivan@example.com"),
            expires_at=datetime(2026, 7, 6, 12, 0, tzinfo=UTC),
        ),
        PasswordResetCompleted(aggregate_id=aggregate_id, email=Email("ivan@example.com")),
        ConsentGranted(
            aggregate_id=aggregate_id,
            consent_type=ConsentType.TERMS_OF_SERVICE,
            consent_version=ConsentVersion("2026-01"),
        ),
        ConsentWithdrawn(
            aggregate_id=aggregate_id,
            consent_type=ConsentType.MARKETING,
            consent_version=ConsentVersion("2026-01"),
        ),
        UserLocked(aggregate_id=aggregate_id, reason="too_many_attempts"),
        UserUnlocked(aggregate_id=aggregate_id, reason="cooloff_elapsed"),
        SessionStarted(aggregate_id=aggregate_id, session_id=_uuid7()),
        SessionEnded(
            aggregate_id=aggregate_id,
            session_id=_uuid7(),
            reason=SessionEndReason.LOGOUT,
        ),
    ]


# ---------------------------------------------------------------------------
# Base envelope: construction, identity, timestamps, immutability
# ---------------------------------------------------------------------------


class TestEnvelope:
    def test_defaults_populate_id_and_timestamp(self, aggregate_id: UserId) -> None:
        event = PasswordChanged(aggregate_id=aggregate_id)
        assert isinstance(event.event_id, uuid.UUID)
        assert isinstance(event.occurred_at, datetime)
        assert event.event_version == 1
        assert event.aggregate_id is aggregate_id

    def test_event_id_is_uuid_v7(self, aggregate_id: UserId) -> None:
        assert PasswordChanged(aggregate_id=aggregate_id).event_id.version == 7

    def test_event_ids_are_unique_per_instance(self, aggregate_id: UserId) -> None:
        ids = {PasswordChanged(aggregate_id=aggregate_id).event_id for _ in range(1000)}
        assert len(ids) == 1000

    def test_occurred_at_is_timezone_aware_utc(self, aggregate_id: UserId) -> None:
        occurred_at = PasswordChanged(aggregate_id=aggregate_id).occurred_at
        assert occurred_at.tzinfo is not None
        assert occurred_at.utcoffset() == timedelta(0)

    def test_occurred_at_defaults_to_now(self, aggregate_id: UserId) -> None:
        before = datetime.now(UTC)
        event = PasswordChanged(aggregate_id=aggregate_id)
        after = datetime.now(UTC)
        assert before <= event.occurred_at <= after

    def test_aware_non_utc_timestamp_is_normalized_to_utc(self, aggregate_id: UserId) -> None:
        moscow = timezone(timedelta(hours=3))
        event = PasswordChanged(
            aggregate_id=aggregate_id,
            occurred_at=datetime(2026, 7, 6, 15, 0, tzinfo=moscow),
        )
        assert event.occurred_at.utcoffset() == timedelta(0)
        assert event.occurred_at == datetime(2026, 7, 6, 12, 0, tzinfo=UTC)

    def test_explicit_envelope_is_preserved(self, aggregate_id: UserId) -> None:
        event_id = _uuid7()
        occurred_at = datetime(2026, 1, 1, tzinfo=UTC)
        event = PasswordChanged(
            aggregate_id=aggregate_id,
            event_id=event_id,
            occurred_at=occurred_at,
            event_version=3,
        )
        assert event.event_id == event_id
        assert event.occurred_at == occurred_at
        assert event.event_version == 3

    def test_naive_timestamp_is_rejected(self, aggregate_id: UserId) -> None:
        with pytest.raises(ValueError, match="timezone-aware"):
            PasswordChanged(aggregate_id=aggregate_id, occurred_at=datetime(2026, 1, 1))

    def test_non_v7_event_id_is_rejected(self, aggregate_id: UserId) -> None:
        with pytest.raises(ValueError, match="UUID v7"):
            PasswordChanged(aggregate_id=aggregate_id, event_id=uuid.uuid4())

    def test_non_positive_event_version_is_rejected(self, aggregate_id: UserId) -> None:
        with pytest.raises(ValueError, match="positive integer"):
            PasswordChanged(aggregate_id=aggregate_id, event_version=0)

    def test_non_uuid_event_id_is_rejected(self, aggregate_id: UserId) -> None:
        with pytest.raises(TypeError, match=r"uuid\.UUID"):
            PasswordChanged(aggregate_id=aggregate_id, event_id="not-a-uuid")  # type: ignore[arg-type]

    def test_event_type_is_class_name(self, aggregate_id: UserId) -> None:
        assert PasswordChanged(aggregate_id=aggregate_id).event_type == "PasswordChanged"

    def test_is_immutable(self, aggregate_id: UserId) -> None:
        event = PasswordChanged(aggregate_id=aggregate_id)
        with pytest.raises(dataclasses.FrozenInstanceError):
            event.event_version = 2  # type: ignore[misc]

    def test_business_field_is_immutable(self, aggregate_id: UserId) -> None:
        event = EmailVerified(aggregate_id=aggregate_id, email=Email("ivan@example.com"))
        with pytest.raises(dataclasses.FrozenInstanceError):
            event.email = Email("other@example.com")  # type: ignore[misc]

    def test_equality_by_value(self, aggregate_id: UserId) -> None:
        event_id = _uuid7()
        occurred_at = datetime(2026, 1, 1, tzinfo=UTC)
        first = EmailVerified(
            aggregate_id=aggregate_id,
            event_id=event_id,
            occurred_at=occurred_at,
            email=Email("ivan@example.com"),
        )
        second = EmailVerified(
            aggregate_id=aggregate_id,
            event_id=event_id,
            occurred_at=occurred_at,
            email=Email("ivan@example.com"),
        )
        assert first == second

    def test_distinct_events_are_not_equal(self, aggregate_id: UserId) -> None:
        # Different auto-generated event_id ⇒ different occurrences.
        first = PasswordChanged(aggregate_id=aggregate_id)
        second = PasswordChanged(aggregate_id=aggregate_id)
        assert first != second


# ---------------------------------------------------------------------------
# Serialization (shared behaviour across every event)
# ---------------------------------------------------------------------------


class TestSerialization:
    @pytest.mark.parametrize("event", _sample_events(UserId.generate()))
    def test_to_dict_is_json_serializable(self, event: DomainEvent) -> None:
        payload = event.to_dict()
        # Round-trips through json without a custom encoder ⇒ only primitives.
        assert json.loads(json.dumps(payload)) == payload

    @pytest.mark.parametrize("event", _sample_events(UserId.generate()))
    def test_to_dict_carries_the_envelope(self, event: DomainEvent) -> None:
        payload = event.to_dict()
        assert payload["event_type"] == event.event_type
        assert payload["event_id"] == str(event.event_id)
        assert payload["occurred_at"] == event.occurred_at.isoformat()
        assert payload["aggregate_id"] == event.aggregate_id.json()
        assert payload["event_version"] == event.event_version

    def test_value_objects_are_serialized_to_primitives(self, aggregate_id: UserId) -> None:
        event = UserRegistered(
            aggregate_id=aggregate_id,
            email=Email("Ivan@Example.com"),
            full_name=FullName("Ivan", "Petrov", "Sergeevich"),
            locale=Locale("ru-RU"),
        )
        payload = event.to_dict()
        assert payload["email"] == "ivan@example.com"  # normalized by the VO
        assert payload["locale"] == "ru-RU"
        assert payload["full_name"] == {
            "first_name": "Ivan",
            "last_name": "Petrov",
            "middle_name": "Sergeevich",
        }

    def test_enum_is_serialized_to_its_value(self, aggregate_id: UserId) -> None:
        event = ConsentGranted(
            aggregate_id=aggregate_id,
            consent_type=ConsentType.PRIVACY_POLICY,
            consent_version=ConsentVersion("2026-01"),
        )
        payload = event.to_dict()
        assert payload["consent_type"] == "privacy_policy"
        assert payload["consent_version"] == "2026-01"

    def test_unmapped_field_type_fails_loudly(self) -> None:
        # Defensive guard: a payload carrying a type the serializer does not
        # know about must fail loudly rather than emit junk.
        with pytest.raises(TypeError, match="Cannot serialize"):
            _serialize(object())


# ---------------------------------------------------------------------------
# Per-event construction of business payloads
# ---------------------------------------------------------------------------


class TestEventPayloads:
    def test_user_registered(self, aggregate_id: UserId) -> None:
        event = UserRegistered(
            aggregate_id=aggregate_id,
            email=Email("ivan@example.com"),
            full_name=FullName("Ivan", "Petrov"),
            locale=Locale("en-US"),
        )
        assert event.email == Email("ivan@example.com")
        assert event.full_name.short() == "Ivan Petrov"
        assert event.locale.is_english()

    def test_phone_verified(self, aggregate_id: UserId) -> None:
        event = PhoneVerified(aggregate_id=aggregate_id, phone=PhoneNumber("+375 29 123-45-67"))
        assert event.phone == PhoneNumber("+375291234567")

    def test_password_reset_requested_carries_deadline(self, aggregate_id: UserId) -> None:
        expires_at = datetime(2026, 7, 6, 12, 0, tzinfo=UTC)
        event = PasswordResetRequested(
            aggregate_id=aggregate_id,
            email=Email("ivan@example.com"),
            expires_at=expires_at,
        )
        assert event.expires_at == expires_at

    def test_consent_withdrawn(self, aggregate_id: UserId) -> None:
        event = ConsentWithdrawn(
            aggregate_id=aggregate_id,
            consent_type=ConsentType.MINOR_DATA_PROCESSING,
            consent_version=ConsentVersion("1.2"),
        )
        assert event.consent_type is ConsentType.MINOR_DATA_PROCESSING
        assert event.consent_version == ConsentVersion("1.2")

    def test_user_locked_temporary(self, aggregate_id: UserId) -> None:
        until = datetime(2026, 7, 6, 13, 0, tzinfo=UTC)
        event = UserLocked(aggregate_id=aggregate_id, reason="too_many_attempts", locked_until=until)
        assert event.reason == "too_many_attempts"
        assert event.locked_until == until

    def test_user_locked_indefinite(self, aggregate_id: UserId) -> None:
        event = UserLocked(aggregate_id=aggregate_id, reason="admin")
        assert event.locked_until is None

    def test_session_started_with_context(self, aggregate_id: UserId) -> None:
        session_id = _uuid7()
        event = SessionStarted(
            aggregate_id=aggregate_id,
            session_id=session_id,
            ip_address="203.0.113.7",
            user_agent="Mozilla/5.0",
        )
        assert event.session_id == session_id
        assert event.ip_address == "203.0.113.7"
        assert event.user_agent == "Mozilla/5.0"

    def test_session_ended_reason(self, aggregate_id: UserId) -> None:
        event = SessionEnded(
            aggregate_id=aggregate_id,
            session_id=_uuid7(),
            reason=SessionEndReason.EXPIRED,
        )
        assert event.reason is SessionEndReason.EXPIRED


# ---------------------------------------------------------------------------
# Hierarchy
# ---------------------------------------------------------------------------


class TestHierarchy:
    @pytest.mark.parametrize("event", _sample_events(UserId.generate()))
    def test_every_event_is_a_domain_event(self, event: DomainEvent) -> None:
        assert isinstance(event, DomainEvent)
