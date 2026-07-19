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
from dataclasses import dataclass
from enum import StrEnum
from typing import Final

from .exceptions import (
    InvalidInvitationTokenHashError,
    InvalidOrganizationIdError,
    InvalidOrganizationNameError,
    InvalidOrganizationProfileError,
    InvalidOrganizationSlugError,
    InvalidStaffEmailError,
    InvalidStaffInvitationIdError,
    InvalidStaffMembershipIdError,
    InvalidStaffUserIdError,
)

__all__ = [
    "InvitationTokenHash",
    "MembershipStatus",
    "OrganizationId",
    "OrganizationName",
    "OrganizationProfile",
    "OrganizationSlug",
    "OrganizationStatus",
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
