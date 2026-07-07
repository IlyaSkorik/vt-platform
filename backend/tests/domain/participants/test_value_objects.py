"""Unit tests for the Participants value objects.

Framework-free, database-free (ARCH-001 §28.2). Each value object is driven purely
through its public surface and asserted on by value: construction validation, the
normalized/derived views it exposes, and its immutability. Coverage spans every
identifier type, ``PersonName``, ``DateOfBirth`` age derivation, ``AgeGroup`` bands,
``DisplayAlias``, ``ConsentReference``, ``ActorReference``, ``GuardianLink``
transitions, and ``InstitutionAuthority``.
"""

from __future__ import annotations

import uuid
from dataclasses import FrozenInstanceError
from datetime import UTC, date, datetime

import pytest

from apps.participants.domain.exceptions import (
    InvalidConsentReferenceError,
    InvalidDateOfBirthError,
    InvalidDisplayAliasError,
    InvalidGuardianIdError,
    InvalidInstitutionIdError,
    InvalidParticipantIdError,
    InvalidPersonNameError,
    InvalidTeacherIdError,
    ValueObjectValidationError,
)
from apps.participants.domain.value_objects import (
    ActorReference,
    ActorType,
    AgeGroup,
    ConsentReference,
    DateOfBirth,
    DisplayAlias,
    GuardianId,
    GuardianLink,
    GuardianRelationshipType,
    InstitutionAuthority,
    InstitutionId,
    ParticipantId,
    PersonName,
    RelationshipStatus,
    TeacherId,
    _generate_uuid7,
)

NOW = datetime(2026, 7, 7, 12, 0, tzinfo=UTC)

_ID_TYPES = [
    (ParticipantId, InvalidParticipantIdError),
    (GuardianId, InvalidGuardianIdError),
    (TeacherId, InvalidTeacherIdError),
    (InstitutionId, InvalidInstitutionIdError),
]


# ---------------------------------------------------------------------------
# Identifiers
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(("id_type", "error"), _ID_TYPES)
def test_identifier_generate_is_uuid7_and_round_trips(
    id_type: type[ParticipantId], error: type[ValueObjectValidationError]
) -> None:
    identity = id_type.generate()
    assert identity.value.version == 7
    assert id_type.from_string(identity.json()) == identity
    assert id_type.from_uuid(identity.value) == identity
    assert str(identity) == identity.json()
    assert id_type.__name__ in repr(identity)


@pytest.mark.parametrize(("id_type", "error"), _ID_TYPES)
def test_identifier_rejects_non_uuid7(
    id_type: type[ParticipantId], error: type[ValueObjectValidationError]
) -> None:
    with pytest.raises(error):
        id_type.from_uuid(uuid.uuid4())


@pytest.mark.parametrize(("id_type", "error"), _ID_TYPES)
def test_identifier_rejects_malformed_string(
    id_type: type[ParticipantId], error: type[ValueObjectValidationError]
) -> None:
    with pytest.raises(error):
        id_type.from_string("not-a-uuid")


@pytest.mark.parametrize(("id_type", "error"), _ID_TYPES)
def test_identifier_rejects_wrong_type(
    id_type: type[ParticipantId], error: type[ValueObjectValidationError]
) -> None:
    with pytest.raises(error):
        id_type.from_uuid("nope")  # type: ignore[arg-type]


def test_participant_id_is_frozen() -> None:
    identity = ParticipantId.generate()
    with pytest.raises(FrozenInstanceError):
        identity.value = _generate_uuid7()  # type: ignore[misc]


# ---------------------------------------------------------------------------
# PersonName
# ---------------------------------------------------------------------------


def test_person_name_normalizes_and_renders() -> None:
    name = PersonName.of("  Ivan ", "Petrov", "Sergeevich")
    assert name.first_name == "Ivan"
    assert name.full == "Ivan Sergeevich Petrov"
    assert name.formal == "Petrov Ivan Sergeevich"
    assert name.short() == "Ivan Petrov"
    assert str(name) == name.full


def test_person_name_blank_middle_becomes_none() -> None:
    assert PersonName("Ivan", "Petrov", "   ").middle_name is None
    assert PersonName("Ivan", "Petrov", None).middle_name is None


@pytest.mark.parametrize("bad", ["", "   ", "Ivan1", "Ivan_"])
def test_person_name_rejects_invalid_parts(bad: str) -> None:
    with pytest.raises(InvalidPersonNameError):
        PersonName(bad, "Petrov")


def test_person_name_rejects_too_long() -> None:
    with pytest.raises(InvalidPersonNameError):
        PersonName("И" * 101, "Petrov")


def test_person_name_allows_hyphen_and_apostrophe() -> None:
    name = PersonName("Anne-Marie", "O'Neil")
    assert name.first_name == "Anne-Marie"
    assert name.last_name == "O'Neil"


# ---------------------------------------------------------------------------
# DateOfBirth
# ---------------------------------------------------------------------------


def test_date_of_birth_from_iso_and_isoformat() -> None:
    dob = DateOfBirth.from_iso("2015-03-04")
    assert dob.value == date(2015, 3, 4)
    assert dob.isoformat() == "2015-03-04"
    assert str(dob) == "2015-03-04"


def test_date_of_birth_rejects_bad_iso() -> None:
    with pytest.raises(InvalidDateOfBirthError):
        DateOfBirth.from_iso("nope")


def test_date_of_birth_rejects_datetime() -> None:
    with pytest.raises(InvalidDateOfBirthError):
        DateOfBirth(datetime(2015, 3, 4, tzinfo=UTC))


@pytest.mark.parametrize("year", [1899, 2201])
def test_date_of_birth_rejects_out_of_range_year(year: int) -> None:
    with pytest.raises(InvalidDateOfBirthError):
        DateOfBirth(date(year, 1, 1))


def test_age_in_years_before_and_after_birthday() -> None:
    dob = DateOfBirth(date(2015, 7, 8))
    assert dob.age_in_years(date(2026, 7, 7)) == 10  # birthday not yet reached
    assert dob.age_in_years(date(2026, 7, 8)) == 11  # birthday reached


def test_age_in_years_rejects_reference_before_birth() -> None:
    dob = DateOfBirth(date(2015, 7, 8))
    with pytest.raises(InvalidDateOfBirthError):
        dob.age_in_years(date(2015, 7, 7))


def test_is_after() -> None:
    dob = DateOfBirth(date(2015, 7, 8))
    assert dob.is_after(date(2015, 7, 7)) is True
    assert dob.is_after(date(2015, 7, 8)) is False


# ---------------------------------------------------------------------------
# AgeGroup
# ---------------------------------------------------------------------------


def test_age_group_normalizes_code_and_label() -> None:
    band = AgeGroup(code="  KIDS ", label="  Kids  6-9 ", min_age=6, max_age=9)
    assert band.code == "kids"
    assert band.label == "Kids 6-9"
    assert str(band) == "kids"


def test_age_group_contains_and_overlaps() -> None:
    a = AgeGroup(code="a", label="A", min_age=6, max_age=9)
    b = AgeGroup(code="b", label="B", min_age=9, max_age=12)
    c = AgeGroup(code="c", label="C", min_age=13, max_age=17)
    assert a.contains(6) and a.contains(9) and not a.contains(10)
    assert a.overlaps(b) is True
    assert a.overlaps(c) is False


@pytest.mark.parametrize("code", ["", "-bad", "Bad Space!"])
def test_age_group_rejects_bad_code(code: str) -> None:
    with pytest.raises(ValueObjectValidationError):
        AgeGroup(code=code, label="L", min_age=1, max_age=2)


def test_age_group_rejects_bad_label() -> None:
    with pytest.raises(ValueObjectValidationError):
        AgeGroup(code="a", label="   ", min_age=1, max_age=2)


def test_age_group_rejects_negative_min() -> None:
    with pytest.raises(ValueObjectValidationError):
        AgeGroup(code="a", label="L", min_age=-1, max_age=2)


def test_age_group_rejects_max_below_min() -> None:
    with pytest.raises(ValueObjectValidationError):
        AgeGroup(code="a", label="L", min_age=5, max_age=2)


# ---------------------------------------------------------------------------
# DisplayAlias
# ---------------------------------------------------------------------------


def test_display_alias_normalizes() -> None:
    alias = DisplayAlias.from_string("  Falcon  99 ")
    assert alias.value == "Falcon 99"
    assert str(alias) == "Falcon 99"


@pytest.mark.parametrize("bad", ["a", "x" * 65, "bad*char", "  "])
def test_display_alias_rejects_invalid(bad: str) -> None:
    with pytest.raises(InvalidDisplayAliasError):
        DisplayAlias(bad)


# ---------------------------------------------------------------------------
# ConsentReference
# ---------------------------------------------------------------------------


def test_consent_reference_of_string_and_uuid() -> None:
    cid = _generate_uuid7()
    from_uuid = ConsentReference.of(cid, "2026-01")
    from_str = ConsentReference.of(str(cid), "2026-01")
    assert from_uuid == from_str
    assert str(from_uuid) == f"{cid}@2026-01"


def test_consent_reference_rejects_bad_uuid_string() -> None:
    with pytest.raises(InvalidConsentReferenceError):
        ConsentReference.of("nope", "2026-01")


def test_consent_reference_rejects_non_uuid() -> None:
    with pytest.raises(InvalidConsentReferenceError):
        ConsentReference(consent_id="x", consent_version="1")  # type: ignore[arg-type]


def test_consent_reference_rejects_blank_version() -> None:
    with pytest.raises(InvalidConsentReferenceError):
        ConsentReference(consent_id=_generate_uuid7(), consent_version="   ")


# ---------------------------------------------------------------------------
# ActorReference
# ---------------------------------------------------------------------------


def test_actor_reference_of_string_and_uuid() -> None:
    aid = _generate_uuid7()
    ref = ActorReference.of(str(aid), ActorType.GUARDIAN)
    assert ref == ActorReference.of(aid, ActorType.GUARDIAN)
    assert str(ref) == f"guardian:{aid}"


def test_actor_reference_rejects_non_uuid() -> None:
    with pytest.raises(ValueObjectValidationError):
        ActorReference(actor_id="x", actor_type=ActorType.TEACHER)  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# GuardianLink
# ---------------------------------------------------------------------------


def test_guardian_link_transitions() -> None:
    link = GuardianLink(
        guardian_id=GuardianId.generate(),
        relationship_type=GuardianRelationshipType.MOTHER,
    )
    assert link.is_proposed() and not link.is_active() and not link.is_revoked()

    active = link.verified(now=NOW)
    assert active.is_active()
    assert active.established_at == NOW
    assert active.status is RelationshipStatus.ACTIVE

    revoked = active.revoked()
    assert revoked.is_revoked()
    # The original link is untouched (immutable value object).
    assert link.is_proposed()


# ---------------------------------------------------------------------------
# InstitutionAuthority
# ---------------------------------------------------------------------------


def test_institution_authority_holds_ids() -> None:
    inst = InstitutionId.generate()
    teacher = TeacherId.generate()
    authority = InstitutionAuthority(institution_id=inst, teacher_id=teacher)
    assert authority.institution_id == inst
    assert authority.teacher_id == teacher
    assert InstitutionAuthority(institution_id=inst).teacher_id is None
