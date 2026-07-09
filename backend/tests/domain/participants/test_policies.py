"""Unit tests for the Participants domain policies.

Framework-free, deterministic (ARCH-001 §28.2). Each policy is exercised for every
decision branch and every configuration guard: age-group derivation (PRT-002),
the guardianship/consent activation gate (PRT-001), and the pseudonymization guard
that keeps a judging alias from leaking the real name (JDG-006).
"""

from __future__ import annotations

from datetime import date

import pytest

from apps.participants.domain.exceptions import (
    AgeGroupUndefinedError,
    PolicyConfigurationError,
)
from apps.participants.domain.policies import (
    ActivationBlockReason,
    AgeGroupPolicy,
    GuardianshipPolicy,
    PseudonymizationPolicy,
)
from apps.participants.domain.value_objects import AgeGroup, DateOfBirth, DisplayAlias, PersonName

_BANDS = (
    AgeGroup(code="junior", label="Junior", min_age=6, max_age=9),
    AgeGroup(code="middle", label="Middle", min_age=10, max_age=13),
    AgeGroup(code="senior", label="Senior", min_age=14, max_age=17),
)


# ---------------------------------------------------------------------------
# AgeGroupPolicy
# ---------------------------------------------------------------------------


def test_age_group_policy_derives_band() -> None:
    policy = AgeGroupPolicy(bands=_BANDS)
    dob = DateOfBirth(date(2015, 1, 1))
    band = policy.derive(dob, reference_date=date(2026, 6, 1))  # age 11
    assert band.code == "middle"


def test_age_group_policy_rejects_empty_bands() -> None:
    with pytest.raises(PolicyConfigurationError):
        AgeGroupPolicy(bands=())


def test_age_group_policy_rejects_overlapping_bands() -> None:
    overlapping = (
        AgeGroup(code="a", label="A", min_age=6, max_age=10),
        AgeGroup(code="b", label="B", min_age=9, max_age=13),
    )
    with pytest.raises(PolicyConfigurationError):
        AgeGroupPolicy(bands=overlapping)


def test_age_group_policy_raises_when_uncovered() -> None:
    policy = AgeGroupPolicy(bands=_BANDS)
    dob = DateOfBirth(date(2020, 1, 1))  # age ~6? too young -> below junior at reference
    with pytest.raises(AgeGroupUndefinedError):
        policy.derive(dob, reference_date=date(2023, 1, 1))  # age 3, no band


# ---------------------------------------------------------------------------
# GuardianshipPolicy
# ---------------------------------------------------------------------------


def test_guardianship_satisfied_with_guardian_and_consent() -> None:
    assessment = GuardianshipPolicy().evaluate(active_guardian_count=1, has_institutional_authority=False, has_active_consent=True)
    assert assessment.allowed is True
    assert assessment.reason is None


def test_guardianship_satisfied_with_institution_and_consent() -> None:
    assessment = GuardianshipPolicy().evaluate(active_guardian_count=0, has_institutional_authority=True, has_active_consent=True)
    assert assessment.allowed is True


def test_guardianship_blocked_without_responsible_adult() -> None:
    assessment = GuardianshipPolicy().evaluate(active_guardian_count=0, has_institutional_authority=False, has_active_consent=True)
    assert assessment.allowed is False
    assert assessment.reason is ActivationBlockReason.NO_RESPONSIBLE_ADULT


def test_guardianship_blocked_without_consent() -> None:
    assessment = GuardianshipPolicy().evaluate(active_guardian_count=1, has_institutional_authority=False, has_active_consent=False)
    assert assessment.allowed is False
    assert assessment.reason is ActivationBlockReason.CONSENT_MISSING


def test_guardianship_consent_gate_can_be_disabled() -> None:
    assessment = GuardianshipPolicy(require_consent=False).evaluate(
        active_guardian_count=1, has_institutional_authority=False, has_active_consent=False
    )
    assert assessment.allowed is True


# ---------------------------------------------------------------------------
# PseudonymizationPolicy
# ---------------------------------------------------------------------------


def test_pseudonymization_detects_leaked_name() -> None:
    policy = PseudonymizationPolicy()
    name = PersonName("Ivan", "Petrov")
    assert policy.reveals_identity(DisplayAlias("Petrov 2026"), name=name) is True


def test_pseudonymization_allows_safe_alias() -> None:
    policy = PseudonymizationPolicy()
    name = PersonName("Ivan", "Petrov")
    assert policy.reveals_identity(DisplayAlias("Falcon-99"), name=name) is False


def test_pseudonymization_ignores_short_name_parts() -> None:
    policy = PseudonymizationPolicy(min_significant_length=3)
    name = PersonName("Li", "Wu")  # both parts shorter than the significance threshold
    assert policy.reveals_identity(DisplayAlias("Wu-champion"), name=name) is False


def test_pseudonymization_checks_middle_name() -> None:
    policy = PseudonymizationPolicy()
    name = PersonName("Ivan", "Petrov", "Sergeevich")
    assert policy.reveals_identity(DisplayAlias("sergeevich art"), name=name) is True


def test_pseudonymization_rejects_bad_config() -> None:
    with pytest.raises(PolicyConfigurationError):
        PseudonymizationPolicy(min_significant_length=0)
