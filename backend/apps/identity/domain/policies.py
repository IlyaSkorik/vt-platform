"""Business policies for the Identity & Access bounded context.

Explicit, testable **business rules** expressed as immutable, injectable policies
(ARCH-001 §4.2, §13.4). Each policy is a frozen, slotted dataclass whose fields
*are* its configuration: nothing is read from Django settings, environment, or a
file, and there is no module-level mutable state. The composition root constructs
a policy with the knobs it wants (Dependency Inversion) and hands it to a use
case; the same policy under the same configuration always decides the same way.

This is **pure domain code** (ARCH-001 §4.1, §7.2): standard library only — no
Django, no DRF, no ORM, no clock. Every method that reasons about time takes the
current instant (``now``) as an argument rather than reading a global clock, so
policies stay deterministic and trivially testable.

Policies never hash or verify passwords, touch a database, or perform IO. They
either **return a rich decision object** — never a bare ``bool`` where the caller
needs to know *why* — or, where an operation is simply forbidden, raise a typed
:class:`~apps.identity.domain.exceptions.PolicyViolationError`. Password reuse
(a comparison against stored hashes) and password expiration enforcement are the
concern of outer layers; this module owns only the *rule*, exposing the
:class:`PasswordReuseChecker` port and the expiration configuration.

Policies implemented here:

* :class:`PasswordPolicy`            — strength, forbidden values, reuse port, expiry config.
* :class:`EmailVerificationPolicy`   — link timeout, resend interval, resend cap.
* :class:`PhoneVerificationPolicy`   — code lifetime, resend cooldown, attempt cap.
* :class:`PasswordResetPolicy`       — reset-link timeout.
* :class:`ConsentPolicy`             — current version, expiry, re-consent decisions.
* :class:`SessionPolicy`             — concurrency, idle timeout, absolute & remember-me lifetimes.
* :class:`AccountLockPolicy`         — failed-login threshold, lock duration, permanent escalation.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import StrEnum
from typing import Protocol

from .exceptions import PolicyConfigurationError, WeakPasswordError
from .value_objects import ConsentVersion

__all__ = [
    "AccountLockPolicy",
    "AttemptDecision",
    "ConsentPolicy",
    "ConsentRequirement",
    "EmailVerificationPolicy",
    "LockAction",
    "LockAssessment",
    "PasswordPolicy",
    "PasswordResetPolicy",
    "PasswordReuseChecker",
    "PasswordValidationResult",
    "PasswordViolation",
    "PhoneVerificationPolicy",
    "ReconsentReason",
    "ResendDecision",
    "ResendDenialReason",
    "SessionAdmission",
    "SessionExpiry",
    "SessionExpiryReason",
    "SessionPolicy",
]


# ---------------------------------------------------------------------------
# Configuration guards (shared, framework-free)
# ---------------------------------------------------------------------------


def _ensure_positive_int(value: int, name: str) -> None:
    """Reject a count that must be at least one (e.g. a maximum-attempts knob)."""
    if value < 1:
        raise PolicyConfigurationError(f"{name} must be a positive integer, got {value}.")


def _ensure_non_negative_int(value: int, name: str) -> None:
    """Reject a negative count where zero is a legitimate value (e.g. history depth)."""
    if value < 0:
        raise PolicyConfigurationError(f"{name} must not be negative, got {value}.")


def _ensure_positive_timedelta(value: timedelta, name: str) -> None:
    """Reject a non-positive duration; a zero/negative window is never meaningful."""
    if value <= timedelta(0):
        raise PolicyConfigurationError(f"{name} must be a positive duration, got {value!r}.")


# ---------------------------------------------------------------------------
# PasswordPolicy
# ---------------------------------------------------------------------------


class PasswordViolation(StrEnum):
    """A single, machine-readable reason a password failed :class:`PasswordPolicy`.

    A :class:`~enum.StrEnum`, so each member *is* its wire value and travels
    straight into :class:`~apps.identity.domain.exceptions.WeakPasswordError` and
    on to the API edge for precise, localizable feedback.
    """

    TOO_SHORT = "пароль слишком короткий"
    TOO_LONG = "пароль слишком длинный"
    FORBIDDEN = "запрещенный"
    MISSING_UPPERCASE = "отсутствует заглавная буква"
    MISSING_LOWERCASE = "отсутствует строчная буква"
    MISSING_DIGIT = "отсутствует цифра"
    MISSING_SYMBOL = "отсутствует специальный символ"


@dataclass(frozen=True, slots=True)
class PasswordValidationResult:
    """The full outcome of checking a password — every failed rule, not just the first.

    Collecting *all* violations lets the edge show a complete checklist rather than
    making the user fix one problem at a time. Empty ``violations`` means the
    password satisfies the policy.
    """

    violations: tuple[PasswordViolation, ...] = ()

    @property
    def is_valid(self) -> bool:
        """Whether the password satisfied every rule (no violations)."""
        return not self.violations

    def raise_if_invalid(self) -> None:
        """Raise :class:`WeakPasswordError` carrying the violations, if any.

        The bridge from the decision style to the exception style, for call sites
        that would rather fail loudly than branch on the result.
        """
        if self.violations:
            raise WeakPasswordError(tuple(self.violations))


class PasswordReuseChecker(Protocol):
    """Port: decides whether a candidate password repeats a user's recent password.

    Reuse detection requires comparing against stored **hashes**, which is an
    infrastructure concern — the domain must never hash or verify. This policy
    therefore owns only the *rule's configuration* (:attr:`PasswordPolicy.history_depth`)
    and this port; a concrete adapter (wired at composition time, using the
    password hasher) implements the comparison. Kept here, beside the policy it
    serves, as the seam an outer layer plugs into.
    """

    def is_reused(self, candidate_password: str, *, history_depth: int) -> bool:
        """Whether ``candidate_password`` matches any of the last ``history_depth`` passwords."""
        ...


@dataclass(frozen=True, slots=True)
class PasswordPolicy:
    """Rules a plaintext password must satisfy before it is accepted (IDN-003).

    Owns length bounds, a forbidden-value denylist, and complexity requirements
    (character classes), returning a :class:`PasswordValidationResult` that lists
    *every* violation. Two adjacent concerns are represented but deliberately not
    executed here: **reuse** is delegated to the injected
    :class:`PasswordReuseChecker` port (this policy contributes only
    :attr:`history_depth`), and **expiration** is pure configuration
    (:attr:`max_age`) plus the :meth:`is_expired` calculation — enforcing either
    still never requires the domain to see a hash.

    Defaults follow current guidance (a 12+ character passphrase, all four
    character classes); every knob is overridable by injection.
    """

    min_length: int = 12
    max_length: int = 128
    require_uppercase: bool = True
    require_lowercase: bool = True
    require_digit: bool = True
    require_symbol: bool = True
    forbidden_passwords: frozenset[str] = field(default_factory=frozenset)
    #: How many previous passwords a :class:`PasswordReuseChecker` should reject
    #: against. Configuration for the reuse rule; not enforced in the domain.
    history_depth: int = 5
    #: Maximum age before a password must be rotated; ``None`` disables expiry.
    #: Configuration only — outer layers decide when to consult :meth:`is_expired`.
    max_age: timedelta | None = None
    #: Case-folded denylist, derived once so membership checks are O(1) and
    #: case-insensitive; excluded from equality/repr (it mirrors ``forbidden_passwords``).
    _forbidden_folded: frozenset[str] = field(init=False, repr=False, compare=False)

    def __post_init__(self) -> None:
        _ensure_positive_int(self.min_length, "min_length")
        _ensure_positive_int(self.max_length, "max_length")
        if self.max_length < self.min_length:
            raise PolicyConfigurationError(f"max_length ({self.max_length}) must be >= min_length ({self.min_length}).")
        _ensure_non_negative_int(self.history_depth, "history_depth")
        if self.max_age is not None:
            _ensure_positive_timedelta(self.max_age, "max_age")
        object.__setattr__(self, "_forbidden_folded", frozenset(p.casefold() for p in self.forbidden_passwords))

    def validate(self, password: str) -> PasswordValidationResult:
        """Check ``password`` against every rule and report all violations at once."""
        violations: list[PasswordViolation] = []
        length = len(password)
        if length < self.min_length:
            violations.append(PasswordViolation.TOO_SHORT)
        if length > self.max_length:
            violations.append(PasswordViolation.TOO_LONG)
        if password.casefold() in self._forbidden_folded:
            violations.append(PasswordViolation.FORBIDDEN)
        if self.require_uppercase and not any(c.isupper() for c in password):
            violations.append(PasswordViolation.MISSING_UPPERCASE)
        if self.require_lowercase and not any(c.islower() for c in password):
            violations.append(PasswordViolation.MISSING_LOWERCASE)
        if self.require_digit and not any(c.isdigit() for c in password):
            violations.append(PasswordViolation.MISSING_DIGIT)
        if self.require_symbol and not any(not c.isalnum() for c in password):
            violations.append(PasswordViolation.MISSING_SYMBOL)
        return PasswordValidationResult(tuple(violations))

    def enforce(self, password: str) -> None:
        """Validate and raise :class:`WeakPasswordError` on the first invalid password."""
        self.validate(password).raise_if_invalid()

    def is_acceptable(self, password: str) -> bool:
        """Convenience predicate for call sites that only need a yes/no answer."""
        return self.validate(password).is_valid

    def is_expired(self, set_at: datetime, now: datetime) -> bool:
        """Whether a password set at ``set_at`` has exceeded :attr:`max_age` by ``now``.

        Always ``False`` when expiry is disabled (``max_age is None``). Enforcing
        the result (forcing a rotation) is an outer-layer decision.
        """
        if self.max_age is None:
            return False
        return now - set_at >= self.max_age


# ---------------------------------------------------------------------------
# Resend / attempt decisions (shared by the verification policies)
# ---------------------------------------------------------------------------


class ResendDenialReason(StrEnum):
    """Why a verification message may not be resent right now."""

    COOLDOWN_ACTIVE = "cooldown_active"
    MAX_ATTEMPTS_REACHED = "max_attempts_reached"


@dataclass(frozen=True, slots=True)
class ResendDecision:
    """Whether a verification message may be resent, and — when not — why.

    Richer than a ``bool``: a denied decision tells the caller whether to wait
    (``retry_after``) or give up (``MAX_ATTEMPTS_REACHED``), and how many resends
    remain, which is exactly what a "resend code" endpoint needs to answer.
    """

    allowed: bool
    reason: ResendDenialReason | None = None
    retry_after: timedelta | None = None
    attempts_remaining: int | None = None

    @classmethod
    def allow(cls, *, attempts_remaining: int | None = None) -> ResendDecision:
        """A permitted resend, optionally reporting how many resends remain."""
        return cls(allowed=True, attempts_remaining=attempts_remaining)

    @classmethod
    def deny(
        cls,
        reason: ResendDenialReason,
        *,
        retry_after: timedelta | None = None,
        attempts_remaining: int | None = None,
    ) -> ResendDecision:
        """A refused resend with the reason and any wait/remaining context."""
        return cls(
            allowed=False,
            reason=reason,
            retry_after=retry_after,
            attempts_remaining=attempts_remaining,
        )


@dataclass(frozen=True, slots=True)
class AttemptDecision:
    """Whether another verification attempt is permitted, with the remaining budget."""

    allowed: bool
    attempts_remaining: int

    @classmethod
    def of(cls, attempts_made: int, max_attempts: int) -> AttemptDecision:
        """Build from attempts already made and the configured maximum."""
        remaining = max(0, max_attempts - attempts_made)
        return cls(allowed=remaining > 0, attempts_remaining=remaining)


# ---------------------------------------------------------------------------
# EmailVerificationPolicy
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class EmailVerificationPolicy:
    """Rules governing email-ownership verification links (IDN-002).

    A verification link is valid for :attr:`verification_timeout`; a new one may be
    requested at most once per :attr:`resend_interval` and at most
    :attr:`max_resend_attempts` times. Expiry is a simple predicate; the resend
    rule returns a :class:`ResendDecision` so the caller learns whether to wait or
    that the cap is reached.
    """

    verification_timeout: timedelta = timedelta(hours=24)
    resend_interval: timedelta = timedelta(minutes=1)
    max_resend_attempts: int = 5

    def __post_init__(self) -> None:
        _ensure_positive_timedelta(self.verification_timeout, "verification_timeout")
        _ensure_positive_timedelta(self.resend_interval, "resend_interval")
        _ensure_positive_int(self.max_resend_attempts, "max_resend_attempts")

    def is_verification_expired(self, sent_at: datetime, now: datetime) -> bool:
        """Whether a link issued at ``sent_at`` is no longer valid at ``now``."""
        return now - sent_at >= self.verification_timeout

    def evaluate_resend(self, *, last_sent_at: datetime | None, attempts_made: int, now: datetime) -> ResendDecision:
        """Decide whether the verification email may be resent now.

        ``last_sent_at`` is ``None`` when nothing has been sent yet (no cooldown
        applies); ``attempts_made`` counts prior resends against the cap.
        """
        remaining = self.max_resend_attempts - attempts_made
        if remaining <= 0:
            return ResendDecision.deny(ResendDenialReason.MAX_ATTEMPTS_REACHED, attempts_remaining=0)
        if last_sent_at is not None:
            elapsed = now - last_sent_at
            if elapsed < self.resend_interval:
                return ResendDecision.deny(
                    ResendDenialReason.COOLDOWN_ACTIVE,
                    retry_after=self.resend_interval - elapsed,
                    attempts_remaining=remaining,
                )
        return ResendDecision.allow(attempts_remaining=remaining)


# ---------------------------------------------------------------------------
# PhoneVerificationPolicy
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class PhoneVerificationPolicy:
    """Rules governing one-time SMS verification codes (IDN-002).

    A code is valid for :attr:`code_lifetime`; a new code may be requested no more
    often than :attr:`resend_cooldown`; and a user may submit at most
    :attr:`max_attempts` guesses against a live code before it must be invalidated.
    The attempt budget is a :class:`AttemptDecision` (never a bare ``bool``) so the
    caller can surface "N attempts left".
    """

    code_lifetime: timedelta = timedelta(minutes=10)
    resend_cooldown: timedelta = timedelta(seconds=60)
    max_attempts: int = 3

    def __post_init__(self) -> None:
        _ensure_positive_timedelta(self.code_lifetime, "code_lifetime")
        _ensure_positive_timedelta(self.resend_cooldown, "resend_cooldown")
        _ensure_positive_int(self.max_attempts, "max_attempts")

    def is_code_expired(self, issued_at: datetime, now: datetime) -> bool:
        """Whether a code issued at ``issued_at`` has lapsed by ``now``."""
        return now - issued_at >= self.code_lifetime

    def evaluate_resend(self, *, last_sent_at: datetime | None, now: datetime) -> ResendDecision:
        """Decide whether a fresh code may be sent, honouring the cooldown."""
        if last_sent_at is not None:
            elapsed = now - last_sent_at
            if elapsed < self.resend_cooldown:
                return ResendDecision.deny(
                    ResendDenialReason.COOLDOWN_ACTIVE,
                    retry_after=self.resend_cooldown - elapsed,
                )
        return ResendDecision.allow()

    def evaluate_attempt(self, attempts_made: int) -> AttemptDecision:
        """Whether another code submission is allowed given how many were already made."""
        return AttemptDecision.of(attempts_made, self.max_attempts)


# ---------------------------------------------------------------------------
# PasswordResetPolicy
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class PasswordResetPolicy:
    """Rules governing password-recovery links (IDN-004).

    A reset link is valid for :attr:`reset_timeout` measured from the instant it was
    issued (carried in the signed token). Kept deliberately shorter than the
    email-verification window: a reset link grants credential control and so must
    lapse quickly. Like the verification policies this is pure configuration plus a
    single time predicate; expiry is owned here, never by the signing adapter.
    """

    reset_timeout: timedelta = timedelta(hours=1)

    def __post_init__(self) -> None:
        _ensure_positive_timedelta(self.reset_timeout, "reset_timeout")

    def is_reset_expired(self, issued_at: datetime, now: datetime) -> bool:
        """Whether a reset link issued at ``issued_at`` is no longer valid at ``now``."""
        return now - issued_at >= self.reset_timeout


# ---------------------------------------------------------------------------
# ConsentPolicy
# ---------------------------------------------------------------------------


class ReconsentReason(StrEnum):
    """Why the platform must (re-)ask the user for consent."""

    NEVER_GRANTED = "never_granted"
    VERSION_SUPERSEDED = "version_superseded"
    CONSENT_EXPIRED = "consent_expired"


@dataclass(frozen=True, slots=True)
class ConsentRequirement:
    """Whether re-consent is required, and — when it is — the reason.

    Richer than a ``bool`` so a consumer can distinguish a first-time prompt from a
    forced re-acceptance after a new document version or an expiry, which may drive
    different copy and legal handling.
    """

    reconsent_required: bool
    reason: ReconsentReason | None = None

    @classmethod
    def satisfied(cls) -> ConsentRequirement:
        """The user's consent is current; nothing to ask."""
        return cls(reconsent_required=False)

    @classmethod
    def required(cls, reason: ReconsentReason) -> ConsentRequirement:
        """Consent must be (re-)collected for the given ``reason``."""
        return cls(reconsent_required=True, reason=reason)


@dataclass(frozen=True, slots=True)
class ConsentPolicy:
    """Rules for keeping a user's consent current (IDN-005, DATA-001 §4.1).

    Consent is always tied to a specific document version. This policy holds the
    :attr:`current_version` in force and an optional :attr:`validity_period` after
    which even a current-version grant must be renewed. :meth:`evaluate` folds the
    two rules — plus "never granted" — into a single :class:`ConsentRequirement`.
    """

    current_version: ConsentVersion
    #: How long a grant stays valid; ``None`` means it never expires on its own.
    validity_period: timedelta | None = None

    def __post_init__(self) -> None:
        if self.validity_period is not None:
            _ensure_positive_timedelta(self.validity_period, "validity_period")

    def is_current(self, version: ConsentVersion) -> bool:
        """Whether ``version`` is at least the version currently in force."""
        return not version.is_older_than(self.current_version)

    def is_expired(self, granted_at: datetime, now: datetime) -> bool:
        """Whether a grant made at ``granted_at`` has aged past :attr:`validity_period`."""
        if self.validity_period is None:
            return False
        return now - granted_at >= self.validity_period

    def evaluate(
        self,
        *,
        granted_version: ConsentVersion | None,
        granted_at: datetime | None,
        now: datetime,
    ) -> ConsentRequirement:
        """Decide whether the user must (re-)consent, and why.

        ``granted_version``/``granted_at`` are ``None`` when the user has never
        consented. A grant that is older than :attr:`current_version` is superseded;
        a grant past its validity window is expired; otherwise consent is current.
        """
        if granted_version is None or granted_at is None:
            return ConsentRequirement.required(ReconsentReason.NEVER_GRANTED)
        if granted_version.is_older_than(self.current_version):
            return ConsentRequirement.required(ReconsentReason.VERSION_SUPERSEDED)
        if self.is_expired(granted_at, now):
            return ConsentRequirement.required(ReconsentReason.CONSENT_EXPIRED)
        return ConsentRequirement.satisfied()


# ---------------------------------------------------------------------------
# SessionPolicy
# ---------------------------------------------------------------------------


class SessionExpiryReason(StrEnum):
    """Why a session is considered expired."""

    IDLE_TIMEOUT = "idle_timeout"
    ABSOLUTE_LIFETIME_EXCEEDED = "absolute_lifetime_exceeded"


@dataclass(frozen=True, slots=True)
class SessionExpiry:
    """Whether a session has expired, and — when it has — the governing reason."""

    expired: bool
    reason: SessionExpiryReason | None = None

    @classmethod
    def active(cls) -> SessionExpiry:
        """The session is still valid."""
        return cls(expired=False)

    @classmethod
    def lapsed(cls, reason: SessionExpiryReason) -> SessionExpiry:
        """The session has expired for the given ``reason``."""
        return cls(expired=True, reason=reason)


@dataclass(frozen=True, slots=True)
class SessionAdmission:
    """Whether a new session may be opened under the concurrency cap.

    Reports the current/allowed counts and — when the cap is hit —
    ``sessions_to_evict``, the number of oldest sessions the caller must close for
    the new one to fit. Richer than a ``bool`` so a "you're signed in on too many
    devices" flow can act precisely.
    """

    allowed: bool
    active_sessions: int
    max_active_sessions: int
    sessions_to_evict: int

    @classmethod
    def evaluate(cls, *, active_sessions: int, max_active_sessions: int) -> SessionAdmission:
        """Compute admission given the active count and the configured cap."""
        if active_sessions < max_active_sessions:
            return cls(
                allowed=True,
                active_sessions=active_sessions,
                max_active_sessions=max_active_sessions,
                sessions_to_evict=0,
            )
        return cls(
            allowed=False,
            active_sessions=active_sessions,
            max_active_sessions=max_active_sessions,
            sessions_to_evict=active_sessions - max_active_sessions + 1,
        )


@dataclass(frozen=True, slots=True)
class SessionPolicy:
    """Rules bounding authenticated sessions (IDN-008).

    Caps concurrent sessions (:attr:`max_active_sessions`) and expires each on the
    earlier of two clocks: inactivity (:attr:`idle_timeout`) and a hard cap since
    login (:attr:`absolute_lifetime`, or :attr:`remember_me_lifetime` for a
    "remember me" session). :meth:`evaluate_expiry` checks the absolute cap first —
    it can never be extended by activity — then idleness.
    """

    max_active_sessions: int = 5
    idle_timeout: timedelta = timedelta(minutes=30)
    absolute_lifetime: timedelta = timedelta(hours=12)
    remember_me_lifetime: timedelta = timedelta(days=30)

    def __post_init__(self) -> None:
        _ensure_positive_int(self.max_active_sessions, "max_active_sessions")
        _ensure_positive_timedelta(self.idle_timeout, "idle_timeout")
        _ensure_positive_timedelta(self.absolute_lifetime, "absolute_lifetime")
        _ensure_positive_timedelta(self.remember_me_lifetime, "remember_me_lifetime")

    def lifetime(self, *, remember_me: bool) -> timedelta:
        """The absolute lifetime for a session, longer when ``remember_me`` is set."""
        return self.remember_me_lifetime if remember_me else self.absolute_lifetime

    def evaluate_expiry(
        self,
        *,
        started_at: datetime,
        last_activity_at: datetime,
        now: datetime,
        remember_me: bool = False,
    ) -> SessionExpiry:
        """Decide whether a session has expired by ``now``, and why."""
        if now - started_at >= self.lifetime(remember_me=remember_me):
            return SessionExpiry.lapsed(SessionExpiryReason.ABSOLUTE_LIFETIME_EXCEEDED)
        if now - last_activity_at >= self.idle_timeout:
            return SessionExpiry.lapsed(SessionExpiryReason.IDLE_TIMEOUT)
        return SessionExpiry.active()

    def evaluate_admission(self, active_sessions: int) -> SessionAdmission:
        """Whether another concurrent session may be opened right now."""
        return SessionAdmission.evaluate(active_sessions=active_sessions, max_active_sessions=self.max_active_sessions)


# ---------------------------------------------------------------------------
# AccountLockPolicy
# ---------------------------------------------------------------------------


class LockAction(StrEnum):
    """The lockout action a :class:`AccountLockPolicy` assessment calls for."""

    NONE = "none"
    TEMPORARY_LOCK = "temporary_lock"
    PERMANENT_LOCK = "permanent_lock"


@dataclass(frozen=True, slots=True)
class LockAssessment:
    """The lockout outcome for a login failure: what to do and the surrounding counts.

    Bundles the :class:`LockAction`, the remaining pre-lock attempts, and — for a
    temporary lock — ``locked_until``. A permanent lock leaves ``locked_until`` as
    ``None`` (it never lifts on its own). Richer than a ``bool`` because the caller
    needs the deadline and the escalation state, not merely "locked / not locked".
    """

    action: LockAction
    failed_attempts: int
    remaining_attempts: int
    locked_until: datetime | None = None
    lockout_count: int = 0

    @property
    def is_locked(self) -> bool:
        """Whether this assessment locks the account (temporarily or permanently)."""
        return self.action is not LockAction.NONE


@dataclass(frozen=True, slots=True)
class AccountLockPolicy:
    """Rules for locking an account after repeated failed logins (IDN-007).

    After :attr:`max_failed_attempts` consecutive failures the account is locked for
    :attr:`lock_duration`. Repeated lockouts escalate: once the running
    lockout count reaches :attr:`max_lockouts_before_permanent`, the lock becomes
    permanent (a human must intervene). :meth:`assess` returns a
    :class:`LockAssessment` describing exactly what should happen.
    """

    max_failed_attempts: int = 5
    lock_duration: timedelta = timedelta(minutes=15)
    max_lockouts_before_permanent: int = 3

    def __post_init__(self) -> None:
        _ensure_positive_int(self.max_failed_attempts, "max_failed_attempts")
        _ensure_positive_timedelta(self.lock_duration, "lock_duration")
        _ensure_positive_int(self.max_lockouts_before_permanent, "max_lockouts_before_permanent")

    def remaining_attempts(self, failed_attempts: int) -> int:
        """How many failures remain before the next lockout (never negative)."""
        return max(0, self.max_failed_attempts - failed_attempts)

    def is_lock_expired(self, locked_until: datetime | None, now: datetime) -> bool:
        """Whether a temporary lock has elapsed by ``now``.

        A permanent lock (``locked_until is None``) never expires.
        """
        if locked_until is None:
            return False
        return now >= locked_until

    def assess(self, *, failed_attempts: int, prior_lockouts: int, now: datetime) -> LockAssessment:
        """Decide the lockout action for the current failure count.

        ``prior_lockouts`` is how many times this account has already been locked;
        it drives escalation to a permanent lock once the threshold is reached.
        """
        if failed_attempts < self.max_failed_attempts:
            return LockAssessment(
                action=LockAction.NONE,
                failed_attempts=failed_attempts,
                remaining_attempts=self.max_failed_attempts - failed_attempts,
                lockout_count=prior_lockouts,
            )
        lockout_count = prior_lockouts + 1
        if lockout_count >= self.max_lockouts_before_permanent:
            return LockAssessment(
                action=LockAction.PERMANENT_LOCK,
                failed_attempts=failed_attempts,
                remaining_attempts=0,
                locked_until=None,
                lockout_count=lockout_count,
            )
        return LockAssessment(
            action=LockAction.TEMPORARY_LOCK,
            failed_attempts=failed_attempts,
            remaining_attempts=0,
            locked_until=now + self.lock_duration,
            lockout_count=lockout_count,
        )
