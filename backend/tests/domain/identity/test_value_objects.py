"""Unit tests for the Identity domain value objects.

Framework-free, database-free (ARCH-001 §28.2). Covers, per value object:
construction & validation, normalization, equality/hashing, invalid inputs,
formatting/display helpers, and (where applicable) comparison/ordering.
"""

from __future__ import annotations

import dataclasses
import uuid
from datetime import datetime, timedelta

import pytest

from apps.identity.domain.exceptions import (
    IdentityDomainError,
    InvalidConsentVersionError,
    InvalidEmailError,
    InvalidFullNameError,
    InvalidPasswordHashError,
    InvalidPhoneNumberError,
    InvalidTimezoneError,
    InvalidUserIdError,
    UnsupportedLocaleError,
    ValueObjectValidationError,
)
from apps.identity.domain.value_objects import (
    SUPPORTED_PHONE_FORMATTERS,
    ConsentVersion,
    Email,
    FullName,
    Locale,
    PasswordHash,
    PhoneNumber,
    Timezone,
    UserId,
)

# ---------------------------------------------------------------------------
# UserId
# ---------------------------------------------------------------------------


class TestUserId:
    def test_generate_produces_uuid_v7(self) -> None:
        user_id = UserId.generate()
        assert user_id.value.version == 7

    def test_generate_is_unique(self) -> None:
        ids = {UserId.generate() for _ in range(1000)}
        assert len(ids) == 1000

    def test_generate_is_time_ordered(self) -> None:
        first = UserId.generate()
        second = UserId.generate()
        # UUID v7 orders by its 48-bit millisecond timestamp; within a single
        # millisecond the low bits are random, so compare the timestamp field only.
        ts_first = first.value.int >> 80
        ts_second = second.value.int >> 80
        assert ts_first <= ts_second

    def test_rejects_non_uuid_type(self) -> None:
        with pytest.raises(InvalidUserIdError):
            UserId("not-a-uuid")  # type: ignore[arg-type]

    def test_from_string_roundtrip(self) -> None:
        original = UserId.generate()
        assert UserId.from_string(str(original)) == original

    def test_from_uuid(self) -> None:
        raw = UserId.generate().value
        assert UserId.from_uuid(raw).value == raw

    def test_equality_and_hash(self) -> None:
        raw = UserId.generate().value
        a, b = UserId(raw), UserId(raw)
        assert a == b
        assert hash(a) == hash(b)
        assert len({a, b}) == 1

    def test_str_is_canonical_uuid(self) -> None:
        user_id = UserId.generate()
        assert str(user_id) == str(user_id.value)

    def test_json_is_canonical_string(self) -> None:
        user_id = UserId.generate()
        assert user_id.json() == str(user_id.value)
        # Round-trips through the JSON string form.
        assert UserId.from_string(user_id.json()) == user_id

    def test_repr_shows_wrapped_uuid(self) -> None:
        user_id = UserId.generate()
        assert repr(user_id) == f"UserId({str(user_id.value)!r})"
        assert "UserId(" in repr(user_id)

    def test_rejects_non_v7_uuid(self) -> None:
        with pytest.raises(InvalidUserIdError):
            UserId(uuid.uuid4())

    def test_rejects_invalid_string(self) -> None:
        for bad in ["not-a-uuid", "", "1234"]:
            with pytest.raises(InvalidUserIdError):
                UserId.from_string(bad)

    def test_is_immutable(self) -> None:
        user_id = UserId.generate()
        with pytest.raises(dataclasses.FrozenInstanceError):
            user_id.value = uuid.uuid4()  # type: ignore[misc]


# ---------------------------------------------------------------------------
# Email
# ---------------------------------------------------------------------------


class TestEmail:
    def test_normalizes_case_and_whitespace(self) -> None:
        assert Email("  Foo.Bar@Example.COM ").value == "foo.bar@example.com"

    def test_equality_by_normalized_value(self) -> None:
        assert Email("A@B.COM") == Email("a@b.com")
        assert hash(Email("A@B.COM")) == hash(Email("a@b.com"))

    def test_local_part_and_domain(self) -> None:
        email = Email("user@sub.example.com")
        assert email.local_part == "user"
        assert email.domain == "sub.example.com"

    def test_masked_keeps_domain_and_hides_local(self) -> None:
        assert Email("ivan.petrov@gmail.com").masked() == "iva***@gmail.com"
        assert Email("alex@example.com").masked() == "ale***@example.com"
        assert Email("a@gmail.com").masked() == "*@gmail.com"

    def test_masked_never_reveals_whole_local_part(self) -> None:
        # A short (but > 1 char) local part still keeps at least one char hidden.
        assert Email("ab@gmail.com").masked() == "a***@gmail.com"
        assert Email("abc@gmail.com").masked() == "ab***@gmail.com"

    def test_accepts_valid_addresses(self) -> None:
        valid = [
            "user@example.com",
            "first.last@sub.example.co",
            "user+tag@example.org",
            "user_name@example-domain.com",
            "ирина@пример.рф",  # internationalized
            "name@xn--e1afmkfd.xn--p1ai",  # punycode
        ]
        for value in valid:
            assert Email(value).value  # constructs without raising

    def test_rejects_invalid_addresses(self) -> None:
        invalid = [
            "",
            "   ",
            "plainaddress",
            "@example.com",
            "user@",
            "user@@example.com",
            "user@example",  # single label
            "user@example.c",  # tld too short
            "user@-example.com",  # label starts with hyphen
            "user@exa mple.com",  # space in domain
            "us er@example.com",  # space in local
            "user@example..com",  # empty label
            "user@.com",
        ]
        for value in invalid:
            with pytest.raises(InvalidEmailError):
                Email(value)

    def test_is_immutable(self) -> None:
        email = Email("user@example.com")
        with pytest.raises(dataclasses.FrozenInstanceError):
            email.value = "other@example.com"  # type: ignore[misc]


# ---------------------------------------------------------------------------
# PhoneNumber
# ---------------------------------------------------------------------------


class TestPhoneNumber:
    def test_normalizes_to_e164(self) -> None:
        assert PhoneNumber("+375 (29) 123-45-67").value == "+375291234567"
        assert PhoneNumber("+375.17.123.45.67").value == "+375171234567"

    def test_equality_by_normalized_value(self) -> None:
        assert PhoneNumber("+375 29 123 45 67") == PhoneNumber("+375291234567")

    def test_country_code_and_national_number(self) -> None:
        phone = PhoneNumber("+375291234567")
        assert phone.country_code == "+375"
        assert phone.national_number == "291234567"

    def test_formatting(self) -> None:
        assert PhoneNumber("+375291234567").formatted() == "+375 29 123-45-67"
        assert PhoneNumber("+375171234567").formatted() == "+375 17 123-45-67"

    def test_formatter_registry_is_the_single_source_of_truth(self) -> None:
        # Formatting is data-driven: each supported code has a formatter whose
        # declared national length matches what it produces.
        assert set(SUPPORTED_PHONE_FORMATTERS) == {"+375"}
        for code, formatter in SUPPORTED_PHONE_FORMATTERS.items():
            assert formatter.country_code == code
            assert sum(size for size, _ in formatter.groups) == formatter.national_length

    def test_str(self) -> None:
        assert str(PhoneNumber("+375291234567")) == "+375291234567"

    def test_rejects_unsupported_country(self) -> None:
        """Belarus is where the festivals are; nothing else is a number to dial."""
        for value in ["+79991234567", "+380671234567", "+14155552671", "+441632960961", "+4915112345678"]:
            with pytest.raises(InvalidPhoneNumberError):
                PhoneNumber(value)

    def test_rejects_belarusian_number_of_the_wrong_length(self) -> None:
        for value in ["+37529123456", "+3752912345678"]:
            with pytest.raises(InvalidPhoneNumberError):
                PhoneNumber(value)

    def test_rejects_invalid_numbers(self) -> None:
        invalid = [
            "",
            "   ",
            "375291234567",  # no leading '+'
            "+0900000000",  # cannot start with 0
            "+123",  # too short
            "phone",
            "+375-29-ABC-45-67",  # letters
        ]
        for value in invalid:
            with pytest.raises(InvalidPhoneNumberError):
                PhoneNumber(value)

    def test_is_immutable(self) -> None:
        phone = PhoneNumber("+375291234567")
        with pytest.raises(dataclasses.FrozenInstanceError):
            phone.value = "+375441234567"  # type: ignore[misc]


# ---------------------------------------------------------------------------
# FullName
# ---------------------------------------------------------------------------


class TestFullName:
    def test_collapses_whitespace(self) -> None:
        name = FullName("  Ирина  ", " Смирнова ", "  Ивановна ")
        assert name.first_name == "Ирина"
        assert name.last_name == "Смирнова"
        assert name.middle_name == "Ивановна"

    def test_middle_name_optional(self) -> None:
        assert FullName("Ann", "Lee").middle_name is None
        assert FullName("Ann", "Lee", "   ").middle_name is None

    def test_display_formatting(self) -> None:
        name = FullName("Иван", "Петров", "Сергеевич")
        assert name.full == "Иван Сергеевич Петров"
        assert name.formal == "Петров Иван Сергеевич"
        assert name.initials() == "Петров И.С."
        assert name.short() == "Иван Петров"
        assert str(name) == name.full

    def test_display_without_middle(self) -> None:
        name = FullName("Ann", "Lee")
        assert name.full == "Ann Lee"
        assert name.initials() == "Lee A."
        assert name.short() == "Ann Lee"

    def test_accepts_compound_names(self) -> None:
        name = FullName("Anna-Maria", "O'Brien")
        assert name.first_name == "Anna-Maria"
        assert name.last_name == "O'Brien"

    def test_equality_by_parts(self) -> None:
        assert FullName("Ann", "Lee", "Q") == FullName(" Ann ", "Lee", " Q ")
        assert FullName("Ann", "Lee") != FullName("Ann", "Lee", "Q")

    def test_rejects_invalid_names(self) -> None:
        invalid: list[tuple[str, str, str | None]] = [
            ("", "Lee", None),
            ("Ann", "", None),
            ("   ", "Lee", None),
            ("Ann2", "Lee", None),  # digit
            ("Ann", "Lee!", None),  # punctuation
            ("Ann", "Lee", "M3"),  # digit in middle
            ("A" * 101, "Lee", None),  # too long
        ]
        for first, last, middle in invalid:
            with pytest.raises(InvalidFullNameError):
                FullName(first, last, middle)

    def test_is_immutable(self) -> None:
        name = FullName("Ann", "Lee")
        with pytest.raises(dataclasses.FrozenInstanceError):
            name.first_name = "Bob"  # type: ignore[misc]


# ---------------------------------------------------------------------------
# PasswordHash
# ---------------------------------------------------------------------------

_ARGON2 = "$argon2id$v=19$m=65536,t=3,p=4$c29tZXNhbHQ$aGFzaHZhbHVl"
_PBKDF2 = "pbkdf2_sha256$390000$salt$hashvalue"


class TestPasswordHash:
    def test_parses_algorithm_from_phc(self) -> None:
        assert PasswordHash.from_hash(_ARGON2).algorithm == "argon2id"

    def test_parses_algorithm_from_django_format(self) -> None:
        assert PasswordHash.from_hash(_PBKDF2).algorithm == "pbkdf2_sha256"

    def test_explicit_algorithm_overrides(self) -> None:
        password_hash = PasswordHash.from_hash(_ARGON2, algorithm="argon2i")
        assert password_hash.algorithm == "argon2i"

    def test_encoded_hash_is_preserved(self) -> None:
        assert PasswordHash.from_hash(_ARGON2).encoded_hash == _ARGON2

    def test_cannot_derive_algorithm_without_structure(self) -> None:
        # Leading '$' but no algorithm token, and a lone trailing token.
        with pytest.raises(InvalidPasswordHashError):
            PasswordHash.from_hash("$$noalgo")

    def test_has_no_verify_method(self) -> None:
        # Verification is an infrastructure concern; the domain must not expose it.
        assert not hasattr(PasswordHash, "verify")

    def test_never_stores_plaintext(self) -> None:
        # A bare plaintext-looking value has no algorithm structure and is refused.
        with pytest.raises(InvalidPasswordHashError):
            PasswordHash.from_hash("hunter2")
        with pytest.raises(InvalidPasswordHashError):
            PasswordHash(algorithm="argon2id", encoded_hash="hunter2")

    def test_empty_values_rejected(self) -> None:
        with pytest.raises(InvalidPasswordHashError):
            PasswordHash(algorithm="", encoded_hash=_ARGON2)
        with pytest.raises(InvalidPasswordHashError):
            PasswordHash(algorithm="argon2id", encoded_hash="  ")

    def test_needs_migration(self) -> None:
        assert PasswordHash.from_hash(_PBKDF2).needs_migration() is True
        assert PasswordHash.from_hash(_ARGON2).needs_migration() is False
        assert PasswordHash.from_hash(_ARGON2).needs_migration("argon2i") is True

    def test_repr_redacts_digest(self) -> None:
        password_hash = PasswordHash.from_hash(_ARGON2)
        assert "argon2id" in repr(password_hash)
        assert "aGFzaHZhbHVl" not in repr(password_hash)
        assert password_hash.encoded_hash not in str(password_hash)

    def test_equality(self) -> None:
        assert PasswordHash.from_hash(_ARGON2) == PasswordHash.from_hash(_ARGON2)

    def test_is_immutable(self) -> None:
        password_hash = PasswordHash.from_hash(_ARGON2)
        with pytest.raises(dataclasses.FrozenInstanceError):
            password_hash.algorithm = "bcrypt"  # type: ignore[misc]


# ---------------------------------------------------------------------------
# ConsentVersion
# ---------------------------------------------------------------------------


class TestConsentVersion:
    def test_str_preserves_original(self) -> None:
        assert str(ConsentVersion("2026-01")) == "2026-01"
        assert str(ConsentVersion("  1.2.0 ")) == "1.2.0"

    def test_ordering(self) -> None:
        assert ConsentVersion("2026-01") < ConsentVersion("2026-02")
        assert ConsentVersion("2.0") > ConsentVersion("1.9")
        assert ConsentVersion("1.2") <= ConsentVersion("1.2")
        assert ConsentVersion("1.10") > ConsentVersion("1.9")  # numeric, not lexical

    def test_sorting(self) -> None:
        versions = [ConsentVersion("1.2"), ConsentVersion("1.0"), ConsentVersion("1.10")]
        assert [str(v) for v in sorted(versions)] == ["1.0", "1.2", "1.10"]

    def test_equality_by_numeric_components(self) -> None:
        assert ConsentVersion("2026-01") == ConsentVersion("2026-1")
        assert hash(ConsentVersion("2026-01")) == hash(ConsentVersion("2026-1"))

    def test_is_newer_older(self) -> None:
        assert ConsentVersion("2.0").is_newer_than(ConsentVersion("1.0"))
        assert ConsentVersion("1.0").is_older_than(ConsentVersion("2.0"))

    def test_comparison_with_other_type_is_not_supported(self) -> None:
        assert ConsentVersion("1.0") != "1.0"
        with pytest.raises(TypeError):
            _ = ConsentVersion("1.0") < 5

    def test_rejects_invalid_versions(self) -> None:
        invalid = ["", "   ", "v1.0", "1.0-beta", "2026_01", "abc", "1..0"]
        for value in invalid:
            with pytest.raises(InvalidConsentVersionError):
                ConsentVersion(value)

    def test_is_immutable(self) -> None:
        version = ConsentVersion("1.0")
        with pytest.raises(dataclasses.FrozenInstanceError):
            version.value = "2.0"  # type: ignore[misc]


# ---------------------------------------------------------------------------
# Locale
# ---------------------------------------------------------------------------


class TestLocale:
    def test_default_is_russian(self) -> None:
        assert Locale.default().value == "ru-RU"

    def test_normalizes_casing_and_separator(self) -> None:
        assert Locale("ru_ru").value == "ru-RU"
        assert Locale("EN-us").value == "en-US"

    def test_language_and_region(self) -> None:
        locale = Locale("ru-RU")
        assert locale.language == "ru"
        assert locale.region == "RU"

    def test_is_russian_and_is_english(self) -> None:
        assert Locale("ru-RU").is_russian() is True
        assert Locale("ru-RU").is_english() is False
        assert Locale("en-US").is_english() is True
        assert Locale("en-US").is_russian() is False

    def test_supported_locales(self) -> None:
        assert Locale("ru-RU").value == "ru-RU"
        assert Locale("en-US").value == "en-US"

    def test_is_supported_predicate(self) -> None:
        assert Locale.is_supported("ru_RU") is True
        assert Locale.is_supported("de-DE") is False
        assert Locale.is_supported("garbage") is False

    def test_equality(self) -> None:
        assert Locale("ru_ru") == Locale("ru-RU")

    def test_rejects_unsupported_locale(self) -> None:
        for value in ["de-DE", "fr-FR", "ru-XX"]:
            with pytest.raises(UnsupportedLocaleError):
                Locale(value)

    def test_rejects_malformed_tag(self) -> None:
        for value in ["", "ru", "ru-RU-extra", "-RU"]:
            with pytest.raises(UnsupportedLocaleError):
                Locale(value)

    def test_is_immutable(self) -> None:
        locale = Locale.default()
        with pytest.raises(dataclasses.FrozenInstanceError):
            locale.value = "en-US"  # type: ignore[misc]


# ---------------------------------------------------------------------------
# Timezone
# ---------------------------------------------------------------------------


class TestTimezone:
    def test_accepts_valid_iana_names(self) -> None:
        for value in ["UTC", "Europe/Moscow", "America/New_York", "Asia/Yekaterinburg"]:
            assert Timezone(value).value == value

    def test_utc_factory(self) -> None:
        assert Timezone.utc().value == "UTC"

    def test_zone_info_property(self) -> None:
        assert str(Timezone("Europe/Moscow").zone_info) == "Europe/Moscow"

    def test_is_utc(self) -> None:
        assert Timezone.utc().is_utc() is True
        assert Timezone("Europe/Moscow").is_utc() is False

    def test_current_time_is_timezone_aware(self) -> None:
        now = Timezone("Europe/Moscow").current_time()
        assert isinstance(now, datetime)
        assert now.tzinfo is not None
        assert now.utcoffset() is not None

    def test_offset(self) -> None:
        # UTC is always +00:00; Moscow has been a fixed UTC+3 since 2014 (no DST).
        assert Timezone.utc().offset() == timedelta(0)
        assert Timezone("Europe/Moscow").offset() == timedelta(hours=3)

    def test_strips_whitespace(self) -> None:
        assert Timezone("  UTC ").value == "UTC"

    def test_equality(self) -> None:
        assert Timezone("UTC") == Timezone.utc()

    def test_rejects_invalid_timezones(self) -> None:
        for value in ["", "   ", "Not/AZone", "Mars/Phobos", "../etc"]:
            with pytest.raises(InvalidTimezoneError):
                Timezone(value)

    def test_is_immutable(self) -> None:
        timezone = Timezone.utc()
        with pytest.raises(dataclasses.FrozenInstanceError):
            timezone.value = "Europe/Moscow"  # type: ignore[misc]


# ---------------------------------------------------------------------------
# Cross-cutting: factories and exception hierarchy
# ---------------------------------------------------------------------------


class TestFactoryMethods:
    """Cover the ``from_string`` / rich constructors and string representations."""

    def test_from_string_factories(self) -> None:
        assert Email.from_string("A@B.COM") == Email("a@b.com")
        assert PhoneNumber.from_string("+375 29 123-45-67").value == "+375291234567"
        assert ConsentVersion.from_string("1.0") == ConsentVersion("1.0")
        assert Locale.from_string("ru_ru") == Locale("ru-RU")
        assert Timezone.from_string("UTC") == Timezone.utc()

    def test_fullname_rich_constructor(self) -> None:
        assert FullName.of("Ann", "Lee", "Q") == FullName("Ann", "Lee", "Q")

    def test_string_representations(self) -> None:
        assert str(Email("a@b.com")) == "a@b.com"
        assert str(PhoneNumber("+375291234567")) == "+375291234567"
        assert str(ConsentVersion("1.0")) == "1.0"
        assert str(Locale.default()) == "ru-RU"
        assert str(Timezone.utc()) == "UTC"


class TestExceptionHierarchy:
    def test_all_validation_errors_share_a_base(self) -> None:
        with pytest.raises(ValueObjectValidationError):
            Email("nope")
        with pytest.raises(IdentityDomainError):
            PhoneNumber("nope")

    def test_validation_errors_are_value_errors(self) -> None:
        # Convenient for callers that treat construction like value parsing.
        with pytest.raises(ValueError):
            ConsentVersion("v1")
