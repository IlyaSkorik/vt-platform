"""Application-layer exceptions for the Identity & Access bounded context.

The application layer speaks its **own** error vocabulary. Use cases catch the
typed domain errors raised by value objects, policies, and the ``User`` aggregate
and re-raise them as :class:`ApplicationError` subclasses, so callers (a future
DRF edge, a CLI, a task) depend only on application-level meaning — never on the
domain's internal exception tree (ARCH-001 §7.6).

Two rules shape this module:

* **Never swallow.** Every translation uses ``raise ... from exc`` so the original
  domain error is preserved as the cause; nothing is silently discarded. Errors
  that signal a *programming/composition* fault rather than a client-correctable
  condition — :class:`~apps.identity.domain.exceptions.PolicyConfigurationError`,
  :class:`~apps.identity.domain.exceptions.DirectConstructionError` — are
  deliberately **not** translated and propagate unchanged.
* **Framework-free.** Standard library only — no Django, no DRF. Each error
  carries a stable, machine-readable :attr:`ApplicationError.code` that the
  presentation layer maps to an RFC 9457 Problem Details ``type``.

The translation itself lives in :func:`translate_domain_errors`, a context
manager wrapped around the domain calls inside each handler.
"""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from typing import ClassVar

from apps.identity.domain.exceptions import (
    PolicyViolationError as DomainPolicyViolationError,
)
from apps.identity.domain.exceptions import (
    UserStateError,
    ValueObjectValidationError,
)
from apps.identity.domain.exceptions import (
    WeakPasswordError as DomainWeakPasswordError,
)

__all__ = [
    "ApplicationError",
    "EmailAlreadyInUseError",
    "InvalidInputError",
    "PhoneAlreadyInUseError",
    "PolicyViolationError",
    "UserNotFoundError",
    "UserStateConflictError",
    "WeakPasswordError",
    "translate_domain_errors",
]


class ApplicationError(Exception):
    """Base class for every error the Identity application layer raises.

    Carries a stable :attr:`code` (subclasses override it) that the presentation
    edge translates into a Problem Details ``type``, decoupling HTTP concerns from
    the use cases.
    """

    code: ClassVar[str] = "application_error"


class UserNotFoundError(ApplicationError):
    """No user matched the identifier/lookup a use case required.

    Raised by a handler when a repository lookup returns ``None`` for a user the
    operation assumes exists. Has no domain counterpart: absence is a use-case
    concern, not a domain invariant.
    """

    code: ClassVar[str] = "user_not_found"


class EmailAlreadyInUseError(ApplicationError):
    """The requested email is already registered to another account.

    Raised from the application-level uniqueness pre-check (via
    :meth:`UserRepository.exists_by_email` / ``get_by_email``) before the domain is
    invoked. Uniqueness spans aggregates, so it is enforced here, not inside a
    single ``User``.
    """

    code: ClassVar[str] = "email_already_in_use"


class PhoneAlreadyInUseError(ApplicationError):
    """The requested phone number is already registered to another account."""

    code: ClassVar[str] = "phone_already_in_use"


class InvalidInputError(ApplicationError):
    """A command carried a value the domain refused to construct.

    The application translation of
    :class:`~apps.identity.domain.exceptions.ValueObjectValidationError` (a bad
    email, phone, name, locale, timezone, consent version, or user id). It means
    the *input* is malformed — distinct from a well-formed input that a business
    rule rejects (:class:`WeakPasswordError`, :class:`PolicyViolationError`) or a
    lifecycle conflict (:class:`UserStateConflictError`).
    """

    code: ClassVar[str] = "invalid_input"


class UserStateConflictError(ApplicationError):
    """The operation is illegal in the user's current state.

    The application translation of
    :class:`~apps.identity.domain.exceptions.UserStateError` (e.g. verifying an
    already-verified email, mutating a deleted account, unlocking one that is not
    locked, an expired verification, stale consent). :attr:`domain_code` preserves
    the concrete domain error name for precise presentation mapping.
    """

    code: ClassVar[str] = "user_state_conflict"

    def __init__(self, message: str, *, domain_code: str) -> None:
        super().__init__(message)
        self.domain_code = domain_code


class WeakPasswordError(ApplicationError):
    """A proposed password failed the active password policy.

    The application translation of
    :class:`~apps.identity.domain.exceptions.WeakPasswordError`; preserves the
    machine-readable :attr:`violations` so the edge can render a precise,
    localizable checklist.
    """

    code: ClassVar[str] = "weak_password"

    def __init__(self, violations: tuple[str, ...], message: str) -> None:
        super().__init__(message)
        self.violations = violations


class PolicyViolationError(ApplicationError):
    """A business policy rejected a well-formed operation.

    The application translation of the domain
    :class:`~apps.identity.domain.exceptions.PolicyViolationError` base for any
    policy violation not represented by a more specific application error.
    """

    code: ClassVar[str] = "policy_violation"


@contextmanager
def translate_domain_errors() -> Iterator[None]:
    """Translate Identity **domain** errors into **application** errors.

    Wrap the domain-touching part of a use case in this context manager::

        with translate_domain_errors():
            email = Email(command.email)
            events = user.change_email(email, now=now)

    Each domain error is re-raised as its application counterpart with the original
    kept as ``__cause__`` (``raise ... from exc``); nothing is swallowed. More
    specific subclasses are matched before their bases (a domain
    ``WeakPasswordError`` before the ``PolicyViolationError`` base). Errors that are
    programming/composition faults rather than client conditions are intentionally
    not handled here and propagate unchanged.
    """
    try:
        yield
    except ValueObjectValidationError as exc:
        raise InvalidInputError(str(exc)) from exc
    except DomainWeakPasswordError as exc:
        raise WeakPasswordError(exc.violations, str(exc)) from exc
    except DomainPolicyViolationError as exc:
        raise PolicyViolationError(str(exc)) from exc
    except UserStateError as exc:
        raise UserStateConflictError(str(exc), domain_code=type(exc).__name__) from exc
