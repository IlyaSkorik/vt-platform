"""Argon2id password hasher — the concrete :class:`PasswordHasher` adapter.

Implements the application's
:class:`~apps.identity.application.interfaces.PasswordHasher` port over
``argon2-cffi``, the platform's preferred algorithm (ARCH-001 §11.2). The domain
only ever holds an opaque
:class:`~apps.identity.domain.value_objects.PasswordHash`; this adapter is the one
place that knows the concrete algorithm, its parameters, and how to verify a
digest in constant time.

There is **no business logic here** — no password-strength checks (that is the
domain :class:`~apps.identity.domain.policies.PasswordPolicy`, enforced on the
plaintext upstream), no account lookup, no lockout. This class only hashes,
verifies, and answers the rehash question.
"""

from __future__ import annotations

from argon2 import PasswordHasher as _Argon2Hasher
from argon2 import exceptions as _argon2_exceptions

from apps.identity.domain.value_objects import PasswordHash

__all__ = ["Argon2PasswordHasher"]


class Argon2PasswordHasher:
    """Constant-time Argon2id implementation of the ``PasswordHasher`` port.

    Wraps a single configured ``argon2.PasswordHasher``; its parameters (time,
    memory, and parallelism cost) are the library defaults, which already follow
    current OWASP guidance and can be tuned by injecting a pre-built hasher.
    """

    def __init__(self, hasher: _Argon2Hasher | None = None) -> None:
        self._hasher = hasher if hasher is not None else _Argon2Hasher()

    def hash(self, password: str) -> PasswordHash:
        """Hash ``password`` into a storable Argon2id :class:`PasswordHash`."""
        encoded = self._hasher.hash(password)
        return PasswordHash.from_hash(encoded, algorithm=PasswordHash.PREFERRED_ALGORITHM)

    def verify(self, password: str, hash: PasswordHash) -> bool:
        """Whether ``password`` matches ``hash`` (constant-time; never raises).

        Argon2 signals a mismatch, or an unreadable/corrupt digest, by raising; the
        port's contract is a boolean, so those are translated to ``False``. A
        successful match returns ``True``.
        """
        try:
            return self._hasher.verify(hash.encoded_hash, password)
        except _argon2_exceptions.VerificationError:
            return False
        except _argon2_exceptions.InvalidHashError:
            return False

    def needs_rehash(self, hash: PasswordHash) -> bool:
        """Whether ``hash`` should be recomputed with current/stronger parameters.

        ``True`` when the stored digest was produced by a different algorithm than
        the platform's preferred one, or with Argon2 cost parameters weaker than
        this hasher's current configuration.
        """
        if hash.needs_migration():
            return True
        return self._hasher.check_needs_rehash(hash.encoded_hash)
