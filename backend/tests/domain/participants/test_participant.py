"""Unit tests for the :class:`Participant` aggregate root.

Framework-free, database-free (ARCH-001 §28.2). Every test drives the aggregate
through its public surface — the ``create``/``rehydrate`` factories, the read-only
properties, and the guardian-link/consent/lifecycle behaviour — and asserts on the
domain events each method returns. Time is always supplied explicitly, so the suite
is deterministic. Coverage spans the full lifecycle (DATA-004 §4.3), the PRT-001
activation gate, PRT-008 duplicate-guardian handling, JDG-006 alias safety, the
erased-terminal guard, optimistic-version bumps, and identity-based equality.
"""

from __future__ import annotations

from datetime import UTC, date, datetime

import pytest

from apps.participants.domain.entities import Participant
from apps.participants.domain.events import (
    GuardianLinked,
    ParticipantActivated,
    ParticipantArchived,
    ParticipantCreated,
    ParticipantErasureRequested,
    ParticipantVerified,
)
from apps.participants.domain.exceptions import (
    ActivationRequirementsError,
    AliasRevealsIdentityError,
    ConsentNotRecordedError,
    DirectConstructionError,
    GuardianAlreadyLinkedError,
    GuardianLinkNotFoundError,
    GuardianLinkNotPendingError,
    InvalidDateOfBirthError,
    InvalidParticipantTransitionError,
    ParticipantErasedError,
    ParticipantNotArchivedError,
)
from apps.participants.domain.policies import (
    ActivationBlockReason,
    AgeGroupPolicy,
    GuardianshipPolicy,
    PseudonymizationPolicy,
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
    InstitutionId,
    ParticipantId,
    ParticipantStatus,
    PersonName,
    TeacherId,
    _generate_uuid7,
)

NOW = datetime(2026, 7, 7, 12, 0, tzinfo=UTC)
_PSEUDONYM = PseudonymizationPolicy()
_GUARDIANSHIP = GuardianshipPolicy()
_AGE_BANDS = AgeGroupPolicy(
    bands=(
        AgeGroup(code="junior", label="Junior", min_age=6, max_age=9),
        AgeGroup(code="middle", label="Middle", min_age=10, max_age=13),
    )
)


def _create(**overrides: object) -> Participant:
    kwargs: dict[str, object] = {
        "participant_id": ParticipantId.generate(),
        "name": PersonName("Ivan", "Petrov"),
        "date_of_birth": DateOfBirth(date(2015, 3, 4)),
        "display_alias": DisplayAlias("Falcon-99"),
        "created_by": ActorReference.of(_generate_uuid7(), ActorType.GUARDIAN),
        "now": NOW,
        "pseudonymization_policy": _PSEUDONYM,
    }
    kwargs.update(overrides)
    participant, _events = Participant.create(**kwargs)  # type: ignore[arg-type]
    return participant


def _activated() -> Participant:
    """A participant driven all the way to ``Active`` (guardian + consent)."""
    participant = _create()
    participant.verify(now=NOW)
    guardian = GuardianId.generate()
    participant.propose_guardian_link(
        guardian_id=guardian, relationship_type=GuardianRelationshipType.MOTHER, now=NOW
    )
    participant.verify_guardian_link(guardian_id=guardian, now=NOW)
    participant.record_consent(
        consent=ConsentReference.of(_generate_uuid7(), "2026-01"), now=NOW
    )
    participant.activate(policy=_GUARDIANSHIP, now=NOW)
    return participant


# ---------------------------------------------------------------------------
# Creation & rehydration
# ---------------------------------------------------------------------------


def test_create_emits_participant_created() -> None:
    pid = ParticipantId.generate()
    participant, events = Participant.create(
        participant_id=pid,
        name=PersonName("Ivan", "Petrov"),
        date_of_birth=DateOfBirth(date(2015, 3, 4)),
        display_alias=DisplayAlias("Falcon-99"),
        created_by=ActorReference.of(_generate_uuid7(), ActorType.GUARDIAN),
        now=NOW,
        pseudonymization_policy=_PSEUDONYM,
    )
    assert participant.status is ParticipantStatus.CREATED
    assert participant.version == 1
    assert len(events) == 1
    assert isinstance(events[0], ParticipantCreated)
    assert events[0].aggregate_id == pid


def test_create_rejects_future_date_of_birth() -> None:
    with pytest.raises(InvalidDateOfBirthError):
        _create(date_of_birth=DateOfBirth(date(2030, 1, 1)))


def test_create_rejects_identity_leaking_alias() -> None:
    with pytest.raises(AliasRevealsIdentityError):
        _create(display_alias=DisplayAlias("Petrov art"))


def test_direct_construction_is_forbidden() -> None:
    with pytest.raises(DirectConstructionError):
        Participant(
            _token=object(),
            _id=ParticipantId.generate(),
            _name=PersonName("Ivan", "Petrov"),
            _date_of_birth=DateOfBirth(date(2015, 3, 4)),
            _display_alias=DisplayAlias("Falcon-99"),
            _created_by=ActorReference.of(_generate_uuid7(), ActorType.GUARDIAN),
            _created_at=NOW,
            _updated_at=NOW,
        )


def test_rehydrate_preserves_state_and_emits_nothing() -> None:
    pid = ParticipantId.generate()
    participant = Participant.rehydrate(
        participant_id=pid,
        name=PersonName("Ivan", "Petrov"),
        date_of_birth=DateOfBirth(date(2015, 3, 4)),
        display_alias=DisplayAlias("Falcon-99"),
        created_by=ActorReference.of(_generate_uuid7(), ActorType.GUARDIAN),
        status=ParticipantStatus.ACTIVE,
        created_at=NOW,
        updated_at=NOW,
        version=7,
    )
    assert participant.status is ParticipantStatus.ACTIVE
    assert participant.version == 7


# ---------------------------------------------------------------------------
# Guardian relationships
# ---------------------------------------------------------------------------


def test_propose_then_verify_guardian_link() -> None:
    participant = _create()
    guardian = GuardianId.generate()
    assert participant.propose_guardian_link(
        guardian_id=guardian, relationship_type=GuardianRelationshipType.FATHER, now=NOW
    ) == []
    assert not participant.has_active_guardian()

    events = participant.verify_guardian_link(guardian_id=guardian, now=NOW)
    assert len(events) == 1
    assert isinstance(events[0], GuardianLinked)
    assert participant.active_guardian_count() == 1
    assert participant.has_active_guardian()


def test_duplicate_guardian_is_rejected() -> None:
    participant = _create()
    guardian = GuardianId.generate()
    participant.propose_guardian_link(
        guardian_id=guardian, relationship_type=GuardianRelationshipType.MOTHER, now=NOW
    )
    with pytest.raises(GuardianAlreadyLinkedError):
        participant.propose_guardian_link(
            guardian_id=guardian, relationship_type=GuardianRelationshipType.MOTHER, now=NOW
        )


def test_revoked_guardian_can_be_reproposed() -> None:
    participant = _create()
    guardian = GuardianId.generate()
    participant.propose_guardian_link(
        guardian_id=guardian, relationship_type=GuardianRelationshipType.MOTHER, now=NOW
    )
    participant.revoke_guardian_link(guardian_id=guardian, now=NOW)
    participant.propose_guardian_link(
        guardian_id=guardian, relationship_type=GuardianRelationshipType.FATHER, now=NOW
    )
    assert len(participant.guardian_links) == 1
    assert participant.guardian_links[0].is_proposed()


def test_verify_missing_guardian_link_raises() -> None:
    participant = _create()
    with pytest.raises(GuardianLinkNotFoundError):
        participant.verify_guardian_link(guardian_id=GuardianId.generate(), now=NOW)


def test_verify_non_proposed_guardian_link_raises() -> None:
    participant = _create()
    guardian = GuardianId.generate()
    participant.propose_guardian_link(
        guardian_id=guardian, relationship_type=GuardianRelationshipType.MOTHER, now=NOW
    )
    participant.verify_guardian_link(guardian_id=guardian, now=NOW)
    with pytest.raises(GuardianLinkNotPendingError):
        participant.verify_guardian_link(guardian_id=guardian, now=NOW)


def test_revoke_missing_guardian_link_raises() -> None:
    participant = _create()
    with pytest.raises(GuardianLinkNotFoundError):
        participant.revoke_guardian_link(guardian_id=GuardianId.generate(), now=NOW)


# ---------------------------------------------------------------------------
# Institution authority & consent
# ---------------------------------------------------------------------------


def test_authorize_institution_records_authority() -> None:
    participant = _create()
    inst = InstitutionId.generate()
    teacher = TeacherId.generate()
    participant.authorize_institution(institution_id=inst, teacher_id=teacher, now=NOW)
    assert participant.has_institutional_authority()
    assert participant.institution_authority is not None
    assert participant.institution_authority.institution_id == inst


def test_record_and_withdraw_consent() -> None:
    participant = _create()
    participant.record_consent(consent=ConsentReference.of(_generate_uuid7(), "2026-01"), now=NOW)
    assert participant.has_active_consent()
    participant.withdraw_consent(now=NOW)
    assert not participant.has_active_consent()


def test_withdraw_without_consent_raises() -> None:
    participant = _create()
    with pytest.raises(ConsentNotRecordedError):
        participant.withdraw_consent(now=NOW)


# ---------------------------------------------------------------------------
# Profile
# ---------------------------------------------------------------------------


def test_rename_updates_name() -> None:
    participant = _create()
    participant.rename(PersonName("Ivan", "Sidorov"), now=NOW)
    assert participant.name.last_name == "Sidorov"


def test_reassign_display_alias_guards_identity() -> None:
    participant = _create()
    participant.reassign_display_alias(
        DisplayAlias("Eagle-7"), pseudonymization_policy=_PSEUDONYM, now=NOW
    )
    assert participant.display_alias.value == "Eagle-7"
    with pytest.raises(AliasRevealsIdentityError):
        participant.reassign_display_alias(
            DisplayAlias("Petrov again"), pseudonymization_policy=_PSEUDONYM, now=NOW
        )


# ---------------------------------------------------------------------------
# Lifecycle
# ---------------------------------------------------------------------------


def test_verify_transition() -> None:
    participant = _create()
    events = participant.verify(now=NOW)
    assert participant.status is ParticipantStatus.VERIFIED
    assert participant.verified_at == NOW
    assert isinstance(events[0], ParticipantVerified)


def test_verify_wrong_state_raises() -> None:
    participant = _create()
    participant.verify(now=NOW)
    with pytest.raises(InvalidParticipantTransitionError):
        participant.verify(now=NOW)


def test_activate_happy_path() -> None:
    participant = _activated()
    assert participant.status is ParticipantStatus.ACTIVE
    assert participant.activated_at == NOW
    assert participant.is_active()


def test_activate_via_institution_authority() -> None:
    participant = _create()
    participant.verify(now=NOW)
    participant.authorize_institution(institution_id=InstitutionId.generate(), now=NOW)
    participant.record_consent(consent=ConsentReference.of(_generate_uuid7(), "1"), now=NOW)
    events = participant.activate(policy=_GUARDIANSHIP, now=NOW)
    assert isinstance(events[0], ParticipantActivated)


def test_activate_blocked_without_responsible_adult() -> None:
    participant = _create()
    participant.verify(now=NOW)
    participant.record_consent(consent=ConsentReference.of(_generate_uuid7(), "1"), now=NOW)
    with pytest.raises(ActivationRequirementsError) as exc:
        participant.activate(policy=_GUARDIANSHIP, now=NOW)
    assert exc.value.reason == ActivationBlockReason.NO_RESPONSIBLE_ADULT.value


def test_activate_blocked_without_consent() -> None:
    participant = _create()
    participant.verify(now=NOW)
    guardian = GuardianId.generate()
    participant.propose_guardian_link(
        guardian_id=guardian, relationship_type=GuardianRelationshipType.MOTHER, now=NOW
    )
    participant.verify_guardian_link(guardian_id=guardian, now=NOW)
    with pytest.raises(ActivationRequirementsError) as exc:
        participant.activate(policy=_GUARDIANSHIP, now=NOW)
    assert exc.value.reason == ActivationBlockReason.CONSENT_MISSING.value


def test_activate_wrong_state_raises() -> None:
    participant = _create()  # still Created, not Verified
    with pytest.raises(InvalidParticipantTransitionError):
        participant.activate(policy=_GUARDIANSHIP, now=NOW)


def test_archive_and_reactivate() -> None:
    participant = _activated()
    archived = participant.archive(now=NOW)
    assert participant.status.value == "archived"
    assert isinstance(archived[0], ParticipantArchived)

    reactivated = participant.reactivate(policy=_GUARDIANSHIP, now=NOW)
    assert participant.status.value == "active"
    assert participant.archived_at is None
    assert isinstance(reactivated[0], ParticipantActivated)


def test_archive_wrong_state_raises() -> None:
    participant = _create()
    with pytest.raises(InvalidParticipantTransitionError):
        participant.archive(now=NOW)


def test_reactivate_when_not_archived_raises() -> None:
    participant = _activated()
    with pytest.raises(ParticipantNotArchivedError):
        participant.reactivate(policy=_GUARDIANSHIP, now=NOW)


def test_request_erasure_from_active() -> None:
    participant = _activated()
    ref = _generate_uuid7()
    events = participant.request_erasure(request_reference=ref, now=NOW)
    assert participant.status is ParticipantStatus.ERASED
    assert participant.is_erased()
    assert isinstance(events[0], ParticipantErasureRequested)
    assert events[0].request_reference == ref


def test_request_erasure_from_created_raises() -> None:
    participant = _create()
    with pytest.raises(InvalidParticipantTransitionError):
        participant.request_erasure(request_reference=_generate_uuid7(), now=NOW)


def test_operations_after_erasure_are_forbidden() -> None:
    participant = _activated()
    participant.request_erasure(request_reference=_generate_uuid7(), now=NOW)
    with pytest.raises(ParticipantErasedError):
        participant.rename(PersonName("Ivan", "Sidorov"), now=NOW)
    with pytest.raises(ParticipantErasedError):
        participant.propose_guardian_link(
            guardian_id=GuardianId.generate(),
            relationship_type=GuardianRelationshipType.OTHER,
            now=NOW,
        )


# ---------------------------------------------------------------------------
# Derived age group, versioning, identity semantics
# ---------------------------------------------------------------------------


def test_derived_age_group() -> None:
    participant = _create()  # born 2015-03-04
    band = participant.derived_age_group(_AGE_BANDS, reference_date=NOW)  # age 11 at 2026-07-07
    assert band.code == "middle"


def test_version_bumps_per_mutation() -> None:
    participant = _create()
    assert participant.version == 1
    participant.verify(now=NOW)
    assert participant.version == 2
    participant.rename(PersonName("Ivan", "Sidorov"), now=NOW)
    assert participant.version == 3


def test_equality_and_hash_by_id() -> None:
    pid = ParticipantId.generate()
    a = _create(participant_id=pid)
    b = _create(participant_id=pid)
    assert a == b
    assert hash(a) == hash(b)
    assert a != _create()
    assert a != "not-a-participant"


def test_repr_is_safe_and_informative() -> None:
    participant = _create()
    text = repr(participant)
    assert "Participant(" in text
    assert "Falcon-99" in text


def test_read_only_properties_expose_state() -> None:
    participant = _activated()
    participant.archive(now=NOW)
    assert participant.id.value.version == 7
    assert participant.name.full == "Ivan Petrov"
    assert participant.date_of_birth.isoformat() == "2015-03-04"
    assert participant.created_by.actor_type is ActorType.GUARDIAN
    assert participant.created_at == NOW
    assert participant.updated_at == NOW
    assert participant.verified_at == NOW
    assert participant.activated_at == NOW
    assert participant.archived_at == NOW
    assert participant.erased_at is None
    assert participant.consent is not None
