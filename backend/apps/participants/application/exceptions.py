"""Application-layer exceptions for the Participants bounded context.

The application layer speaks its **own** error vocabulary. Use cases catch the
typed domain errors raised by value objects, policies, and the ``Participant``
aggregate and re-raise them as :class:`ApplicationError` subclasses, so callers
(the DRF edge, a CLI, a task) depend only on application-level meaning — never on
the domain's internal exception tree (ARCH-001 §7.6).

Two rules shape this module:

* **Never swallow.** Every translation uses ``raise ... from exc`` so the original
  domain error is preserved as the cause; nothing is silently discarded. Errors
  that signal a *programming/composition* fault rather than a client-correctable
  condition —
  :class:`~apps.participants.domain.exceptions.PolicyConfigurationError`,
  :class:`~apps.participants.domain.exceptions.DirectConstructionError` — are
  deliberately **not** translated and propagate unchanged.
* **Framework-free.** Standard library only — no Django, no DRF. Each error
  carries a stable, machine-readable :attr:`ApplicationError.code` that the
  presentation layer maps to an RFC 9457 Problem Details ``type``.

The translation itself lives in :func:`translate_domain_errors`, a context manager
wrapped around the domain calls inside each handler.
"""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from typing import ClassVar

from apps.participants.domain.exceptions import (
    ActivationRequirementsError as DomainActivationRequirementsError,
)
from apps.participants.domain.exceptions import (
    ParticipantStateError,
    ValueObjectValidationError,
)
from apps.participants.domain.exceptions import (
    PolicyViolationError as DomainPolicyViolationError,
)

__all__ = [
    "ActivationBlockedError",
    "ApplicationError",
    "DisplayAliasAlreadyInUseError",
    "InvalidInputError",
    "ParticipantNotFoundError",
    "ParticipantStateConflictError",
    "PolicyViolationError",
    "translate_domain_errors",
]


class ApplicationError(Exception):
    """Base class for every error the Participants application layer raises.

    Carries a stable :attr:`code` (subclasses override it) that the presentation
    edge translates into a Problem Details ``type``, decoupling HTTP concerns from
    the use cases.
    """

    code: ClassVar[str] = "application_error"


class ParticipantNotFoundError(ApplicationError):
    """No participant matched the identifier/lookup a use case required.

    Raised by a handler when a repository lookup returns ``None`` for a participant
    the operation assumes exists. Has no domain counterpart: absence is a use-case
    concern, not a domain invariant.
    """

    code: ClassVar[str] = "participant_not_found"


class DisplayAliasAlreadyInUseError(ApplicationError):
    """The requested display alias is already used by another active participant.

    Raised from the application-level uniqueness pre-check (via
    :meth:`ParticipantRepository.exists_by_display_alias` / ``get_by_display_alias``)
    before the domain is invoked. Uniqueness spans aggregates, so it is enforced
    here, not inside a single ``Participant``.
    """

    code: ClassVar[str] = "display_alias_already_in_use"


class InvalidInputError(ApplicationError):
    """A command carried a value the domain refused to construct.

    The application translation of
    :class:`~apps.participants.domain.exceptions.ValueObjectValidationError` (a bad
    id, name, date of birth, alias, or consent reference). It means the *input* is
    malformed — distinct from a well-formed input a business rule rejects
    (:class:`PolicyViolationError`) or a lifecycle conflict
    (:class:`ParticipantStateConflictError`).
    """

    code: ClassVar[str] = "invalid_input"


class ParticipantStateConflictError(ApplicationError):
    """The operation is illegal in the participant's current state.

    The application translation of
    :class:`~apps.participants.domain.exceptions.ParticipantStateError` (e.g.
    verifying a non-created participant, activating a non-verified one, mutating an
    erased participant, a duplicate guardian link). :attr:`domain_code` preserves
    the concrete domain error name for precise presentation mapping.
    """

    code: ClassVar[str] = "participant_state_conflict"

    def __init__(self, message: str, *, domain_code: str) -> None:
        super().__init__(message)
        self.domain_code = domain_code


class ActivationBlockedError(ApplicationError):
    """Activation was blocked because its preconditions are not met (PRT-001).

    The application translation of
    :class:`~apps.participants.domain.exceptions.ActivationRequirementsError`. It is
    a lifecycle conflict, but distinguished from the generic
    :class:`ParticipantStateConflictError` because it carries the machine-readable
    :attr:`reason` (no responsible adult / consent missing) the edge surfaces to the
    guardian or teacher.
    """

    code: ClassVar[str] = "activation_blocked"

    def __init__(self, message: str, *, reason: str) -> None:
        super().__init__(message)
        self.reason = reason


class PolicyViolationError(ApplicationError):
    """A business policy rejected a well-formed operation.

    The application translation of the domain
    :class:`~apps.participants.domain.exceptions.PolicyViolationError` base — an
    undefined age band (PRT-002) or an identity-leaking display alias (JDG-006).
    """

    code: ClassVar[str] = "policy_violation"


@contextmanager
def translate_domain_errors() -> Iterator[None]:
    """Translate Participants **domain** errors into **application** errors.

    Wrap the domain-touching part of a use case in this context manager::

        with translate_domain_errors():
            alias = DisplayAlias(command.display_alias)
            events = participant.reassign_display_alias(alias, ..., now=now)

    Each domain error is re-raised as its application counterpart with the original
    kept as ``__cause__`` (``raise ... from exc``); nothing is swallowed. More
    specific subclasses are matched before their bases (a domain
    ``ActivationRequirementsError`` before the ``ParticipantStateError`` base).
    Errors that are programming/composition faults rather than client conditions are
    intentionally not handled here and propagate unchanged.
    """
    try:
        yield
    except ValueObjectValidationError as exc:
        raise InvalidInputError(str(exc)) from exc
    except DomainActivationRequirementsError as exc:
        raise ActivationBlockedError(str(exc), reason=exc.reason) from exc
    except DomainPolicyViolationError as exc:
        raise PolicyViolationError(str(exc)) from exc
    except ParticipantStateError as exc:
        raise ParticipantStateConflictError(str(exc), domain_code=type(exc).__name__) from exc
