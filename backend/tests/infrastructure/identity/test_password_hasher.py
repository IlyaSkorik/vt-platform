"""Tests for :class:`Argon2PasswordHasher`.

Exercise the real ``argon2-cffi`` adapter (no database): a hash is a valid
Argon2id digest, verification is correct for right/wrong passwords and never
raises on a corrupt digest, and the rehash decision reacts to both a legacy
algorithm and weaker Argon2 parameters.
"""

from __future__ import annotations

from argon2 import PasswordHasher as _Argon2Hasher

from apps.identity.application.interfaces import PasswordHasher
from apps.identity.domain.value_objects import PasswordHash
from apps.identity.infrastructure.auth import Argon2PasswordHasher

_PASSWORD = "corriente-horse-battery-staple-42"


def test_conforms_to_the_port() -> None:
    assert isinstance(Argon2PasswordHasher(), PasswordHasher)


def test_hash_produces_an_argon2id_digest() -> None:
    result = Argon2PasswordHasher().hash(_PASSWORD)

    assert isinstance(result, PasswordHash)
    assert result.algorithm == "argon2id"
    assert result.encoded_hash.startswith("$argon2id$")


def test_hash_is_salted_and_non_deterministic() -> None:
    hasher = Argon2PasswordHasher()

    assert hasher.hash(_PASSWORD).encoded_hash != hasher.hash(_PASSWORD).encoded_hash


def test_verify_accepts_the_correct_password() -> None:
    hasher = Argon2PasswordHasher()

    assert hasher.verify(_PASSWORD, hasher.hash(_PASSWORD)) is True


def test_verify_rejects_a_wrong_password() -> None:
    hasher = Argon2PasswordHasher()

    assert hasher.verify("wrong-password", hasher.hash(_PASSWORD)) is False


def test_verify_returns_false_on_a_corrupt_digest_instead_of_raising() -> None:
    corrupt = PasswordHash.from_hash("$argon2id$v=19$m=1,t=1,p=1$c2FsdA$not-a-real-digest")

    assert Argon2PasswordHasher().verify(_PASSWORD, corrupt) is False


def test_needs_rehash_is_false_for_a_current_digest() -> None:
    hasher = Argon2PasswordHasher()

    assert hasher.needs_rehash(hasher.hash(_PASSWORD)) is False


def test_needs_rehash_is_true_for_a_legacy_algorithm() -> None:
    legacy = PasswordHash.from_hash("$pbkdf2-sha256$29000$c2FsdA$digest", algorithm="pbkdf2-sha256")

    assert Argon2PasswordHasher().needs_rehash(legacy) is True


def test_needs_rehash_is_true_for_weaker_argon2_parameters() -> None:
    # A digest produced with lower cost than the current hasher's configuration.
    weak_digest = _Argon2Hasher(time_cost=1, memory_cost=8, parallelism=1).hash(_PASSWORD)
    weak = PasswordHash.from_hash(weak_digest)
    strong = Argon2PasswordHasher(_Argon2Hasher(time_cost=3, memory_cost=65536, parallelism=4))

    assert strong.needs_rehash(weak) is True
