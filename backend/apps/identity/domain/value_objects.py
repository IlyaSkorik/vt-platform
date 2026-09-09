"""Value objects for the Identity & Access bounded context.

Immutable, identity-less concepts of the Identity domain (DATA-001 §8). Every
value object here is a frozen, slotted dataclass: it validates its input on
construction, is compared by value, and can never be mutated afterwards.

This is **pure domain code** (ARCH-001 §4.1, §7.2): standard library only — no
Django, no DRF, no ORM, no Pydantic, no third-party validators. Persistence,
hashing, and transport live in outer layers and depend on these types — never
the other way around. Keeping these invariants in the domain means an invalid
``Email`` or ``PhoneNumber`` simply cannot exist at runtime, so no outer layer
has to re-check them.

Value objects implemented here:

* :class:`UserId`         — UUID v7 identity of a user account (API-000 §23).
* :class:`Email`          — normalized, validated email address (DATA-001 §8).
* :class:`PhoneNumber`    — E.164 phone number for supported countries only.
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
from datetime import datetime, timedelta
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
    3.14) so the domain works on any supported interpreter (>= 3.13). The
    time-ordered layout keeps primary keys roughly monotonic, which avoids the
    index-fragmentation that random UUID v4 keys cause at database scale. Layout:
    48-bit Unix-millisecond timestamp, 4-bit version, 12 random bits, 2-bit
    variant, 62 random bits.
    """
    unix_ms = time.time_ns() // 1_000_000
    rand = int.from_bytes(os.urandom(10), "big")  # 80 random bits
    rand_a = rand >> 68 & 0x0FFF  # 12 bits
    rand_b = rand & ((1 << 62) - 1)  # 62 bits
    value = (unix_ms & ((1 << 48) - 1)) << 80 | _UUID_V7_VERSION << 76 | rand_a << 64 | 0b10 << 62 | rand_b
    return uuid.UUID(int=value)


@dataclass(frozen=True, slots=True, repr=False)
class UserId:
    """The globally unique identity of a user account (DATA-001 §9.2).

    Wraps a time-ordered **UUID v7** (API-000 §23) so identifiers are globally
    unique, non-enumerable (unlike sequential integers, they leak no counts), and
    index-friendly. Compared and hashed by value.
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

    def json(self) -> str:
        """The canonical string form for JSON payloads and API responses.

        JSON has no native UUID type, so the identity crosses the wire as its
        canonical hyphenated string (API-000 §23). This is the single method
        transport/serialization code should call, decoupling it from the internal
        :class:`uuid.UUID` representation.
        """
        return str(self.value)

    def __str__(self) -> str:
        return str(self.value)

    def __repr__(self) -> str:
        return f"UserId({str(self.value)!r})"


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
#: Leading characters of the local part kept visible by :meth:`Email.masked`.
_EMAIL_MASK_VISIBLE: Final = 3


def _normalize_email(value: str) -> str:
    raw = value.strip()
    if not raw:
        raise InvalidEmailError("Укажите адрес почты.")
    if raw.count("@") != 1:
        raise InvalidEmailError("Адрес почты должен содержать один символ «@».")
    local, domain = raw.split("@")
    if not 1 <= len(local) <= _EMAIL_MAX_LOCAL:
        raise InvalidEmailError(f"Часть адреса до «@» — от 1 до {_EMAIL_MAX_LOCAL} символов.")
    if not _EMAIL_LOCAL_RE.match(local):
        raise InvalidEmailError("Проверьте адрес почты: часть до «@» указана неверно.")
    if not 1 <= len(domain) <= _EMAIL_MAX_DOMAIN:
        raise InvalidEmailError(f"Домен почты — от 1 до {_EMAIL_MAX_DOMAIN} символов.")
    labels = domain.split(".")
    if len(labels) < 2:
        raise InvalidEmailError("Проверьте домен почты: нужен вид «example.com».")
    for label in labels:
        if not 1 <= len(label) <= _EMAIL_MAX_LABEL:
            raise InvalidEmailError("Проверьте домен почты: неверная длина части домена.")
        if label.startswith("-") or label.endswith("-"):
            raise InvalidEmailError("Проверьте домен почты: часть домена не может начинаться или заканчиваться дефисом.")
        if not _EMAIL_LABEL_RE.match(label):
            raise InvalidEmailError("Проверьте домен почты: недопустимые символы.")
    if not _EMAIL_TLD_RE.match(labels[-1]):
        raise InvalidEmailError("Проверьте домен почты: неверная доменная зона.")
    # Normalize to lowercase for a single canonical form (DATA-001 §8: one
    # verified email per active account). Unicode-aware ``str.lower``.
    return f"{local.lower()}@{domain.lower()}"


@dataclass(frozen=True, slots=True)
class Email:
    """A normalized, validated email address (DATA-001 §8).

    Stored lowercase so equality is by normalized value: ``Foo@Bar.COM`` and
    ``foo@bar.com`` are the same address, which enforces the "one verified email
    per active account" rule without a case-sensitivity loophole. Unicode local
    parts and internationalized domains are accepted.
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

    def masked(self) -> str:
        """A privacy-preserving rendering that keeps the domain but hides the local part.

        Used wherever an address is shown for recognition without full disclosure
        (support screens, audit trails, notification previews). At most the first
        few characters of the local part survive, and a one-character local part
        is hidden entirely, so the masked form never reveals the whole mailbox::

            ivan.petrov@gmail.com -> iva***@gmail.com
            alex@example.com      -> ale***@example.com
            a@gmail.com           -> *@gmail.com
        """
        local = self.local_part
        visible = min(_EMAIL_MASK_VISIBLE, len(local) - 1)
        hidden = f"{local[:visible]}***" if visible > 0 else "*"
        return f"{hidden}@{self.domain}"

    def __str__(self) -> str:
        return self.value


# ---------------------------------------------------------------------------
# PhoneNumber
# ---------------------------------------------------------------------------

_PHONE_SEPARATORS_RE: Final = re.compile(r"[\s\-().]")
_E164_RE: Final = re.compile(r"^\+[1-9]\d{6,14}$")  # '+' then 7-15 digits


@dataclass(frozen=True, slots=True)
class _PhoneFormatter:
    """How to validate and pretty-print the national number for one country.

    Formatting rules differ per country, so they live in data (a formatter per
    calling code) instead of branching logic inside :class:`PhoneNumber`. Adding a
    country is a single entry in :data:`SUPPORTED_PHONE_FORMATTERS` — the value
    object itself never changes.
    """

    #: E.164 country calling code, including the leading ``+`` (e.g. ``+375``).
    country_code: str
    #: Exact number of national digits expected after the calling code.
    national_length: int
    #: Display groups as ``(size, separator-before-group)``; the first group's
    #: separator is empty.
    groups: tuple[tuple[int, str], ...]

    def format(self, national_number: str) -> str:
        """Render ``+<code> <grouped national number>``."""
        chunks: list[str] = []
        index = 0
        for size, separator in self.groups:
            chunks.append(separator)
            chunks.append(national_number[index : index + size])
            index += size
        return f"{self.country_code} {''.join(chunks)}"


#: Extensible registry of supported countries. Belarus is the only one the
#: platform serves: its festivals are held there, its participants live there, and
#: the number is what an organizer dials on the day. Every other calling code is
#: rejected outright rather than stored in a shape nobody here will ring.
#:
#: The registry stays a registry — a second country is one entry, not a rewrite of
#: this value object — but it is deliberately not populated speculatively.
SUPPORTED_PHONE_FORMATTERS: Final[dict[str, _PhoneFormatter]] = {
    "+375": _PhoneFormatter("+375", 9, ((2, ""), (3, " "), (2, "-"), (2, "-"))),
}
# Match longer calling codes first so a prefix is never claimed by a shorter one.
_PHONE_CODES_BY_LENGTH: Final = tuple(sorted(SUPPORTED_PHONE_FORMATTERS, key=len, reverse=True))


def _match_formatter(e164: str, *, original: str) -> _PhoneFormatter:
    """Resolve the formatter for an E.164 number, rejecting unsupported countries."""
    for code in _PHONE_CODES_BY_LENGTH:
        if e164.startswith(code):
            formatter = SUPPORTED_PHONE_FORMATTERS[code]
            national = e164[len(code) :]
            if len(national) != formatter.national_length:
                raise InvalidPhoneNumberError(f"Номер с кодом {code} состоит из {formatter.national_length} цифр после кода страны.")
            return formatter
    supported = ", ".join(sorted(SUPPORTED_PHONE_FORMATTERS))
    raise InvalidPhoneNumberError(f"Такой код страны не поддерживается. Доступны: {supported}.")


def _normalize_phone(value: str) -> str:
    cleaned = _PHONE_SEPARATORS_RE.sub("", value.strip())
    if not cleaned:
        raise InvalidPhoneNumberError("Укажите номер телефона.")
    if not _E164_RE.match(cleaned):
        raise InvalidPhoneNumberError("Телефон указывается в международном формате, например +375291234567.")
    _match_formatter(cleaned, original=value)  # validate country + length
    return cleaned


@dataclass(frozen=True, slots=True)
class PhoneNumber:
    """A telephone number stored in normalized **E.164** form (DATA-001 §8).

    E.164 is the only representation kept internally, so equality and storage are
    unambiguous regardless of how a user typed the number (spaces, dashes,
    parentheses, and dots are stripped). Only calling codes the platform actually
    serves are accepted — see :data:`SUPPORTED_PHONE_FORMATTERS`. Human-facing
    grouping is produced on demand by :meth:`formatted`.
    """

    value: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "value", _normalize_phone(self.value))

    @classmethod
    def from_string(cls, value: str) -> PhoneNumber:
        """Parse and normalize a phone number to E.164."""
        return cls(value)

    @property
    def country_code(self) -> str:
        """The E.164 country calling code including the ``+`` (e.g. ``+375``)."""
        return _match_formatter(self.value, original=self.value).country_code

    @property
    def national_number(self) -> str:
        """The subscriber digits after the country calling code."""
        return self.value[len(self.country_code) :]

    def formatted(self) -> str:
        """A human-readable rendering using the country's grouping rules::

        +375291234567 -> +375 29 123-45-67
        +375171234567 -> +375 17 123-45-67
        """
        formatter = _match_formatter(self.value, original=self.value)
        return formatter.format(self.national_number)

    def __str__(self) -> str:
        return self.value


# ---------------------------------------------------------------------------
# FullName
# ---------------------------------------------------------------------------

_NAME_PART_RE: Final = re.compile(r"^[^\W\d_]+(?:[ '\-][^\W\d_]+)*$", re.UNICODE)
_NAME_MAX_LEN: Final = 100


def _clean_name_part(value: str) -> str:
    return " ".join(value.split())


def _validate_name_part(value: str, *, field: str) -> str:
    cleaned = _clean_name_part(value)
    if not cleaned:
        raise InvalidFullNameError(f"Заполните поле «{field}».")
    if len(cleaned) > _NAME_MAX_LEN:
        raise InvalidFullNameError(f"«{field}» — не длиннее {_NAME_MAX_LEN} символов.")
    if not _NAME_PART_RE.match(cleaned):
        raise InvalidFullNameError(f"«{field}»: допустимы только буквы, пробелы, дефисы и апострофы.")
    return cleaned


@dataclass(frozen=True, slots=True)
class FullName:
    """A person's name: given (first), family (last), and optional middle name.

    ``middle_name`` carries the patronymic for ``ru-RU`` (DATA-001 §8 PersonName),
    which is why several display forms exist: Russian official contexts want the
    surname first with initials, while Western contexts want ``First Last``.
    Whitespace is collapsed on construction; names may contain letters, spaces,
    hyphens and apostrophes only. Compared by normalized parts.
    """

    first_name: str
    last_name: str
    middle_name: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "first_name", _validate_name_part(self.first_name, field="first_name"))
        object.__setattr__(self, "last_name", _validate_name_part(self.last_name, field="last_name"))
        if self.middle_name is not None and _clean_name_part(self.middle_name):
            object.__setattr__(self, "middle_name", _validate_name_part(self.middle_name, field="middle_name"))
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

    def initials(self) -> str:
        """Surname plus given (and patronymic) initials, the ru-RU official short form.

        Renders ``Last F.`` (or ``Last F.M.`` when a patronymic is present), e.g.
        ``Ann Lee -> Lee A.``. This is the canonical way documents and certificates
        address a person, so it is a method producing a formatted string rather
        than raw initials.
        """
        letters = [self.first_name[0].upper()]
        if self.middle_name:
            letters.append(self.middle_name[0].upper())
        return f"{self.last_name} " + "".join(f"{letter}." for letter in letters)

    def short(self) -> str:
        """Given and family name only, dropping the patronymic: ``Иван Петров``.

        The friendly form for greetings and UI where the full patronymic would be
        needlessly formal.
        """
        return f"{self.first_name} {self.last_name}"

    def __str__(self) -> str:
        return self.full


# ---------------------------------------------------------------------------
# PasswordHash
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True, repr=False)
class PasswordHash:
    """A stored password digest together with its algorithm metadata.

    This value object is an **abstraction only**: it never stores plaintext,
    performs no hashing, and — deliberately — cannot verify a password. Computing
    and checking digests requires the concrete algorithm and belongs to a
    ``PasswordHasher`` gateway in the infrastructure layer (ARCH-001 §11.2).
    Keeping verification out of the domain prevents a hashing library from leaking
    across the layer boundary. ``PasswordHash`` merely carries the opaque,
    already-computed ``encoded_hash`` and the ``algorithm`` that produced it, which
    is exactly what :meth:`needs_migration` needs to drive transparent rehashing.
    """

    #: Algorithms recognized for migration decisions (Argon2 preferred, ARCH-001 §11.2).
    SUPPORTED_ALGORITHMS: ClassVar[frozenset[str]] = frozenset({"argon2id", "argon2i", "argon2d", "pbkdf2_sha256", "bcrypt", "scrypt"})
    #: The preferred algorithm for newly created hashes and rehash decisions.
    PREFERRED_ALGORITHM: ClassVar[str] = "argon2id"

    algorithm: str
    encoded_hash: str

    def __post_init__(self) -> None:
        if not self.algorithm or not self.algorithm.strip():
            raise InvalidPasswordHashError("Password hash algorithm must not be empty.")
        if not self.encoded_hash or not self.encoded_hash.strip():
            raise InvalidPasswordHashError("Password hash must not be empty.")
        if "$" not in self.encoded_hash:
            # A real digest is always an encoded string (PHC/Django format). The
            # absence of any structure strongly suggests plaintext leaked in, so we
            # refuse it rather than risk persisting a raw password.
            raise InvalidPasswordHashError("Password hash does not look like an encoded digest; refusing to store a possible plaintext value.")

    @classmethod
    def from_hash(cls, encoded_hash: str, algorithm: str | None = None) -> PasswordHash:
        """Wrap an already-computed digest.

        If ``algorithm`` is omitted it is derived from the encoded string, which is
        expected in PHC (``$argon2id$...``) or Django (``pbkdf2_sha256$...``) form.
        No hashing is performed here.
        """
        resolved = algorithm.strip() if algorithm and algorithm.strip() else _parse_algorithm(encoded_hash)
        return cls(algorithm=resolved, encoded_hash=encoded_hash)

    def needs_migration(self, preferred_algorithm: str | None = None) -> bool:
        """Whether this hash should be re-computed with a newer algorithm.

        Lets the platform silently upgrade legacy digests to the current preferred
        algorithm the next time a user authenticates.
        """
        target = preferred_algorithm or self.PREFERRED_ALGORITHM
        return self.algorithm != target

    def __repr__(self) -> str:
        # Never expose the digest in logs/reprs.
        return f"PasswordHash(algorithm={self.algorithm!r}, encoded_hash=<redacted>)"

    def __str__(self) -> str:
        return f"<PasswordHash {self.algorithm}>"


def _parse_algorithm(encoded_hash: str) -> str:
    """Derive the algorithm identifier from an encoded digest string."""
    if encoded_hash.startswith("$"):
        parts = encoded_hash.split("$")
        if len(parts) >= 2 and parts[1]:
            return parts[1]
    elif "$" in encoded_hash:
        head = encoded_hash.split("$", 1)[0]
        if head:
            return head
    raise InvalidPasswordHashError(
        f"Cannot determine hashing algorithm from encoded value; pass 'algorithm' explicitly (got {encoded_hash[:12]!r}…)."
    )


# ---------------------------------------------------------------------------
# ConsentVersion
# ---------------------------------------------------------------------------

_VERSION_SPLIT_RE: Final = re.compile(r"[.\-]")


def _parse_version_components(value: str) -> tuple[int, ...]:
    parts = _VERSION_SPLIT_RE.split(value)
    if not parts or any(not part.isdigit() for part in parts):
        raise InvalidConsentVersionError(f"Consent version must be dot/dash-separated integers (e.g. '2026-01' or '1.2'), got {value!r}.")
    return tuple(int(part) for part in parts)


@total_ordering
@dataclass(frozen=True, slots=True, eq=False)
class ConsentVersion:
    """An immutable, comparable identifier of a consent-text version.

    Consent is versioned and the exact text in force is preserved immutably as
    legal evidence (DATA-001 §4.1, IDN-005). Ordering exists so the platform can
    answer "has the user accepted the *current* version?" and re-prompt when a
    newer one ships. Components are compared numerically, so ``1.10`` is newer than
    ``1.9`` (not the reverse a string compare would give) and ``2026-01`` equals
    ``2026-1``.
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
        raise UnsupportedLocaleError("Язык указывается в виде «ru-RU».")
    return f"{parts[0].lower()}-{parts[1].upper()}"


@dataclass(frozen=True, slots=True)
class Locale:
    """A supported language/region tag (ARCH-001 §8.6).

    The primary locale is ``ru-RU``; ``en-US`` is also supported. Rejecting
    unsupported tags at construction guarantees any ``Locale`` in the system maps
    to translations that actually exist. The supported set is extensible via
    :attr:`SUPPORTED`, and tags are normalized to ``language-REGION`` casing so
    ``ru_ru`` and ``RU-ru`` collapse to one value.
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
            raise UnsupportedLocaleError(f"Такой язык интерфейса не поддерживается. Доступны: {supported}.")
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

    def is_russian(self) -> bool:
        """Whether this locale's language is Russian (region-independent)."""
        return self.language == "ru"

    def is_english(self) -> bool:
        """Whether this locale's language is English (region-independent)."""
        return self.language == "en"

    def __str__(self) -> str:
        return self.value


# ---------------------------------------------------------------------------
# Timezone
# ---------------------------------------------------------------------------

_UTC_ZONE_KEY: Final = "UTC"


@dataclass(frozen=True, slots=True)
class Timezone:
    """A validated IANA timezone name (e.g. ``Europe/Moscow``, ``UTC``).

    Validation goes through :class:`zoneinfo.ZoneInfo` against the system/``tzdata``
    database, so only real zones can exist. The platform stores and computes in UTC
    (API-000 §22); this value object exists so a *user-facing* preference can point
    at a real zone and render local times without the domain hard-coding offsets
    (which shift with DST and political changes). Compared by name.
    """

    #: The platform's canonical timezone (ARCH-001: timezone UTC).
    DEFAULT: ClassVar[str] = _UTC_ZONE_KEY

    value: str

    def __post_init__(self) -> None:
        raw = self.value.strip()
        if not raw:
            raise InvalidTimezoneError("Укажите часовой пояс.")
        try:
            ZoneInfo(raw)
        except (ZoneInfoNotFoundError, ValueError) as exc:
            raise InvalidTimezoneError("Такого часового пояса не существует.") from exc
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

    def is_utc(self) -> bool:
        """Whether this zone is UTC — the platform's canonical storage zone."""
        return self.zone_info.key == _UTC_ZONE_KEY

    def current_time(self) -> datetime:
        """The current wall-clock time as a timezone-aware datetime in this zone.

        Aware (never naive) so callers cannot accidentally mix it with UTC values.
        """
        return datetime.now(self.zone_info)

    def offset(self) -> timedelta:
        """The current offset from UTC, accounting for DST at this moment.

        Returned as a :class:`~datetime.timedelta` because a fixed number would be
        wrong half the year for zones that observe daylight saving time.
        """
        delta = self.current_time().utcoffset()
        if delta is None:  # pragma: no cover - a real ZoneInfo always yields an offset
            return timedelta(0)
        return delta

    def __str__(self) -> str:
        return self.value
