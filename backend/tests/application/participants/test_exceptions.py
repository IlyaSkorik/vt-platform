"""Unit tests for the Participants application error vocabulary.

Verifies that :func:`translate_domain_errors` maps each domain error onto its
application counterpart (preserving the cause and the stable ``code``), and that
faults which signal a programming/composition mistake propagate unchanged.
"""

from __future__ import annotations

import pytest

from apps.participants.application.exceptions import (
    ActivationBlockedError,
    ApplicationError,
    InvalidInputError,
    ParticipantStateConflictError,
    PolicyViolationError,
    translate_domain_errors,
)
from apps.participants.domain.exceptions import (
    ActivationRequirementsError,
    AgeGroupUndefinedError,
    AliasRevealsIdentityError,
    DirectConstructionError,
    InvalidDisplayAliasError,
    ParticipantErasedError,
)


def test_value_object_error_becomes_invalid_input() -> None:
    with pytest.raises(InvalidInputError) as exc:  # noqa: SIM117
        with translate_domain_errors():
            raise InvalidDisplayAliasError("bad alias")
    assert exc.value.code == "invalid_input"
    assert isinstance(exc.value.__cause__, InvalidDisplayAliasError)


def test_activation_requirements_becomes_activation_blocked() -> None:
    with pytest.raises(ActivationBlockedError) as exc:  # noqa: SIM117
        with translate_domain_errors():
            raise ActivationRequirementsError("blocked", reason="consent_missing")
    assert exc.value.code == "activation_blocked"
    assert exc.value.reason == "consent_missing"


def test_alias_leak_becomes_policy_violation() -> None:
    with pytest.raises(PolicyViolationError) as exc:  # noqa: SIM117
        with translate_domain_errors():
            raise AliasRevealsIdentityError("leak")
    assert exc.value.code == "policy_violation"


def test_age_group_undefined_becomes_policy_violation() -> None:
    with pytest.raises(PolicyViolationError):  # noqa: SIM117
        with translate_domain_errors():
            raise AgeGroupUndefinedError("no band")


def test_participant_state_error_becomes_state_conflict() -> None:
    with pytest.raises(ParticipantStateConflictError) as exc:  # noqa: SIM117
        with translate_domain_errors():
            raise ParticipantErasedError("erased")
    assert exc.value.code == "participant_state_conflict"
    assert exc.value.domain_code == "ParticipantErasedError"


def test_composition_faults_propagate_unchanged() -> None:
    with pytest.raises(DirectConstructionError):  # noqa: SIM117
        with translate_domain_errors():
            raise DirectConstructionError("built directly")


def test_application_error_base_code() -> None:
    assert ApplicationError.code == "application_error"
