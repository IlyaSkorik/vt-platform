"""Business policies for the Participants bounded context.

Explicit, testable **business rules** expressed as immutable, injectable policies
(ARCH-001 §4.2, §13.4). Each policy is a frozen, slotted dataclass whose fields
*are* its configuration: nothing is read from Django settings, environment, or a
file, and there is no module-level mutable state. The composition root constructs
a policy with the knobs it wants (Dependency Inversion) and hands it to a use
case or the aggregate; the same policy under the same configuration always decides
the same way.

This is **pure domain code** (ARCH-001 §4.1, §7.2): standard library only — no
Django, no DRF, no ORM, no clock. Every method that reasons about time takes the
reference instant as an argument rather than reading a global clock, so policies
stay deterministic and trivially testable.

Policies either **return a rich decision object** — never a bare ``bool`` where the
caller needs to know *why* — or, where an operation is simply forbidden, raise a
typed :class:`~apps.participants.domain.exceptions.PolicyViolationError`.

Policies implemented here:

* :class:`AgeGroupPolicy`         — derives the age group from date of birth (PRT-002).
* :class:`GuardianshipPolicy`     — decides whether activation preconditions hold (PRT-001).
* :class:`PseudonymizationPolicy` — guards that the judging alias hides identity (JDG-006).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from enum import StrEnum

from .exceptions import AgeGroupUndefinedError, PolicyConfigurationError
from .value_objects import AgeGroup, DateOfBirth, DisplayAlias, PersonName

__all__ = [
    "ActivationAssessment",
    "ActivationBlockReason",
    "AgeGroupPolicy",
    "GuardianshipPolicy",
    "PseudonymizationPolicy",
]


# ---------------------------------------------------------------------------
# AgeGroupPolicy
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class AgeGroupPolicy:
    """Derives a participant's age group from date of birth (PRT-002).

    Age group is **always derived, never entered** (PRT-002): this policy holds the
    competition's non-overlapping :class:`AgeGroup` bands and maps a
    :class:`DateOfBirth` at a reference date onto exactly one of them. Overlapping
    or empty bands are a configuration bug rejected at construction; an age no band
    covers is a runtime :class:`AgeGroupUndefinedError` rather than a fabricated
    cohort.
    """

    bands: tuple[AgeGroup, ...]

    def __post_init__(self) -> None:
        if not self.bands:
            raise PolicyConfigurationError("AgeGroupPolicy requires at least one age band.")
        for i, band in enumerate(self.bands):
            for other in self.bands[i + 1 :]:
                if band.overlaps(other):
                    raise PolicyConfigurationError(f"AgeGroup bands {band.code!r} and {other.code!r} overlap.")

    def derive(self, date_of_birth: DateOfBirth, *, reference_date: date) -> AgeGroup:
        """Return the age band a participant falls into at ``reference_date`` (PRT-002).

        The reference date is the competition's (never "today"), keeping cohorting
        deterministic and tamper-resistant. Raises :class:`AgeGroupUndefinedError`
        when no configured band covers the derived age.
        """
        age = date_of_birth.age_in_years(reference_date)
        for band in self.bands:
            if band.contains(age):
                return band
        raise AgeGroupUndefinedError(f"No configured age band covers age {age} at {reference_date.isoformat()}.")


# ---------------------------------------------------------------------------
# GuardianshipPolicy
# ---------------------------------------------------------------------------


class ActivationBlockReason(StrEnum):
    """Why a participant may not yet be activated (PRT-001)."""

    NO_RESPONSIBLE_ADULT = "no_responsible_adult"
    CONSENT_MISSING = "consent_missing"


@dataclass(frozen=True, slots=True)
class ActivationAssessment:
    """Whether a participant may be activated, and — when not — the blocking reason.

    Richer than a ``bool`` so the caller (and ultimately the API) can distinguish
    "no verified responsible adult" from "no active consent", which drive different
    guidance to the guardian/teacher.
    """

    allowed: bool
    reason: ActivationBlockReason | None = None

    @classmethod
    def satisfied(cls) -> ActivationAssessment:
        """Activation preconditions are met."""
        return cls(allowed=True)

    @classmethod
    def blocked(cls, reason: ActivationBlockReason) -> ActivationAssessment:
        """Activation is blocked for the given ``reason``."""
        return cls(allowed=False, reason=reason)


@dataclass(frozen=True, slots=True)
class GuardianshipPolicy:
    """Decides whether a participant's activation preconditions hold (PRT-001).

    A participant may not become active without at least one **active guardian
    relationship** *or* an **authorized institution/teacher link**, **and** an
    **active, recorded consent** (PRT-001, DATA-004 TRN-PRT-002). This policy owns
    that rule; the aggregate owns the state it evaluates against and consults the
    policy in :meth:`~apps.participants.domain.entities.Participant.activate`.

    :attr:`require_consent` is ``True`` by default and models the non-negotiable
    consent gate; it exists as an explicit, injectable knob rather than a hidden
    constant.
    """

    require_consent: bool = True

    def evaluate(
        self,
        *,
        active_guardian_count: int,
        has_institutional_authority: bool,
        has_active_consent: bool,
    ) -> ActivationAssessment:
        """Assess the activation preconditions and report the first unmet one."""
        has_responsible_adult = active_guardian_count > 0 or has_institutional_authority
        if not has_responsible_adult:
            return ActivationAssessment.blocked(ActivationBlockReason.NO_RESPONSIBLE_ADULT)
        if self.require_consent and not has_active_consent:
            return ActivationAssessment.blocked(ActivationBlockReason.CONSENT_MISSING)
        return ActivationAssessment.satisfied()


# ---------------------------------------------------------------------------
# PseudonymizationPolicy
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class PseudonymizationPolicy:
    """Guards that the judging alias never leaks the participant's real name (JDG-006).

    Judges see only the :class:`DisplayAlias`, never the real :class:`PersonName`
    (PRT-006, ADR-0013). A well-formed alias could still accidentally embed a name
    part (e.g. ``"Ivan-2026"``); this policy detects that so the aggregate can
    refuse it. Matching is case-insensitive and token-based; short name parts below
    :attr:`min_significant_length` are ignored to avoid false positives on common
    two-letter fragments.
    """

    min_significant_length: int = 3

    def __post_init__(self) -> None:
        if self.min_significant_length < 1:
            raise PolicyConfigurationError("min_significant_length must be a positive integer.")

    def reveals_identity(self, alias: DisplayAlias, *, name: PersonName) -> bool:
        """Whether ``alias`` embeds any significant part of ``name`` (case-insensitive)."""
        folded = alias.value.casefold()
        parts = [name.first_name, name.last_name]
        if name.middle_name is not None:
            parts.append(name.middle_name)
        return any(len(part) >= self.min_significant_length and part.casefold() in folded for part in parts)
