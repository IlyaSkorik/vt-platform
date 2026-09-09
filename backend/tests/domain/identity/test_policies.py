"""Unit tests for the Identity domain policies.

Framework-free, database-free, clock-free (ARCH-001 §28.2): every time-dependent
policy is exercised by passing an explicit ``now``. Covers, per policy:
configuration validation (rejecting bad injected config), the happy path, and
each decision branch — targeting 100% statement coverage of ``policies.py``.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from apps.identity.domain.exceptions import (
    IdentityDomainError,
    PolicyConfigurationError,
    PolicyViolationError,
    WeakPasswordError,
)
from apps.identity.domain.policies import (
    AccountLockPolicy,
    AttemptDecision,
    ConsentPolicy,
    EmailVerificationPolicy,
    LockAction,
    PasswordPolicy,
    PasswordReuseChecker,
    PasswordValidationResult,
    PasswordViolation,
    PhoneVerificationPolicy,
    ReconsentReason,
    ResendDecision,
    ResendDenialReason,
    SessionAdmission,
    SessionExpiry,
    SessionExpiryReason,
    SessionPolicy,
)
from apps.identity.domain.value_objects import ConsentVersion

# A fixed reference instant — policies never read a clock, so tests are deterministic.
NOW = datetime(2026, 7, 6, 12, 0, tzinfo=UTC)


# ---------------------------------------------------------------------------
# PasswordPolicy
# ---------------------------------------------------------------------------


class TestPasswordPolicyConfiguration:
    def test_defaults_are_valid(self) -> None:
        policy = PasswordPolicy()
        assert policy.min_length == 12
        assert policy.history_depth == 5
        assert policy.max_age is None

    def test_is_immutable(self) -> None:
        policy = PasswordPolicy()
        with pytest.raises(AttributeError):
            policy.min_length = 4  # type: ignore[misc]

    def test_equal_configs_compare_equal(self) -> None:
        assert PasswordPolicy(forbidden_passwords=frozenset({"a"})) == PasswordPolicy(forbidden_passwords=frozenset({"a"}))

    @pytest.mark.parametrize(
        "kwargs",
        [
            {"min_length": 0},
            {"max_length": 0},
            {"max_length": 8, "min_length": 12},
            {"history_depth": -1},
            {"max_age": timedelta(0)},
            {"max_age": timedelta(days=-1)},
        ],
    )
    def test_rejects_invalid_configuration(self, kwargs: dict[str, object]) -> None:
        with pytest.raises(PolicyConfigurationError):
            PasswordPolicy(**kwargs)  # type: ignore[arg-type]


class TestPasswordPolicyValidation:
    def test_strong_password_passes(self) -> None:
        result = PasswordPolicy().validate("Str0ng-Passphrase!")
        assert result.is_valid
        assert result.violations == ()

    def test_too_short(self) -> None:
        result = PasswordPolicy(min_length=12).validate("Ab1!x")
        assert PasswordViolation.TOO_SHORT in result.violations

    def test_too_long(self) -> None:
        policy = PasswordPolicy(max_length=16, min_length=1)
        result = policy.validate("Ab1!" + "x" * 20)
        assert PasswordViolation.TOO_LONG in result.violations

    def test_forbidden_is_case_insensitive(self) -> None:
        policy = PasswordPolicy(min_length=1, forbidden_passwords=frozenset({"Password123!"}))
        result = policy.validate("password123!")
        assert PasswordViolation.FORBIDDEN in result.violations

    def test_missing_each_character_class(self) -> None:
        # A lowercase-only password trips every complexity rule except lowercase.
        result = PasswordPolicy(min_length=1).validate("abcdefgh")
        assert PasswordViolation.MISSING_UPPERCASE in result.violations
        assert PasswordViolation.MISSING_DIGIT in result.violations
        assert PasswordViolation.MISSING_SYMBOL in result.violations
        assert PasswordViolation.MISSING_LOWERCASE not in result.violations

    def test_cyrillic_is_outside_the_alphabet(self) -> None:
        # Its digit and its "!" are ASCII and do count; its letters do not — under
        # ascii_only, "П" is not an uppercase letter and "ароль" is not a lowercase one.
        result = PasswordPolicy().validate("ОченьДлинныйПароль1!")
        assert PasswordViolation.INVALID_ALPHABET in result.violations
        assert PasswordViolation.MISSING_UPPERCASE in result.violations
        assert PasswordViolation.MISSING_LOWERCASE in result.violations
        assert PasswordViolation.MISSING_DIGIT not in result.violations
        assert PasswordViolation.MISSING_SYMBOL not in result.violations

    def test_ascii_digits_are_the_only_digits(self) -> None:
        # An Arabic-Indic digit reads as a digit to str.isdigit but is not typeable
        # on the keyboards this platform's users have.
        result = PasswordPolicy(min_length=1).validate("Ab!\u0661")
        assert PasswordViolation.INVALID_ALPHABET in result.violations
        assert PasswordViolation.MISSING_DIGIT in result.violations

    def test_control_characters_are_outside_the_alphabet(self) -> None:
        result = PasswordPolicy(min_length=1).validate("Ab1!\n")
        assert PasswordViolation.INVALID_ALPHABET in result.violations

    def test_space_is_inside_the_alphabet(self) -> None:
        # A passphrase is a legitimate password and its spaces are its symbols.
        assert PasswordPolicy().validate("A correct horse 1").is_valid

    def test_alphabet_can_be_disabled(self) -> None:
        # Turning the knob off restores the Unicode-aware character classes, so a
        # deployment that wants passphrases in its own script gets them whole.
        policy = PasswordPolicy(ascii_only=False)
        result = policy.validate("ОченьДлинныйПароль1!")
        assert result.is_valid, result.violations

    def test_missing_lowercase(self) -> None:
        result = PasswordPolicy(min_length=1).validate("ABCDEFGH")
        assert PasswordViolation.MISSING_LOWERCASE in result.violations

    def test_complexity_can_be_disabled(self) -> None:
        policy = PasswordPolicy(
            min_length=1,
            require_uppercase=False,
            require_lowercase=False,
            require_digit=False,
            require_symbol=False,
        )
        assert policy.validate("aaaa").is_valid

    def test_collects_multiple_violations(self) -> None:
        result = PasswordPolicy(min_length=20).validate("short")
        assert PasswordViolation.TOO_SHORT in result.violations
        assert PasswordViolation.MISSING_UPPERCASE in result.violations
        assert len(result.violations) >= 2

    def test_is_acceptable_predicate(self) -> None:
        policy = PasswordPolicy()
        assert policy.is_acceptable("Str0ng-Passphrase!") is True
        assert policy.is_acceptable("weak") is False

    def test_enforce_is_silent_on_valid(self) -> None:
        PasswordPolicy().enforce("Str0ng-Passphrase!")  # no raise

    def test_enforce_raises_with_violations(self) -> None:
        with pytest.raises(WeakPasswordError) as exc:
            PasswordPolicy(min_length=20).enforce("short")
        assert PasswordViolation.TOO_SHORT.value in exc.value.violations
        assert isinstance(exc.value, PolicyViolationError)


class TestPasswordValidationResult:
    def test_raise_if_invalid_is_silent_when_valid(self) -> None:
        PasswordValidationResult().raise_if_invalid()  # no raise

    def test_raise_if_invalid_raises_when_invalid(self) -> None:
        result = PasswordValidationResult((PasswordViolation.TOO_SHORT,))
        with pytest.raises(WeakPasswordError):
            result.raise_if_invalid()


class TestPasswordExpiration:
    def test_never_expires_without_max_age(self) -> None:
        policy = PasswordPolicy()
        assert policy.is_expired(NOW - timedelta(days=3650), NOW) is False

    def test_expired_after_max_age(self) -> None:
        policy = PasswordPolicy(max_age=timedelta(days=90))
        assert policy.is_expired(NOW - timedelta(days=91), NOW) is True

    def test_not_expired_within_max_age(self) -> None:
        policy = PasswordPolicy(max_age=timedelta(days=90))
        assert policy.is_expired(NOW - timedelta(days=10), NOW) is False


class TestPasswordReuseChecker:
    def test_protocol_is_structurally_satisfied(self) -> None:
        # A conforming adapter needs no explicit subclassing (structural typing).
        class FakeChecker:
            def is_reused(self, candidate_password: str, *, history_depth: int) -> bool:
                return candidate_password == "reused" and history_depth > 0

        checker: PasswordReuseChecker = FakeChecker()
        assert checker.is_reused("reused", history_depth=PasswordPolicy().history_depth) is True
        assert checker.is_reused("fresh", history_depth=5) is False


# ---------------------------------------------------------------------------
# EmailVerificationPolicy
# ---------------------------------------------------------------------------


class TestEmailVerificationPolicy:
    @pytest.mark.parametrize(
        "kwargs",
        [
            {"verification_timeout": timedelta(0)},
            {"resend_interval": timedelta(0)},
            {"max_resend_attempts": 0},
        ],
    )
    def test_rejects_invalid_configuration(self, kwargs: dict[str, object]) -> None:
        with pytest.raises(PolicyConfigurationError):
            EmailVerificationPolicy(**kwargs)  # type: ignore[arg-type]

    def test_verification_expiry(self) -> None:
        policy = EmailVerificationPolicy(verification_timeout=timedelta(hours=24))
        assert policy.is_verification_expired(NOW - timedelta(hours=25), NOW) is True
        assert policy.is_verification_expired(NOW - timedelta(hours=1), NOW) is False

    def test_first_send_allowed(self) -> None:
        policy = EmailVerificationPolicy()
        decision = policy.evaluate_resend(last_sent_at=None, attempts_made=0, now=NOW)
        assert decision.allowed is True
        assert decision.attempts_remaining == policy.max_resend_attempts

    def test_resend_allowed_after_interval(self) -> None:
        policy = EmailVerificationPolicy(resend_interval=timedelta(minutes=1), max_resend_attempts=5)
        decision = policy.evaluate_resend(last_sent_at=NOW - timedelta(minutes=2), attempts_made=1, now=NOW)
        assert decision.allowed is True
        assert decision.attempts_remaining == 4

    def test_resend_blocked_by_cooldown(self) -> None:
        policy = EmailVerificationPolicy(resend_interval=timedelta(minutes=5))
        decision = policy.evaluate_resend(last_sent_at=NOW - timedelta(minutes=1), attempts_made=1, now=NOW)
        assert decision.allowed is False
        assert decision.reason is ResendDenialReason.COOLDOWN_ACTIVE
        assert decision.retry_after == timedelta(minutes=4)
        assert decision.attempts_remaining == 4

    def test_resend_blocked_by_max_attempts(self) -> None:
        policy = EmailVerificationPolicy(max_resend_attempts=3)
        decision = policy.evaluate_resend(last_sent_at=NOW - timedelta(hours=1), attempts_made=3, now=NOW)
        assert decision.allowed is False
        assert decision.reason is ResendDenialReason.MAX_ATTEMPTS_REACHED
        assert decision.attempts_remaining == 0


# ---------------------------------------------------------------------------
# PhoneVerificationPolicy
# ---------------------------------------------------------------------------


class TestPhoneVerificationPolicy:
    @pytest.mark.parametrize(
        "kwargs",
        [
            {"code_lifetime": timedelta(0)},
            {"resend_cooldown": timedelta(0)},
            {"max_attempts": 0},
        ],
    )
    def test_rejects_invalid_configuration(self, kwargs: dict[str, object]) -> None:
        with pytest.raises(PolicyConfigurationError):
            PhoneVerificationPolicy(**kwargs)  # type: ignore[arg-type]

    def test_code_expiry(self) -> None:
        policy = PhoneVerificationPolicy(code_lifetime=timedelta(minutes=10))
        assert policy.is_code_expired(NOW - timedelta(minutes=11), NOW) is True
        assert policy.is_code_expired(NOW - timedelta(minutes=1), NOW) is False

    def test_first_send_allowed(self) -> None:
        decision = PhoneVerificationPolicy().evaluate_resend(last_sent_at=None, now=NOW)
        assert decision.allowed is True
        assert decision.attempts_remaining is None

    def test_resend_allowed_after_cooldown(self) -> None:
        policy = PhoneVerificationPolicy(resend_cooldown=timedelta(seconds=60))
        decision = policy.evaluate_resend(last_sent_at=NOW - timedelta(seconds=90), now=NOW)
        assert decision.allowed is True

    def test_resend_blocked_by_cooldown(self) -> None:
        policy = PhoneVerificationPolicy(resend_cooldown=timedelta(seconds=60))
        decision = policy.evaluate_resend(last_sent_at=NOW - timedelta(seconds=20), now=NOW)
        assert decision.allowed is False
        assert decision.reason is ResendDenialReason.COOLDOWN_ACTIVE
        assert decision.retry_after == timedelta(seconds=40)

    def test_attempts_remaining(self) -> None:
        policy = PhoneVerificationPolicy(max_attempts=3)
        assert policy.evaluate_attempt(0) == AttemptDecision(allowed=True, attempts_remaining=3)
        assert policy.evaluate_attempt(2) == AttemptDecision(allowed=True, attempts_remaining=1)

    def test_attempts_exhausted(self) -> None:
        policy = PhoneVerificationPolicy(max_attempts=3)
        decision = policy.evaluate_attempt(3)
        assert decision.allowed is False
        assert decision.attempts_remaining == 0

    def test_attempts_never_negative(self) -> None:
        assert PhoneVerificationPolicy(max_attempts=3).evaluate_attempt(9).attempts_remaining == 0


# ---------------------------------------------------------------------------
# ConsentPolicy
# ---------------------------------------------------------------------------


class TestConsentPolicy:
    def test_rejects_invalid_validity_period(self) -> None:
        with pytest.raises(PolicyConfigurationError):
            ConsentPolicy(current_version=ConsentVersion("2026-01"), validity_period=timedelta(0))

    def test_never_granted_requires_consent(self) -> None:
        policy = ConsentPolicy(current_version=ConsentVersion("2026-01"))
        decision = policy.evaluate(granted_version=None, granted_at=None, now=NOW)
        assert decision.reconsent_required is True
        assert decision.reason is ReconsentReason.NEVER_GRANTED

    def test_granted_at_missing_requires_consent(self) -> None:
        policy = ConsentPolicy(current_version=ConsentVersion("2026-01"))
        decision = policy.evaluate(granted_version=ConsentVersion("2026-01"), granted_at=None, now=NOW)
        assert decision.reason is ReconsentReason.NEVER_GRANTED

    def test_superseded_version_requires_consent(self) -> None:
        policy = ConsentPolicy(current_version=ConsentVersion("2026-02"))
        decision = policy.evaluate(granted_version=ConsentVersion("2026-01"), granted_at=NOW, now=NOW)
        assert decision.reconsent_required is True
        assert decision.reason is ReconsentReason.VERSION_SUPERSEDED

    def test_expired_consent_requires_consent(self) -> None:
        policy = ConsentPolicy(current_version=ConsentVersion("2026-01"), validity_period=timedelta(days=365))
        decision = policy.evaluate(
            granted_version=ConsentVersion("2026-01"),
            granted_at=NOW - timedelta(days=400),
            now=NOW,
        )
        assert decision.reconsent_required is True
        assert decision.reason is ReconsentReason.CONSENT_EXPIRED

    def test_current_consent_is_satisfied(self) -> None:
        policy = ConsentPolicy(current_version=ConsentVersion("2026-01"), validity_period=timedelta(days=365))
        decision = policy.evaluate(
            granted_version=ConsentVersion("2026-01"),
            granted_at=NOW - timedelta(days=10),
            now=NOW,
        )
        assert decision.reconsent_required is False
        assert decision.reason is None

    def test_current_consent_without_expiry_is_satisfied(self) -> None:
        policy = ConsentPolicy(current_version=ConsentVersion("2026-01"))
        decision = policy.evaluate(
            granted_version=ConsentVersion("2026-01"),
            granted_at=NOW - timedelta(days=99999),
            now=NOW,
        )
        assert decision.reconsent_required is False

    def test_is_current_helper(self) -> None:
        policy = ConsentPolicy(current_version=ConsentVersion("2.0"))
        assert policy.is_current(ConsentVersion("2.0")) is True
        assert policy.is_current(ConsentVersion("2.1")) is True  # newer counts as current
        assert policy.is_current(ConsentVersion("1.9")) is False

    def test_is_expired_helper_without_period(self) -> None:
        policy = ConsentPolicy(current_version=ConsentVersion("2026-01"))
        assert policy.is_expired(NOW - timedelta(days=100000), NOW) is False


# ---------------------------------------------------------------------------
# SessionPolicy
# ---------------------------------------------------------------------------


class TestSessionPolicy:
    @pytest.mark.parametrize(
        "kwargs",
        [
            {"max_active_sessions": 0},
            {"idle_timeout": timedelta(0)},
            {"absolute_lifetime": timedelta(0)},
            {"remember_me_lifetime": timedelta(0)},
        ],
    )
    def test_rejects_invalid_configuration(self, kwargs: dict[str, object]) -> None:
        with pytest.raises(PolicyConfigurationError):
            SessionPolicy(**kwargs)  # type: ignore[arg-type]

    def test_lifetime_depends_on_remember_me(self) -> None:
        policy = SessionPolicy(absolute_lifetime=timedelta(hours=12), remember_me_lifetime=timedelta(days=30))
        assert policy.lifetime(remember_me=False) == timedelta(hours=12)
        assert policy.lifetime(remember_me=True) == timedelta(days=30)

    def test_active_session(self) -> None:
        policy = SessionPolicy(idle_timeout=timedelta(minutes=30), absolute_lifetime=timedelta(hours=12))
        decision = policy.evaluate_expiry(
            started_at=NOW - timedelta(hours=1),
            last_activity_at=NOW - timedelta(minutes=5),
            now=NOW,
        )
        assert decision == SessionExpiry.active()
        assert decision.expired is False

    def test_absolute_lifetime_exceeded(self) -> None:
        policy = SessionPolicy(absolute_lifetime=timedelta(hours=12))
        decision = policy.evaluate_expiry(
            started_at=NOW - timedelta(hours=13),
            last_activity_at=NOW,
            now=NOW,
        )
        assert decision.expired is True
        assert decision.reason is SessionExpiryReason.ABSOLUTE_LIFETIME_EXCEEDED

    def test_idle_timeout(self) -> None:
        policy = SessionPolicy(idle_timeout=timedelta(minutes=30), absolute_lifetime=timedelta(hours=12))
        decision = policy.evaluate_expiry(
            started_at=NOW - timedelta(hours=1),
            last_activity_at=NOW - timedelta(minutes=31),
            now=NOW,
        )
        assert decision.expired is True
        assert decision.reason is SessionExpiryReason.IDLE_TIMEOUT

    def test_remember_me_extends_absolute_lifetime(self) -> None:
        policy = SessionPolicy(
            absolute_lifetime=timedelta(hours=12),
            remember_me_lifetime=timedelta(days=30),
            idle_timeout=timedelta(days=90),
        )
        decision = policy.evaluate_expiry(
            started_at=NOW - timedelta(hours=13),
            last_activity_at=NOW,
            now=NOW,
            remember_me=True,
        )
        assert decision.expired is False

    def test_admission_allowed_under_cap(self) -> None:
        decision = SessionPolicy(max_active_sessions=5).evaluate_admission(3)
        assert decision == SessionAdmission(allowed=True, active_sessions=3, max_active_sessions=5, sessions_to_evict=0)

    def test_admission_denied_at_cap_requires_one_eviction(self) -> None:
        decision = SessionPolicy(max_active_sessions=5).evaluate_admission(5)
        assert decision.allowed is False
        assert decision.sessions_to_evict == 1

    def test_admission_denied_over_cap_reports_evictions(self) -> None:
        decision = SessionPolicy(max_active_sessions=5).evaluate_admission(7)
        assert decision.allowed is False
        assert decision.sessions_to_evict == 3


# ---------------------------------------------------------------------------
# AccountLockPolicy
# ---------------------------------------------------------------------------


class TestAccountLockPolicy:
    @pytest.mark.parametrize(
        "kwargs",
        [
            {"max_failed_attempts": 0},
            {"lock_duration": timedelta(0)},
            {"max_lockouts_before_permanent": 0},
        ],
    )
    def test_rejects_invalid_configuration(self, kwargs: dict[str, object]) -> None:
        with pytest.raises(PolicyConfigurationError):
            AccountLockPolicy(**kwargs)  # type: ignore[arg-type]

    def test_remaining_attempts(self) -> None:
        policy = AccountLockPolicy(max_failed_attempts=5)
        assert policy.remaining_attempts(2) == 3
        assert policy.remaining_attempts(9) == 0  # never negative

    def test_below_threshold_no_lock(self) -> None:
        policy = AccountLockPolicy(max_failed_attempts=5)
        assessment = policy.assess(failed_attempts=3, prior_lockouts=0, now=NOW)
        assert assessment.action is LockAction.NONE
        assert assessment.is_locked is False
        assert assessment.remaining_attempts == 2
        assert assessment.locked_until is None

    def test_reaching_threshold_temporary_lock(self) -> None:
        policy = AccountLockPolicy(
            max_failed_attempts=5,
            lock_duration=timedelta(minutes=15),
            max_lockouts_before_permanent=3,
        )
        assessment = policy.assess(failed_attempts=5, prior_lockouts=0, now=NOW)
        assert assessment.action is LockAction.TEMPORARY_LOCK
        assert assessment.is_locked is True
        assert assessment.locked_until == NOW + timedelta(minutes=15)
        assert assessment.lockout_count == 1
        assert assessment.remaining_attempts == 0

    def test_escalates_to_permanent_lock(self) -> None:
        policy = AccountLockPolicy(max_failed_attempts=5, max_lockouts_before_permanent=3)
        assessment = policy.assess(failed_attempts=5, prior_lockouts=2, now=NOW)
        assert assessment.action is LockAction.PERMANENT_LOCK
        assert assessment.locked_until is None
        assert assessment.lockout_count == 3

    def test_temporary_lock_expiry(self) -> None:
        policy = AccountLockPolicy(lock_duration=timedelta(minutes=15))
        locked_until = NOW + timedelta(minutes=15)
        assert policy.is_lock_expired(locked_until, NOW + timedelta(minutes=16)) is True
        assert policy.is_lock_expired(locked_until, NOW + timedelta(minutes=5)) is False

    def test_permanent_lock_never_expires(self) -> None:
        policy = AccountLockPolicy()
        assert policy.is_lock_expired(None, NOW + timedelta(days=3650)) is False


# ---------------------------------------------------------------------------
# Cross-cutting
# ---------------------------------------------------------------------------


class TestDecisionObjectsAreImmutable:
    def test_resend_decision_is_frozen(self) -> None:
        decision = ResendDecision.allow(attempts_remaining=3)
        with pytest.raises(AttributeError):
            decision.allowed = False  # type: ignore[misc]

    def test_lock_assessment_is_frozen(self) -> None:
        assessment = AccountLockPolicy().assess(failed_attempts=0, prior_lockouts=0, now=NOW)
        with pytest.raises(AttributeError):
            assessment.action = LockAction.PERMANENT_LOCK  # type: ignore[misc]


def test_policy_configuration_error_is_a_domain_error() -> None:
    assert issubclass(PolicyConfigurationError, IdentityDomainError)
    assert issubclass(PolicyConfigurationError, ValueError)
