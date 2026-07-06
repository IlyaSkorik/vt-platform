"""Value objects for the Identity & Access bounded context.

Immutable, identity-less concepts of the Identity domain (DATA-001 §8). Every
value object here is a frozen, slotted dataclass: it validates its input on
construction, is compared by value, and can never be mutated afterwards.

This is **pure domain code** (ARCH-001 §4.1, §7.2): no Django, no DRF, no ORM,
no I/O. Persistence, hashing, and transport live in outer layers and depend on
these types — never the other way around.

Value objects implemented here:

* :class:`UserId`         — UUID v7 identity of a user account (API-000 §23).
* :class:`Email`          — normalized, validated email address (DATA-001 §8).
* :class:`PhoneNumber`    — E.164-normalized telephone number.
* :class:`FullName`       — given / family / optional middle (patronymic) name.
* :class:`PasswordHash`   — stored password digest + algorithm metadata (abstraction only).
* :class:`ConsentVersion` — comparable consent-text version (IDN-005, DATA-001 §4.1).
* :class:`Locale`         — a supported language/region tag (ARCH-001 §8.6).
* :class:`Timezone`       — a validated IANA timezone name (API-000 §22).
"""

from __future__ import annotations

import os
import re
import time
import uuid
from dataclasses import dataclass
from functools import total_ordering
from typing import ClassVar, Final
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from .exceptions import (
    InvalidConsentVersionError,
    InvalidEmailError,
    InvalidFullNameError,
    InvalidPasswordHashError,
    InvalidPhoneNumberError,
    InvalidTimezoneError,
    InvalidUserIdError,
    UnsupportedLocaleError,
)

__all__ = [
    "ConsentVersion",
    "Email",
    "FullName",
    "Locale",
    "PasswordHash",
    "PhoneNumber",
    "Timezone",
    "UserId",
]


# ---------------------------------------------------------------------------
# UserId
# ---------------------------------------------------------------------------

_UUID_V7_VERSION: Final = 7


def _generate_uuid7() -> uuid.UUID:
    """Generate a UUID version 7 (time-ordered) per RFC 9562 §5.7.

    Implemented directly rather than via ``uuid.uuid7`` (added only in Python
    3.14) so the domain works on any supported interpreter (>= 3.13). Layout:
    48-bit Unix-millisecond timestamp, 4-bit version, 12 random bits, 2-bit
    variant, 62 random bits.
    """
    unix_ms = time.time_ns() // 1_000_000
    rand = int.from_bytes(os.urandom(10), "big")  # 80 random bits
    rand_a = rand >> 68 & 0x0FFF  # 12 bits
    rand_b = rand & ((1 << 62) - 1)  # 62 bits
    value = (
        (unix_ms & ((1 << 48) - 1)) << 80
        | _UUID_V7_VERSION << 76
        | rand_a << 64
        | 0b10 << 62
        | rand_b
    )
    return uuid.UUID(int=value)


@dataclass(frozen=True, slots=True)
class UserId:
    """The globally unique identity of a user account (DATA-001 §9.2).

    Wraps a time-ordered **UUID v7** (API-000 §23): globally unique,
    non-enumerable, and index-friendly. Compared and hashed by value.
    """

    value: uuid.UUID

    def __post_init__(self) -> None:
        if not isinstance(self.value, uuid.UUID):  # defensive: wrong type
            raise InvalidUserIdError(f"UserId must wrap a uuid.UUID, got {type(self.value)!r}.")
        if self.value.version != _UUID_V7_VERSION:
            raise InvalidUserIdError(f"UserId must be a UUID v7, got version {self.value.version}.")

    @classmethod
    def generate(cls) -> UserId:
        """Create a brand-new identity backed by a fresh UUID v7."""
        return cls(_generate_uuid7())

    @classmethod
    def from_uuid(cls, value: uuid.UUID) -> UserId:
        """Build a ``UserId`` from an existing :class:`uuid.UUID`."""
        return cls(value)

    @classmethod
    def from_string(cls, value: str) -> UserId:
        """Parse a canonical UUID string into a ``UserId``.

        Raises :class:`InvalidUserIdError` if the string is not a valid UUID.
        """
        try:
            parsed = uuid.UUID(value)
        except (ValueError, AttributeError, TypeError) as exc:
            raise InvalidUserIdError(f"{value!r} is not a valid UUID string.") from exc
        return cls(parsed)

    def __str__(self) -> str:
        return str(self.value)


# ---------------------------------------------------------------------------
# Email
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
        raise InvalidEmailError("Email must not be empty.")
    if raw.count("@") != 1:
        raise InvalidEmailError(f"Email must contain exactly one '@': {value!r}.")
    local, domain = raw.split("@")
    if not 1 <= len(local) <= _EMAIL_MAX_LOCAL:
        raise InvalidEmailError(f"Email local part must be 1-{_EMAIL_MAX_LOCAL} characters.")
    if not _EMAIL_LOCAL_RE.match(local):
        raise InvalidEmailError(f"Email local part is invalid: {value!r}.")
    if not 1 <= len(domain) <= _EMAIL_MAX_DOMAIN:
        raise InvalidEmailError(f"Email domain must be 1-{_EMAIL_MAX_DOMAIN} characters.")
    labels = domain.split(".")
    if len(labels) < 2:
        raise InvalidEmailError(f"Email domain must have at least two labels: {value!r}.")
    for label in labels:
        if not 1 <= len(label) <= _EMAIL_MAX_LABEL:
            raise InvalidEmailError(f"Email domain label length is invalid: {value!r}.")
        if label.startswith("-") or label.endswith("-"):
            raise InvalidEmailError(f"Email domain label must not start/end with '-': {value!r}.")
        if not _EMAIL_LABEL_RE.match(label):
            raise InvalidEmailError(f"Email domain label has invalid characters: {value!r}.")
    if not _EMAIL_TLD_RE.match(labels[-1]):
        raise InvalidEmailError(f"Email top-level domain is invalid: {value!r}.")
    # Normalize to lowercase for a single canonical form (DATA-001 §8: one
    # verified email per active account). Unicode-aware ``str.lower``.
    return f"{local.lower()}@{domain.lower()}"


@dataclass(frozen=True, slots=True)
class Email:
    """A normalized, validated email address (DATA-001 §8).

    Stored lowercase so equality is by normalized value: ``Foo@Bar.COM`` and
    ``foo@bar.com`` are the same address. Unicode local parts and internationalized
    domains are accepted.
    """

    value: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "value", _normalize_email(self.value))

    @classmethod
    def from_string(cls, value: str) -> Email:
        """Parse and normalize an email address."""
        return cls(value)

    @property
    def local_part(self) -> str:
        """The part before the ``@``."""
        return self.value.split("@", 1)[0]

    @property
    def domain(self) -> str:
        """The part after the ``@``."""
        return self.value.split("@", 1)[1]

    def __str__(self) -> str:
        return self.value


# ---------------------------------------------------------------------------
# PhoneNumber
# ---------------------------------------------------------------------------

_PHONE_SEPARATORS_RE: Final = re.compile(r"[\s\-().]")
_E164_RE: Final = re.compile(r"^\+[1-9]\d{6,14}$")  # '+' then 7-15 digits


def _normalize_phone(value: str) -> str:
    cleaned = _PHONE_SEPARATORS_RE.sub("", value.strip())
    if not cleaned:
        raise InvalidPhoneNumberError("Phone number must not be empty.")
    if not _E164_RE.match(cleaned):
        raise InvalidPhoneNumberError(
            f"Phone number must be in E.164 format (e.g. '+79000000000'), got {value!r}."
        )
    return cleaned


@dataclass(frozen=True, slots=True)
class PhoneNumber:
    """A telephone number stored in normalized **E.164** form (DATA-001 §8).

    Input separators (spaces, dashes, parentheses, dots) are stripped; the result
    must be a leading ``+`` followed by 7-15 digits. Compared by normalized value.
    """

    value: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "value", _normalize_phone(self.value))

    @classmethod
    def from_string(cls, value: str) -> PhoneNumber:
        """Parse and normalize a phone number to E.164."""
        return cls(value)

    @property
    def country_calling_code_digits(self) -> str:
        """The digits following ``+`` (full national+country number, no separators)."""
        return self.value[1:]

    def __str__(self) -> str:
        return self.value


# ---------------------------------------------------------------------------
# FullName
# ---------------------------------------------------------------------------

_NAME_PART_RE: Final = re.compile(r"^[^\W\d_]+(?:[ ''\-][^\W\d_]+)*$", re.UNICODE)
_NAME_MAX_LEN: Final = 100


def _clean_name_part(value: str) -> str:
    return " ".join(value.split())


def _validate_name_part(value: str, *, field: str) -> str:
    cleaned = _clean_name_part(value)
    if not cleaned:
        raise InvalidFullNameError(f"{field} must not be empty.")
    if len(cleaned) > _NAME_MAX_LEN:
        raise InvalidFullNameError(f"{field} must be at most {_NAME_MAX_LEN} characters.")
    if not _NAME_PART_RE.match(cleaned):
        raise InvalidFullNameError(
            f"{field} contains invalid characters (letters, spaces, hyphens and "
            f"apostrophes only): {value!r}."
        )
    return cleaned


@dataclass(frozen=True, slots=True)
class FullName:
    """A person's name: given (first), family (last), and optional middle name.

    ``middle_name`` carries the patronymic for ``ru-RU`` (DATA-001 §8 PersonName).
    Whitespace is collapsed; names may contain letters, spaces, hyphens and
    apostrophes only. Compared by normalized parts.
    """

    first_name: str
    last_name: str
    middle_name: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(
            self, "first_name", _validate_name_part(self.first_name, field="first_name")
        )
        object.__setattr__(
            self, "last_name", _validate_name_part(self.last_name, field="last_name")
        )
        if self.middle_name is not None and _clean_name_part(self.middle_name):
            object.__setattr__(
                self, "middle_name", _validate_name_part(self.middle_name, field="middle_name")
            )
        else:
            object.__setattr__(self, "middle_name", None)

    @classmethod
    def of(cls, first_name: str, last_name: str, middle_name: str | None = None) -> FullName:
        """Rich constructor mirroring the field order."""
        return cls(first_name=first_name, last_name=last_name, middle_name=middle_name)

    @property
    def full(self) -> str:
        """Western display order: ``First [Middle] Last``."""
        parts = [self.first_name, self.middle_name, self.last_name]
        return " ".join(part for part in parts if part)

    @property
    def formal(self) -> str:
        """Eastern-Slavic display order: ``Last First [Middle]`` (ru-RU official)."""
        parts = [self.last_name, self.first_name, self.middle_name]
        return " ".join(part for part in parts if part)

    @property
    def initials(self) -> str:
        """Initials in display order, e.g. ``I. S.`` or ``I. V. S.``."""
        parts = [self.first_name, self.middle_name, self.last_name]
        return " ".join(f"{part[0].upper()}." for part in parts if part)

    def __str__(self) -> str:
        return self.full


# ---------------------------------------------------------------------------
# PasswordHash
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True, repr=False)
class PasswordHash:
    """A stored password digest together with its algorithm metadata.

    This value object is an **abstraction only** — it never stores or handles
    plaintext, and it performs no hashing. Computing and checking digests is the
    responsibility of a ``PasswordHasher`` gateway in the infrastructure layer
    (ARCH-001 §11.2). ``PasswordHash`` merely carries an opaque, already-computed
    ``encoded`` digest and the ``algorithm`` that produced it, which enables
    transparent algorithm migration (:meth:`needs_migration`).
    """

    #: Algorithms recognized for migration decisions (Argon2 preferred, ARCH-001 §11.2).
    SUPPORTED_ALGORITHMS: ClassVar[frozenset[str]] = frozenset(
        {"argon2id", "argon2i", "argon2d", "pbkdf2_sha256", "bcrypt", "scrypt"}
    )
    #: The preferred algorithm for newly created hashes and rehash decisions.
    PREFERRED_ALGORITHM: ClassVar[str] = "argon2id"

    algorithm: str
    encoded: str

    def __post_init__(self) -> None:
        if not self.algorithm or not self.algorithm.strip():
            raise InvalidPasswordHashError("Password hash algorithm must not be empty.")
        if not self.encoded or not self.encoded.strip():
            raise InvalidPasswordHashError("Password hash must not be empty.")
        if "$" not in self.encoded:
            # A real digest is always an encoded string (PHC/Django format). The
            # absence of any structure strongly suggests plaintext leaked in.
            raise InvalidPasswordHashError(
                "Password hash does not look like an encoded digest; refusing to store "
                "a possible plaintext value."
            )

    @classmethod
    def from_hash(cls, encoded: str, algorithm: str | None = None) -> PasswordHash:
        """Wrap an already-computed digest.

        If ``algorithm`` is omitted it is derived from the encoded string, which is
        expected in PHC (``$argon2id$...``) or Django (``pbkdf2_sha256$...``) form.
        No hashing is performed here.
        """
        resolved = (
            algorithm.strip() if algorithm and algorithm.strip() else _parse_algorithm(encoded)
        )
        return cls(algorithm=resolved, encoded=encoded)

    def verify(self, plaintext: str) -> bool:
        """Check a plaintext candidate against this hash.

        Not implemented in the domain: verification requires the concrete hashing
        algorithm, which lives behind a ``PasswordHasher`` gateway in the
        infrastructure layer. This method defines the contract only.
        """
        raise NotImplementedError(
            "Password verification is delegated to a PasswordHasher gateway in the "
            "infrastructure layer; the domain provides no hashing implementation."
        )

    def needs_migration(self, preferred_algorithm: str | None = None) -> bool:
        """Whether this hash should be re-computed with a newer algorithm."""
        target = preferred_algorithm or self.PREFERRED_ALGORITHM
        return self.algorithm != target

    def __repr__(self) -> str:
        # Never expose the digest in logs/reprs.
        return f"PasswordHash(algorithm={self.algorithm!r}, encoded=<redacted>)"

    def __str__(self) -> str:
        return f"<PasswordHash {self.algorithm}>"


def _parse_algorithm(encoded: str) -> str:
    """Derive the algorithm identifier from an encoded digest string."""
    if encoded.startswith("$"):
        parts = encoded.split("$")
        if len(parts) >= 2 and parts[1]:
            return parts[1]
    elif "$" in encoded:
        head = encoded.split("$", 1)[0]
        if head:
            return head
    raise InvalidPasswordHashError(
        f"Cannot determine hashing algorithm from encoded value; pass 'algorithm' explicitly "
        f"(got {encoded[:12]!r}…)."
    )


# ---------------------------------------------------------------------------
# ConsentVersion
# ---------------------------------------------------------------------------

_VERSION_SPLIT_RE: Final = re.compile(r"[.\-]")


def _parse_version_components(value: str) -> tuple[int, ...]:
    parts = _VERSION_SPLIT_RE.split(value)
    if not parts or any(not part.isdigit() for part in parts):
        raise InvalidConsentVersionError(
            f"Consent version must be dot/dash-separated integers (e.g. '2026-01' or "
            f"'1.2'), got {value!r}."
        )
    return tuple(int(part) for part in parts)


@total_ordering
@dataclass(frozen=True, slots=True, eq=False)
class ConsentVersion:
    """An immutable, comparable identifier of a consent-text version.

    Consent is versioned and the exact text in force is preserved immutably as
    evidence (DATA-001 §4.1, IDN-005). Versions are dot- or dash-separated
    integers (``2026-01``, ``1.2.0``) and support ordering so the platform can ask
    "is this the current version?". Equality and ordering are by numeric
    components, so ``2026-01`` and ``2026-1`` are equal.
    """

    value: str

    def __post_init__(self) -> None:
        stripped = self.value.strip()
        if not stripped:
            raise InvalidConsentVersionError("Consent version must not be empty.")
        _parse_version_components(stripped)  # validate eagerly
        object.__setattr__(self, "value", stripped)

    @classmethod
    def from_string(cls, value: str) -> ConsentVersion:
        """Parse a consent-text version string."""
        return cls(value)

    @property
    def _key(self) -> tuple[int, ...]:
        return _parse_version_components(self.value)

    def is_newer_than(self, other: ConsentVersion) -> bool:
        """Whether this version supersedes ``other``."""
        return self._key > other._key

    def is_older_than(self, other: ConsentVersion) -> bool:
        """Whether this version is superseded by ``other``."""
        return self._key < other._key

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, ConsentVersion):
            return NotImplemented
        return self._key == other._key

    def __lt__(self, other: object) -> bool:
        if not isinstance(other, ConsentVersion):
            return NotImplemented
        return self._key < other._key

    def __hash__(self) -> int:
        return hash(self._key)

    def __str__(self) -> str:
        return self.value


# ---------------------------------------------------------------------------
# Locale
# ---------------------------------------------------------------------------


def _normalize_locale(value: str) -> str:
    raw = value.strip().replace("_", "-")
    parts = raw.split("-")
    if len(parts) != 2 or not parts[0] or not parts[1]:
        raise UnsupportedLocaleError(
            f"Locale must be a 'language-REGION' tag (e.g. 'ru-RU'), got {value!r}."
        )
    return f"{parts[0].lower()}-{parts[1].upper()}"


@dataclass(frozen=True, slots=True)
class Locale:
    """A supported language/region tag (ARCH-001 §8.6).

    The primary locale is ``ru-RU``; ``en-US`` is also supported. The supported
    set is extensible via :attr:`SUPPORTED`. Tags are normalized to
    ``language-REGION`` casing; unsupported locales are rejected.
    """

    #: Extensible set of supported BCP-47-style tags.
    SUPPORTED: ClassVar[frozenset[str]] = frozenset({"ru-RU", "en-US"})
    #: The platform default / primary locale (ARCH-001 §8.6, §15 localization).
    DEFAULT: ClassVar[str] = "ru-RU"

    value: str

    def __post_init__(self) -> None:
        normalized = _normalize_locale(self.value)
        if normalized not in self.SUPPORTED:
            supported = ", ".join(sorted(self.SUPPORTED))
            raise UnsupportedLocaleError(
                f"Unsupported locale {self.value!r}; supported locales are: {supported}."
            )
        object.__setattr__(self, "value", normalized)

    @classmethod
    def from_string(cls, value: str) -> Locale:
        """Parse and normalize a locale tag."""
        return cls(value)

    @classmethod
    def default(cls) -> Locale:
        """The platform's primary locale (``ru-RU``)."""
        return cls(cls.DEFAULT)

    @classmethod
    def is_supported(cls, value: str) -> bool:
        """Whether ``value`` normalizes to a supported locale (never raises)."""
        try:
            return _normalize_locale(value) in cls.SUPPORTED
        except UnsupportedLocaleError:
            return False

    @property
    def language(self) -> str:
        """The lowercase language subtag (e.g. ``ru``)."""
        return self.value.split("-", 1)[0]

    @property
    def region(self) -> str:
        """The uppercase region subtag (e.g. ``RU``)."""
        return self.value.split("-", 1)[1]

    def __str__(self) -> str:
        return self.value


# ---------------------------------------------------------------------------
# Timezone
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class Timezone:
    """A validated IANA timezone name (e.g. ``Europe/Moscow``, ``UTC``).

    Validation is performed against the system/``tzdata`` zone database via
    :class:`zoneinfo.ZoneInfo`. The platform stores and computes in UTC
    (API-000 §22); this value object lets user-facing preferences reference a real
    zone. Compared by name.
    """

    #: The platform's canonical timezone (ARCH-001: timezone UTC).
    DEFAULT: ClassVar[str] = "UTC"

    value: str

    def __post_init__(self) -> None:
        raw = self.value.strip()
        if not raw:
            raise InvalidTimezoneError("Timezone must not be empty.")
        try:
            ZoneInfo(raw)
        except (ZoneInfoNotFoundError, ValueError) as exc:
            raise InvalidTimezoneError(f"{self.value!r} is not a valid IANA timezone.") from exc
        object.__setattr__(self, "value", raw)

    @classmethod
    def from_string(cls, value: str) -> Timezone:
        """Parse and validate an IANA timezone name."""
        return cls(value)

    @classmethod
    def utc(cls) -> Timezone:
        """The platform default timezone (``UTC``)."""
        return cls(cls.DEFAULT)

    @property
    def zone_info(self) -> ZoneInfo:
        """The corresponding :class:`zoneinfo.ZoneInfo` instance."""
        return ZoneInfo(self.value)

    def __str__(self) -> str:
        return self.value
