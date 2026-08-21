"""Value objects for the Organization bounded context.

Immutable, identity-less concepts of the Organization domain. Each is a frozen,
slotted dataclass that validates on construction, compares by value, and can
never be mutated. **Pure domain code** (ARCH-001 §4.1, §7.2): standard library
only — no Django, no ORM, no third-party validators.

Value objects implemented here:

* :class:`OrganizationId`      — UUID v7 identity of the organization.
* :class:`StaffMembershipId`   — UUID v7 identity of a staff membership.
* :class:`StaffInvitationId`   — UUID v7 identity of a staff invitation.
* :class:`StaffUserId`         — UUID v7 reference to an Identity user (opaque here).
* :class:`OrganizationName`    — non-empty, length-bounded display name.
* :class:`OrganizationSlug`    — lowercase kebab-case URL-safe identifier.
* :class:`OrganizationStatus`  — ACTIVE / SUSPENDED lifecycle enum.
* :class:`BillingModel`        — which of the two commercial terms applies.
* :class:`PerformanceFeeTier`  — one band of a fee schedule ("2–5 participants → 4.00").
* :class:`PerformanceFeeSchedule` — the ordered, gap-free set of those bands.
* :class:`StaffRole`           — the seven staff roles.
* :class:`MembershipStatus`    — PENDING / ACTIVE / REVOKED lifecycle enum.
* :class:`StaffEmail`          — normalized, validated invitee email address.
* :class:`InvitationTokenHash` — SHA-256 hex digest of an invitation secret.

The id and email value objects intentionally duplicate logic that also exists in
the Identity context: the two bounded contexts stay independent (no shared import
edge), so a little duplication is preferred over a cross-context dependency.
"""

from __future__ import annotations

import os
import re
import time
import uuid
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation
from enum import StrEnum
from itertools import pairwise
from typing import Final

from .exceptions import (
    InvalidBillingModelError,
    InvalidCommissionRateError,
    InvalidInvitationTokenHashError,
    InvalidOrganizationIdError,
    InvalidOrganizationNameError,
    InvalidOrganizationProfileError,
    InvalidOrganizationSlugError,
    InvalidPerformanceFeeScheduleError,
    InvalidPerformanceFeeTierError,
    InvalidStaffEmailError,
    InvalidStaffInvitationIdError,
    InvalidStaffMembershipIdError,
    InvalidStaffUserIdError,
)

__all__ = [
    "BillingModel",
    "CommissionRate",
    "InvitationTokenHash",
    "MembershipStatus",
    "OrganizationId",
    "OrganizationName",
    "OrganizationProfile",
    "OrganizationSlug",
    "OrganizationStatus",
    "PerformanceFeeSchedule",
    "PerformanceFeeTier",
    "StaffEmail",
    "StaffInvitationId",
    "StaffMembershipId",
    "StaffRole",
    "StaffUserId",
]

_UUID_V7_VERSION: Final = 7


def _generate_uuid7() -> uuid.UUID:
    """Generate a UUID version 7 (time-ordered) per RFC 9562 §5.7.

    Implemented directly rather than via ``uuid.uuid7`` (added only in Python
    3.14) so the domain works on any supported interpreter. The time-ordered
    layout keeps primary keys roughly monotonic, avoiding the index fragmentation
    random UUID v4 keys cause at scale.
    """
    unix_ms = time.time_ns() // 1_000_000
    rand = int.from_bytes(os.urandom(10), "big")  # 80 random bits
    rand_a = rand >> 68 & 0x0FFF  # 12 bits
    rand_b = rand & ((1 << 62) - 1)  # 62 bits
    value = (unix_ms & ((1 << 48) - 1)) << 80 | _UUID_V7_VERSION << 76 | rand_a << 64 | 0b10 << 62 | rand_b
    return uuid.UUID(int=value)


# ---------------------------------------------------------------------------
# Identifiers (UUID v7, one distinct type per aggregate/reference)
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True, repr=False)
class OrganizationId:
    """The globally unique identity of the organization (UUID v7)."""

    value: uuid.UUID

    def __post_init__(self) -> None:
        if not isinstance(self.value, uuid.UUID):
            raise InvalidOrganizationIdError(f"OrganizationId must wrap a uuid.UUID, got {type(self.value)!r}.")
        if self.value.version != _UUID_V7_VERSION:
            raise InvalidOrganizationIdError(f"OrganizationId must be a UUID v7, got version {self.value.version}.")

    @classmethod
    def generate(cls) -> OrganizationId:
        """Create a brand-new identity backed by a fresh UUID v7."""
        return cls(_generate_uuid7())

    @classmethod
    def from_uuid(cls, value: uuid.UUID) -> OrganizationId:
        """Build an ``OrganizationId`` from an existing :class:`uuid.UUID`."""
        return cls(value)

    @classmethod
    def from_string(cls, value: str) -> OrganizationId:
        """Parse a canonical UUID string, or raise :class:`InvalidOrganizationIdError`."""
        try:
            parsed = uuid.UUID(value)
        except (ValueError, AttributeError, TypeError) as exc:
            raise InvalidOrganizationIdError(f"{value!r} is not a valid UUID string.") from exc
        return cls(parsed)

    def json(self) -> str:
        """The canonical string form for JSON payloads and API responses."""
        return str(self.value)

    def __str__(self) -> str:
        return str(self.value)

    def __repr__(self) -> str:
        return f"OrganizationId({str(self.value)!r})"


@dataclass(frozen=True, slots=True, repr=False)
class StaffMembershipId:
    """The globally unique identity of a staff membership (UUID v7)."""

    value: uuid.UUID

    def __post_init__(self) -> None:
        if not isinstance(self.value, uuid.UUID):
            raise InvalidStaffMembershipIdError(f"StaffMembershipId must wrap a uuid.UUID, got {type(self.value)!r}.")
        if self.value.version != _UUID_V7_VERSION:
            raise InvalidStaffMembershipIdError(f"StaffMembershipId must be a UUID v7, got version {self.value.version}.")

    @classmethod
    def generate(cls) -> StaffMembershipId:
        """Create a brand-new identity backed by a fresh UUID v7."""
        return cls(_generate_uuid7())

    @classmethod
    def from_uuid(cls, value: uuid.UUID) -> StaffMembershipId:
        """Build a ``StaffMembershipId`` from an existing :class:`uuid.UUID`."""
        return cls(value)

    @classmethod
    def from_string(cls, value: str) -> StaffMembershipId:
        """Parse a canonical UUID string, or raise :class:`InvalidStaffMembershipIdError`."""
        try:
            parsed = uuid.UUID(value)
        except (ValueError, AttributeError, TypeError) as exc:
            raise InvalidStaffMembershipIdError(f"{value!r} is not a valid UUID string.") from exc
        return cls(parsed)

    def json(self) -> str:
        """The canonical string form for JSON payloads and API responses."""
        return str(self.value)

    def __str__(self) -> str:
        return str(self.value)

    def __repr__(self) -> str:
        return f"StaffMembershipId({str(self.value)!r})"


@dataclass(frozen=True, slots=True, repr=False)
class StaffInvitationId:
    """The globally unique identity of a staff invitation (UUID v7)."""

    value: uuid.UUID

    def __post_init__(self) -> None:
        if not isinstance(self.value, uuid.UUID):
            raise InvalidStaffInvitationIdError(f"StaffInvitationId must wrap a uuid.UUID, got {type(self.value)!r}.")
        if self.value.version != _UUID_V7_VERSION:
            raise InvalidStaffInvitationIdError(f"StaffInvitationId must be a UUID v7, got version {self.value.version}.")

    @classmethod
    def generate(cls) -> StaffInvitationId:
        """Create a brand-new identity backed by a fresh UUID v7."""
        return cls(_generate_uuid7())

    @classmethod
    def from_uuid(cls, value: uuid.UUID) -> StaffInvitationId:
        """Build a ``StaffInvitationId`` from an existing :class:`uuid.UUID`."""
        return cls(value)

    @classmethod
    def from_string(cls, value: str) -> StaffInvitationId:
        """Parse a canonical UUID string, or raise :class:`InvalidStaffInvitationIdError`."""
        try:
            parsed = uuid.UUID(value)
        except (ValueError, AttributeError, TypeError) as exc:
            raise InvalidStaffInvitationIdError(f"{value!r} is not a valid UUID string.") from exc
        return cls(parsed)

    def json(self) -> str:
        """The canonical string form for JSON payloads and API responses."""
        return str(self.value)

    def __str__(self) -> str:
        return str(self.value)

    def __repr__(self) -> str:
        return f"StaffInvitationId({str(self.value)!r})"


@dataclass(frozen=True, slots=True, repr=False)
class StaffUserId:
    """A reference to an Identity user, held only as an opaque UUID v7.

    The Organization context never resolves this to a ``User`` — it knows a person
    solely by this id. Deliberately a **separate** type from Identity's ``UserId``
    so the two contexts share no import edge (ARCH-001 §14).
    """

    value: uuid.UUID

    def __post_init__(self) -> None:
        if not isinstance(self.value, uuid.UUID):
            raise InvalidStaffUserIdError(f"StaffUserId must wrap a uuid.UUID, got {type(self.value)!r}.")
        if self.value.version != _UUID_V7_VERSION:
            raise InvalidStaffUserIdError(f"StaffUserId must be a UUID v7, got version {self.value.version}.")

    @classmethod
    def from_uuid(cls, value: uuid.UUID) -> StaffUserId:
        """Build a ``StaffUserId`` from an existing :class:`uuid.UUID`."""
        return cls(value)

    @classmethod
    def from_string(cls, value: str) -> StaffUserId:
        """Parse a canonical UUID string, or raise :class:`InvalidStaffUserIdError`."""
        try:
            parsed = uuid.UUID(value)
        except (ValueError, AttributeError, TypeError) as exc:
            raise InvalidStaffUserIdError(f"{value!r} is not a valid UUID string.") from exc
        return cls(parsed)

    def json(self) -> str:
        """The canonical string form for JSON payloads and API responses."""
        return str(self.value)

    def __str__(self) -> str:
        return str(self.value)

    def __repr__(self) -> str:
        return f"StaffUserId({str(self.value)!r})"


# ---------------------------------------------------------------------------
# Organization name & slug
# ---------------------------------------------------------------------------

_NAME_MAX: Final = 200
_SLUG_RE: Final = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
_SLUG_MAX: Final = 100


@dataclass(frozen=True, slots=True)
class OrganizationName:
    """A non-empty, length-bounded organization display name."""

    value: str

    def __post_init__(self) -> None:
        stripped = self.value.strip()
        if not stripped:
            raise InvalidOrganizationNameError("Organization name must not be empty.")
        if len(stripped) > _NAME_MAX:
            raise InvalidOrganizationNameError(f"Organization name must be at most {_NAME_MAX} characters.")
        # Normalize to the stripped form so equality ignores surrounding whitespace.
        object.__setattr__(self, "value", stripped)

    def __str__(self) -> str:
        return self.value


@dataclass(frozen=True, slots=True)
class OrganizationSlug:
    """A lowercase kebab-case, URL-safe organization identifier (e.g. ``vzlyot-talantov``)."""

    value: str

    def __post_init__(self) -> None:
        if not self.value:
            raise InvalidOrganizationSlugError("Organization slug must not be empty.")
        if len(self.value) > _SLUG_MAX:
            raise InvalidOrganizationSlugError(f"Organization slug must be at most {_SLUG_MAX} characters.")
        if not _SLUG_RE.match(self.value):
            raise InvalidOrganizationSlugError(f"Organization slug must be lowercase kebab-case: {self.value!r}.")

    def __str__(self) -> str:
        return self.value


# ---------------------------------------------------------------------------
# Commercial terms
# ---------------------------------------------------------------------------

#: The platform's cut is a percentage, so the scale is fixed at two decimals —
#: enough for "12.5%" without inviting a rate nobody can reconcile against a bank
#: statement.
_COMMISSION_SCALE: Final = Decimal("0.01")


@dataclass(frozen=True, slots=True)
class CommissionRate:
    """What share of an organization's participation fees the platform is owed.

    The commercial term under which an organization is connected: the platform
    hosts the festival, the organizer collects the entry fees, and this is the
    percentage of those fees that comes back. Zero is a legitimate rate — an
    organization can be hosted for free — and 100 is the upper bound rather than a
    sensible setting.

    Kept as an exact :class:`~decimal.Decimal` percentage (never a float): the
    number is multiplied by money and read off invoices.
    """

    percent: Decimal

    def __post_init__(self) -> None:
        if isinstance(self.percent, float):
            raise InvalidCommissionRateError("Commission rate must not be built from a float; use Decimal or str.")
        try:
            value = Decimal(self.percent).quantize(_COMMISSION_SCALE, rounding=ROUND_HALF_UP)
        except (InvalidOperation, TypeError, ValueError) as exc:
            raise InvalidCommissionRateError(f"{self.percent!r} is not a valid commission rate.") from exc
        if value < Decimal("0") or value > Decimal("100"):
            raise InvalidCommissionRateError(f"Commission rate must be between 0 and 100 percent, got {value}.")
        object.__setattr__(self, "percent", value)

    @classmethod
    def zero(cls) -> CommissionRate:
        """No commission — the organization is hosted for free."""
        return cls(Decimal("0.00"))

    @classmethod
    def of(cls, value: Decimal | int | str) -> CommissionRate:
        """Build a rate from a decimal, integer or string percentage."""
        return cls(Decimal(str(value)))

    def apply_to(self, amount: Decimal) -> Decimal:
        """The platform's share of ``amount``, rounded to the minor unit.

        Rounds half-up to two decimals, the way money is rounded everywhere else
        on the platform, so a projection adds up against the fees it came from.
        """
        return (amount * self.percent / Decimal("100")).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    def __str__(self) -> str:
        return f"{self.percent}%"


class BillingModel(StrEnum):
    """Which of the two commercial terms an organization is connected under.

    The platform charges an organization one way or the other, never both:

    * :attr:`COMMISSION_PERCENT` — a share of the participation fees the
      organization collects (:class:`CommissionRate`). The original term.
    * :attr:`PER_PERFORMANCE_FEE` — a flat price per submitted performance,
      read off a :class:`PerformanceFeeSchedule` by how many participants that
      performance has ("solo costs 2.50, a duet-to-quintet 4.00, larger 6.00"),
      regardless of what the organization charges its own participants.
    """

    COMMISSION_PERCENT = "COMMISSION_PERCENT"
    PER_PERFORMANCE_FEE = "PER_PERFORMANCE_FEE"

    @classmethod
    def of(cls, value: str) -> BillingModel:
        """Parse a wire value, raising a domain error rather than a bare ``ValueError``."""
        try:
            return cls(value)
        except ValueError as exc:
            raise InvalidBillingModelError(f"{value!r} names no known billing model.") from exc


#: Fees are money, so the scale is the minor unit — two decimals, like everything
#: else that ends up on an invoice.
_FEE_SCALE: Final = Decimal("0.01")

#: An upper bound on a single band's price. Not a commercial rule — a typo guard,
#: so a stray keystroke cannot bill an organization five figures per performance.
_FEE_MAX: Final = Decimal("100000.00")

#: The platform trades in a single currency (see the Applications/Competitions
#: ``Currency`` enums, BYN-only), so a fee carries an amount and nothing else.
FEE_CURRENCY: Final = "BYN"

#: How many bands one schedule may hold. A schedule is a pricing table a human
#: reads off; past a couple of dozen rows it is a different feature.
_MAX_FEE_TIERS: Final = 20


@dataclass(frozen=True, slots=True)
class PerformanceFeeTier:
    """One band of a fee schedule: *this many participants cost this much*.

    ``min_participants``/``max_participants`` bound the headcount of a single
    performance, inclusive on both ends; ``max_participants`` of ``None`` means the
    band is open-ended ("6 and up"). ``amount`` is what the platform is owed for a
    performance falling in the band — an exact :class:`~decimal.Decimal` in
    :data:`FEE_CURRENCY`, never a float, because it is multiplied by counts and read
    off invoices.
    """

    min_participants: int
    max_participants: int | None
    amount: Decimal

    def __post_init__(self) -> None:
        object.__setattr__(self, "min_participants", self._count("min_participants", self.min_participants))
        if self.max_participants is not None:
            object.__setattr__(self, "max_participants", self._count("max_participants", self.max_participants))
            if self.max_participants < self.min_participants:
                raise InvalidPerformanceFeeTierError(
                    f"Fee band upper bound {self.max_participants} is below its lower bound {self.min_participants}."
                )
        if isinstance(self.amount, float):
            raise InvalidPerformanceFeeTierError("Fee amount must not be built from a float; use Decimal or str.")
        try:
            amount = Decimal(self.amount).quantize(_FEE_SCALE, rounding=ROUND_HALF_UP)
        except (InvalidOperation, TypeError, ValueError) as exc:
            raise InvalidPerformanceFeeTierError(f"{self.amount!r} is not a valid fee amount.") from exc
        if amount < Decimal("0"):
            raise InvalidPerformanceFeeTierError(f"Fee amount must not be negative, got {amount}.")
        if amount > _FEE_MAX:
            raise InvalidPerformanceFeeTierError(f"Fee amount must be at most {_FEE_MAX}, got {amount}.")
        object.__setattr__(self, "amount", amount)

    @staticmethod
    def _count(field: str, value: object) -> int:
        """A participant headcount bound: a plain positive ``int`` (``bool`` refused)."""
        if isinstance(value, bool) or not isinstance(value, int):
            raise InvalidPerformanceFeeTierError(f"{field} must be an integer, got {value!r}.")
        if value < 1:
            raise InvalidPerformanceFeeTierError(f"{field} must be at least 1, got {value}.")
        return value

    @classmethod
    def of(cls, min_participants: int, max_participants: int | None, amount: Decimal | int | str) -> PerformanceFeeTier:
        """Build a band from primitives (a command payload, a JSON column, a test)."""
        return cls(
            min_participants=min_participants,
            max_participants=max_participants,
            amount=amount if isinstance(amount, Decimal) else Decimal(str(amount)),
        )

    @property
    def is_open_ended(self) -> bool:
        """Whether the band has no upper bound ("6 and up")."""
        return self.max_participants is None

    def contains(self, participant_count: int) -> bool:
        """Whether a performance with ``participant_count`` participants falls in this band."""
        if participant_count < self.min_participants:
            return False
        return self.max_participants is None or participant_count <= self.max_participants

    def range_label(self) -> str:
        """The band's headcount range as a human reads it: ``1``, ``2-5``, ``6+``."""
        if self.max_participants is None:
            return f"{self.min_participants}+"
        if self.max_participants == self.min_participants:
            return str(self.min_participants)
        return f"{self.min_participants}-{self.max_participants}"

    def __str__(self) -> str:
        return f"{self.range_label()}: {self.amount} {FEE_CURRENCY}"


@dataclass(frozen=True, slots=True)
class PerformanceFeeSchedule:
    """The full price list behind :attr:`BillingModel.PER_PERFORMANCE_FEE`.

    An ordered set of :class:`PerformanceFeeTier` bands that between them cover
    *every* headcount a performance can have: the bands are sorted, start at one
    participant, leave no gap and no overlap, and the last one is open-ended. That
    is what makes :meth:`fee_for` total — a schedule with a hole in it would bill
    some performances nothing at all, silently, which is the one failure mode that
    must not be reachable.

    Bands arrive in any order and are stored sorted, so two schedules listing the
    same bands compare equal.
    """

    tiers: tuple[PerformanceFeeTier, ...]

    def __post_init__(self) -> None:
        if isinstance(self.tiers, PerformanceFeeTier) or not isinstance(self.tiers, Iterable):
            raise InvalidPerformanceFeeScheduleError("A fee schedule is built from an iterable of bands.")
        tiers = tuple(self.tiers)
        if not tiers:
            raise InvalidPerformanceFeeScheduleError("A fee schedule must hold at least one band.")
        if len(tiers) > _MAX_FEE_TIERS:
            raise InvalidPerformanceFeeScheduleError(f"A fee schedule must hold at most {_MAX_FEE_TIERS} bands.")
        if any(not isinstance(tier, PerformanceFeeTier) for tier in tiers):
            raise InvalidPerformanceFeeScheduleError("Every band of a fee schedule must be a PerformanceFeeTier.")
        tiers = tuple(sorted(tiers, key=lambda tier: tier.min_participants))
        if tiers[0].min_participants != 1:
            raise InvalidPerformanceFeeScheduleError(f"A fee schedule must start at 1 participant, starts at {tiers[0].min_participants}.")
        for previous, current in pairwise(tiers):
            if previous.is_open_ended:
                raise InvalidPerformanceFeeScheduleError(f"The open-ended band {previous.range_label()} must be the last one.")
            expected = previous.max_participants + 1  # type: ignore[operator]  # closed by the guard above
            if current.min_participants != expected:
                problem = "an overlap" if current.min_participants < expected else "a gap"
                raise InvalidPerformanceFeeScheduleError(
                    f"Bands {previous.range_label()} and {current.range_label()} leave {problem}; "
                    f"the next band must start at {expected} participants."
                )
        if not tiers[-1].is_open_ended:
            raise InvalidPerformanceFeeScheduleError(
                f"The last band must be open-ended so every headcount is priced; {tiers[-1].range_label()} is not."
            )
        object.__setattr__(self, "tiers", tiers)

    @classmethod
    def of(cls, rows: Iterable[Sequence[object]]) -> PerformanceFeeSchedule:
        """Build a schedule from ``(min, max, amount)`` triples of primitives."""
        return cls(
            tiers=tuple(
                PerformanceFeeTier.of(
                    min_participants=row[0],  # type: ignore[arg-type]
                    max_participants=row[1],  # type: ignore[arg-type]
                    amount=row[2],  # type: ignore[arg-type]
                )
                for row in rows
            )
        )

    def fee_for(self, participant_count: int) -> Decimal:
        """What the platform is owed for one performance with this headcount.

        Total by construction: the bands cover 1..∞, so a count of at least one
        always lands in exactly one of them. A count below one is not a performance
        anybody can submit — it is priced off the first band rather than raising,
        because a reporting projection must not blow up on a malformed row.
        """
        for tier in self.tiers:
            if tier.contains(participant_count):
                return tier.amount
        return self.tiers[0].amount

    def total_for(self, participant_counts: Iterable[int]) -> Decimal:
        """What the platform is owed for a whole basket of performances."""
        return sum((self.fee_for(count) for count in participant_counts), Decimal("0.00"))

    def __str__(self) -> str:
        return "; ".join(str(tier) for tier in self.tiers)


# ---------------------------------------------------------------------------
# Contact profile
# ---------------------------------------------------------------------------

_PROFILE_SHORT_MAX: Final = 200
_PROFILE_ADDRESS_MAX: Final = 500
_PROFILE_LEGAL_MAX: Final = 5000


@dataclass(frozen=True, slots=True)
class OrganizationProfile:
    """The organization's optional public contact & legal details.

    A cohesive bundle of the "how to reach and identify us" fields the aggregate
    exposes alongside its name and slug: contact channels, social links, a logo
    reference, and legal boilerplate. Every field is optional — a freshly seeded
    organization has :meth:`empty` — and each is normalized (surrounding
    whitespace stripped; a blank string collapses to ``None``) and length-bounded
    on construction. Compares by value, so an unchanged edit is a no-op upstream.
    """

    phone: str | None = None
    email: str | None = None
    website: str | None = None
    address: str | None = None
    logo: str | None = None
    vk: str | None = None
    instagram: str | None = None
    telegram: str | None = None
    legal_information: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "phone", self._clean("phone", self.phone, _PROFILE_SHORT_MAX))
        object.__setattr__(self, "email", self._clean("email", self.email, _PROFILE_SHORT_MAX))
        object.__setattr__(self, "website", self._clean("website", self.website, _PROFILE_SHORT_MAX))
        object.__setattr__(self, "address", self._clean("address", self.address, _PROFILE_ADDRESS_MAX))
        object.__setattr__(self, "logo", self._clean("logo", self.logo, _PROFILE_SHORT_MAX))
        object.__setattr__(self, "vk", self._clean("vk", self.vk, _PROFILE_SHORT_MAX))
        object.__setattr__(self, "instagram", self._clean("instagram", self.instagram, _PROFILE_SHORT_MAX))
        object.__setattr__(self, "telegram", self._clean("telegram", self.telegram, _PROFILE_SHORT_MAX))
        object.__setattr__(self, "legal_information", self._clean("legal_information", self.legal_information, _PROFILE_LEGAL_MAX))

    @staticmethod
    def _clean(field_name: str, value: str | None, max_length: int) -> str | None:
        """Strip surrounding whitespace, collapse blanks to ``None``, and bound length."""
        if value is None:
            return None
        stripped = value.strip()
        if not stripped:
            return None
        if len(stripped) > max_length:
            raise InvalidOrganizationProfileError(f"Organization profile field {field_name!r} must be at most {max_length} characters.")
        return stripped

    @classmethod
    def empty(cls) -> OrganizationProfile:
        """The profile of an organization that has not filled in any contact details."""
        return cls()


# ---------------------------------------------------------------------------
# Enumerations
# ---------------------------------------------------------------------------


class OrganizationStatus(StrEnum):
    """The organization's operational lifecycle state.

    A :class:`~enum.StrEnum`, so each member *is* its wire value and serializes to
    a plain string. Only the singleton organization exists; suspension is a
    break-glass administrative state, not a self-service one.
    """

    ACTIVE = "ACTIVE"
    SUSPENDED = "SUSPENDED"


class StaffRole(StrEnum):
    """A staff member's role within the organization (the authorization grant).

    Authorization is decided *only* by an ACTIVE :class:`~apps.organization.domain.
    entities.StaffMembership` carrying one of these roles — never by any attribute
    of the Identity user.
    """

    OWNER = "OWNER"
    DIRECTOR = "DIRECTOR"
    FINANCE = "FINANCE"
    COMPETITION_MANAGER = "COMPETITION_MANAGER"
    CONTENT_MANAGER = "CONTENT_MANAGER"
    MODERATOR = "MODERATOR"
    SUPPORT = "SUPPORT"


class MembershipStatus(StrEnum):
    """A staff membership's lifecycle state (PENDING → ACTIVE → REVOKED)."""

    PENDING = "PENDING"
    ACTIVE = "ACTIVE"
    REVOKED = "REVOKED"


# ---------------------------------------------------------------------------
# Invitee email
# ---------------------------------------------------------------------------

_EMAIL_LOCAL_RE: Final = re.compile(
    r"^[\w!#$%&'*+/=?^_`{|}~-]+(?:\.[\w!#$%&'*+/=?^_`{|}~-]+)*$",
    re.UNICODE,
)
_EMAIL_LABEL_RE: Final = re.compile(r"^[\w-]+$", re.UNICODE)
_EMAIL_TLD_RE: Final = re.compile(r"^(?:[^\W\d_]{2,}|xn--[\w-]{2,})$", re.UNICODE)
_EMAIL_MAX_LOCAL: Final = 64
_EMAIL_MAX_DOMAIN: Final = 255
_EMAIL_MAX_LABEL: Final = 63


def _normalize_email(value: str) -> str:
    raw = value.strip()
    if not raw:
        raise InvalidStaffEmailError("Email must not be empty.")
    if raw.count("@") != 1:
        raise InvalidStaffEmailError(f"Email must contain exactly one '@': {value!r}.")
    local, domain = raw.split("@")
    if not 1 <= len(local) <= _EMAIL_MAX_LOCAL:
        raise InvalidStaffEmailError(f"Email local part must be 1-{_EMAIL_MAX_LOCAL} characters.")
    if not _EMAIL_LOCAL_RE.match(local):
        raise InvalidStaffEmailError(f"Email local part is invalid: {value!r}.")
    if not 1 <= len(domain) <= _EMAIL_MAX_DOMAIN:
        raise InvalidStaffEmailError(f"Email domain must be 1-{_EMAIL_MAX_DOMAIN} characters.")
    labels = domain.split(".")
    if len(labels) < 2:
        raise InvalidStaffEmailError(f"Email domain must have at least two labels: {value!r}.")
    for label in labels:
        if not 1 <= len(label) <= _EMAIL_MAX_LABEL:
            raise InvalidStaffEmailError(f"Email domain label length is invalid: {value!r}.")
        if label.startswith("-") or label.endswith("-"):
            raise InvalidStaffEmailError(f"Email domain label must not start/end with '-': {value!r}.")
        if not _EMAIL_LABEL_RE.match(label):
            raise InvalidStaffEmailError(f"Email domain label has invalid characters: {value!r}.")
    if not _EMAIL_TLD_RE.match(labels[-1]):
        raise InvalidStaffEmailError(f"Email top-level domain is invalid: {value!r}.")
    return f"{local.lower()}@{domain.lower()}"


@dataclass(frozen=True, slots=True)
class StaffEmail:
    """A normalized, validated email address an invitation is sent to.

    Stored lowercase so equality is by normalized value. Independent of Identity's
    ``Email`` by design (no cross-context import).
    """

    value: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "value", _normalize_email(self.value))

    def __str__(self) -> str:
        return self.value


# ---------------------------------------------------------------------------
# Invitation token hash
# ---------------------------------------------------------------------------

_SHA256_HEX_RE: Final = re.compile(r"^[0-9a-f]{64}$")


@dataclass(frozen=True, slots=True, repr=False)
class InvitationTokenHash:
    """The SHA-256 hex digest of an invitation's raw secret token.

    The raw token is emailed to the invitee and **never** stored; only this digest
    is persisted. Acceptance hashes the presented token and compares digests — the
    same philosophy as password storage. Constructing this VO does not hash
    anything: it wraps an already-computed 64-char lowercase hex digest (the
    hashing is an infrastructure concern, injected via a port).
    """

    value: str

    def __post_init__(self) -> None:
        if not _SHA256_HEX_RE.match(self.value):
            raise InvalidInvitationTokenHashError("Invitation token hash must be a 64-character lowercase hex SHA-256 digest.")

    def __str__(self) -> str:
        return self.value

    def __repr__(self) -> str:
        # Never render the full digest in logs/reprs (defence in depth).
        return f"InvitationTokenHash({self.value[:8]}…)"
