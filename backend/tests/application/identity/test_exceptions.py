"""Unit tests for the Identity application exceptions and their translation.

Covers every branch of :func:`translate_domain_errors` (each domain error family,
the pass-through, and the deliberately non-translated faults), plus the stable
error codes and preservation of the original cause.
"""

from __future__ import annotations

import pytest

from apps.identity.application.exceptions import (
    ApplicationError,
    EmailAlreadyInUseError,
    InvalidInputError,
    PhoneAlreadyInUseError,
    PolicyViolationError,
    UserNotFoundError,
    UserStateConflictError,
    WeakPasswordError,
    translate_domain_errors,
)
from apps.identity.domain.exceptions import (
    InvalidEmailError,
    PolicyConfigurationError,
    UserDeletedError,
)
from apps.identity.domain.exceptions import (
    PolicyViolationError as DomainPolicyViolationError,
)
from apps.identity.domain.exceptions import (
    WeakPasswordError as DomainWeakPasswordError,
)


class TestTranslateDomainErrors:
    def test_passes_through_when_no_error(self) -> None:
        marker = []
        with translate_domain_errors():
            marker.append(1)
        assert marker == [1]

    def test_value_object_error_becomes_invalid_input(self) -> None:
        with pytest.raises(InvalidInputError) as excinfo, translate_domain_errors():
            raise InvalidEmailError("bad email")
        assert isinstance(excinfo.value.__cause__, InvalidEmailError)

    def test_weak_password_error_is_translated_with_violations(self) -> None:
        with pytest.raises(WeakPasswordError) as excinfo, translate_domain_errors():
            raise DomainWeakPasswordError(("too_short", "missing_digit"))
        assert excinfo.value.violations == ("too_short", "missing_digit")
        assert isinstance(excinfo.value.__cause__, DomainWeakPasswordError)

    def test_generic_policy_violation_is_translated(self) -> None:
        with pytest.raises(PolicyViolationError) as excinfo, translate_domain_errors():
            raise DomainPolicyViolationError("nope")
        assert isinstance(excinfo.value.__cause__, DomainPolicyViolationError)

    def test_user_state_error_carries_domain_code(self) -> None:
        with pytest.raises(UserStateConflictError) as excinfo, translate_domain_errors():
            raise UserDeletedError("deleted")
        assert excinfo.value.domain_code == "UserDeletedError"
        assert isinstance(excinfo.value.__cause__, UserDeletedError)

    def test_configuration_error_is_not_translated(self) -> None:
        with pytest.raises(PolicyConfigurationError), translate_domain_errors():
            raise PolicyConfigurationError("misconfigured")


class TestErrorCodes:
    def test_codes_are_stable(self) -> None:
        assert ApplicationError.code == "application_error"
        assert UserNotFoundError.code == "user_not_found"
        assert EmailAlreadyInUseError.code == "email_already_in_use"
        assert PhoneAlreadyInUseError.code == "phone_already_in_use"
        assert InvalidInputError.code == "invalid_input"
        assert UserStateConflictError.code == "user_state_conflict"
        assert WeakPasswordError.code == "weak_password"
        assert PolicyViolationError.code == "policy_violation"

    def test_all_are_application_errors(self) -> None:
        for exc_type in (
            UserNotFoundError,
            EmailAlreadyInUseError,
            PhoneAlreadyInUseError,
            InvalidInputError,
            UserStateConflictError,
            WeakPasswordError,
            PolicyViolationError,
        ):
            assert issubclass(exc_type, ApplicationError)
