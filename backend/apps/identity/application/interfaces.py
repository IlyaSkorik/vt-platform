"""Application ports (contracts) required by Identity & Access use cases.

The **outbound dependencies** of the Identity application layer, expressed as
pure :class:`typing.Protocol` seams (ARCH-001 §7.3, Dependency Inversion). A use
case (command/query handler) depends only on these abstractions; the concrete
adapters — a Django ORM repository, an Argon2 hasher, an SMTP/SMS provider, a
Celery/outbox publisher — live in ``infrastructure/`` and are injected at
composition time. The dependency arrow therefore points *inward*: infrastructure
depends on this module, never the reverse.

This module is **framework-free** (ARCH-001 §4.1, §7.2): standard library only —
no Django, no DRF, no ORM, no message bus, no IO. It contains **interfaces
only**; there are deliberately no implementations here. Every method is fully
typed and no signature uses ``Any``.

Design choices worth stating once, since they shape every port below:

* **Protocols, not ABCs.** Structural typing lets an adapter satisfy a port
  without importing or inheriting from it, which keeps the domain/application
  core free of dependency edges pointing outward. The protocols are
  :func:`~typing.runtime_checkable` purely so tests can assert conformance with
  ``isinstance``; production code relies on static structural checks.
* **Lookups return ``User | None``.** The three repository getters report absence
  as ``None`` rather than raising, so the *use case* decides whether a missing
  user is an error (e.g. login vs. registration-uniqueness check). The companion
  ``exists_*`` methods answer presence questions without materializing an
  aggregate. No repository-level "not found" exception is invented here.
* **Time and identity are injected.** :class:`Clock` and :class:`UuidGenerator`
  exist so use cases never call ``datetime.now`` or ``uuid`` directly, keeping
  them deterministic and testable — the same rule the domain already follows by
  taking ``now`` as an argument.

Ports defined here:

* :class:`UserRepository`     — persistence & retrieval of the ``User`` aggregate.
* :class:`PasswordHasher`     — hash / verify / rehash-decision for credentials.
* :class:`EmailGateway`       — transactional email delivery.
* :class:`SmsGateway`         — one-time SMS code delivery.
* :class:`NotificationGateway`— in-app / push user notifications.
* :class:`Clock`              — the current instant, injected not read globally.
* :class:`UuidGenerator`      — fresh UUID v7 identifiers, injected not read globally.
* :class:`EventPublisher`     — dispatch of recorded domain events to the outside.
"""

from __future__ import annotations

import uuid
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime
from typing import Protocol, runtime_checkable

from apps.identity.application.dto import TokenPairDto
from apps.identity.domain.entities import User
from apps.identity.domain.events import DomainEvent
from apps.identity.domain.value_objects import (
    Email,
    FullName,
    Locale,
    PasswordHash,
    PhoneNumber,
    UserId,
)

__all__ = [
    "Clock",
    "EmailGateway",
    "EventPublisher",
    "NotificationGateway",
    "PasswordHasher",
    "SmsGateway",
    "TokenService",
    "UserRepository",
    "UuidGenerator",
    "VerificationToken",
    "VerificationTokenService",
]


# ---------------------------------------------------------------------------
# Repository ports
# ---------------------------------------------------------------------------


@runtime_checkable
class UserRepository(Protocol):
    """Port: persistence and retrieval of the :class:`User` aggregate root.

    **Why it exists.** Use cases must load and store users without knowing *how*
    they are stored. This port is the seam that inverts that dependency: the
    application layer speaks only ``User`` and value objects, never SQL, an ORM
    model, or a session.

    **Who implements it.** An adapter in ``apps.identity.infrastructure`` backed
    by the Django ORM (mapping rows to/from the aggregate via
    :meth:`User.rehydrate`). Tests substitute an in-memory fake.

    **Who consumes it.** Every Identity command/query handler that reads or
    mutates a user (registration, login, email/phone changes, lockout, deletion).

    Contract notes: the ``get_*`` lookups return ``None`` when no user matches, so
    the caller decides whether absence is an error. ``save`` performs an upsert
    keyed by :attr:`User.id` and is responsible for enforcing the aggregate's
    optimistic-concurrency :attr:`User.version`. Uniqueness of email/phone is a
    persistence-level invariant the adapter guards; ``exists_*`` lets a use case
    check it up front without loading the aggregate.
    """

    def get(self, user_id: UserId) -> User | None:
        """Return the user with ``user_id``, or ``None`` if none exists."""
        ...

    def get_by_email(self, email: Email) -> User | None:
        """Return the user whose current email is ``email``, or ``None``."""
        ...

    def get_by_phone(self, phone: PhoneNumber) -> User | None:
        """Return the user whose current phone is ``phone``, or ``None``."""
        ...

    def exists(self, user_id: UserId) -> bool:
        """Whether a user with ``user_id`` is stored."""
        ...

    def exists_by_email(self, email: Email) -> bool:
        """Whether some user currently uses ``email`` (uniqueness pre-check)."""
        ...

    def exists_by_phone(self, phone: PhoneNumber) -> bool:
        """Whether some user currently uses ``phone`` (uniqueness pre-check)."""
        ...

    def save(self, user: User) -> None:
        """Persist ``user`` (insert or update), honouring its optimistic version."""
        ...

    def delete(self, user: User) -> None:
        """Remove ``user`` from storage.

        This is a *storage* deletion; the reversible business lifecycle transition
        is :meth:`User.soft_delete`. Most flows soft-delete and ``save``; a hard
        ``delete`` is reserved for legally mandated erasure.
        """
        ...


# ---------------------------------------------------------------------------
# Gateway ports
# ---------------------------------------------------------------------------


@runtime_checkable
class PasswordHasher(Protocol):
    """Port: compute and verify password digests outside the domain.

    **Why it exists.** The domain models a credential only as an opaque
    :class:`PasswordHash` and deliberately cannot hash or verify (ARCH-001 §11.2);
    doing so needs a concrete algorithm and secrets handling that must not leak
    across the layer boundary. This port is where that capability lives.

    **Who implements it.** An infrastructure adapter over ``argon2-cffi`` (the
    platform's preferred ``argon2id``), or Django's password hashers. Tests use a
    trivial deterministic fake.

    **Who consumes it.** Registration and password-change use cases (to produce a
    :class:`PasswordHash` for :meth:`User.change_password`) and the login use case
    (to :meth:`verify` a submitted password and opportunistically rehash).
    """

    def hash(self, password: str) -> PasswordHash:
        """Hash a plaintext ``password`` into a storable :class:`PasswordHash`."""
        ...

    def verify(self, password: str, hash: PasswordHash) -> bool:
        """Whether ``password`` matches the stored ``hash`` (constant-time)."""
        ...

    def needs_rehash(self, hash: PasswordHash) -> bool:
        """Whether ``hash`` should be recomputed with stronger/current parameters.

        Lets the login flow transparently upgrade a legacy digest after a
        successful :meth:`verify`.
        """
        ...


@runtime_checkable
class EmailGateway(Protocol):
    """Port: deliver transactional emails to a user's address.

    **Why it exists.** Sending email is IO against an external provider; use cases
    must trigger it without binding to SMTP, an API client, or a template engine.

    **Who implements it.** An infrastructure adapter over the platform's email
    provider (SMTP / a transactional-email API), rendering localized templates.
    Tests capture calls with a recording fake.

    **Who consumes it.** The verification use case (on ``UserRegistered`` /
    ``EmailChanged``) and the password-reset use case (on
    ``PasswordResetRequested``).

    Contract note: the gateway receives an already-built ``verification_url`` /
    ``reset_url`` and never sees or generates the underlying token — secrets are
    minted by a dedicated use case, not the delivery adapter.
    """

    def send_verification_email(
        self, *, email: Email, full_name: FullName, verification_url: str, locale: Locale
    ) -> None:
        """Send an email-ownership verification link to ``email``."""
        ...

    def send_password_reset(
        self,
        *,
        email: Email,
        full_name: FullName,
        reset_url: str,
        expires_at: datetime,
        locale: Locale,
    ) -> None:
        """Send a password-reset link to ``email``, valid until ``expires_at``."""
        ...


@runtime_checkable
class SmsGateway(Protocol):
    """Port: deliver one-time verification codes by SMS.

    **Why it exists.** Phone verification needs to push a short code to a carrier;
    that IO must stay behind an interface so use cases remain provider-agnostic.

    **Who implements it.** An infrastructure adapter over the platform's SMS
    provider. Tests use a recording fake.

    **Who consumes it.** The phone-verification use case, which generates a code
    under :class:`~apps.identity.domain.policies.PhoneVerificationPolicy` and asks
    this gateway to deliver it (paired later with :meth:`User.verify_phone`).
    """

    def send_verification_code(self, *, phone: PhoneNumber, code: str) -> None:
        """Send the one-time verification ``code`` to ``phone``."""
        ...


@runtime_checkable
class NotificationGateway(Protocol):
    """Port: deliver in-app / push notifications to a user.

    **Why it exists.** Security- and lifecycle-relevant facts (a new sign-in, a
    password change, a lockout) should reach the user through the platform's own
    notification channel, distinct from email/SMS. Use cases need to fire such a
    notification without knowing the transport.

    **Who implements it.** An infrastructure adapter over the platform's
    notification service (push provider and/or in-app store). Tests use a
    recording fake.

    **Who consumes it.** Security-notification handlers reacting to Identity
    events (e.g. ``PasswordChanged``, ``UserLocked``).
    """

    def notify(self, *, recipient: UserId, subject: str, body: str, locale: Locale) -> None:
        """Send a notification titled ``subject`` with ``body`` to ``recipient``."""
        ...


# ---------------------------------------------------------------------------
# Ambient-dependency ports (time & identity, injected not read globally)
# ---------------------------------------------------------------------------


@runtime_checkable
class Clock(Protocol):
    """Port: the source of the current instant, injected rather than read globally.

    **Why it exists.** The domain already takes ``now`` as an argument to stay
    deterministic; this port is how the application layer *obtains* that ``now``
    without calling :func:`datetime.now` directly, so use cases are testable with
    a frozen clock and never accidentally read wall-clock time.

    **Who implements it.** A trivial system-clock adapter in infrastructure. Tests
    inject a fixed/controllable fake clock.

    **Who consumes it.** Every use case that stamps a mutation or evaluates a
    time-based policy (verification expiry, lock duration, session lifetime).

    Contract note: both methods return **timezone-aware** datetimes. :meth:`utcnow`
    is the canonical UTC instant the platform stores (API-000 §22); :meth:`now`
    may carry a configured display zone.
    """

    def now(self) -> datetime:
        """The current instant as a timezone-aware datetime (possibly non-UTC zone)."""
        ...

    def utcnow(self) -> datetime:
        """The current instant as a timezone-aware **UTC** datetime."""
        ...


@runtime_checkable
class UuidGenerator(Protocol):
    """Port: source of fresh UUID v7 identifiers, injected rather than read globally.

    **Why it exists.** Identifiers for new aggregates, events, and sessions must be
    time-ordered UUID v7 (API-000 §23) yet generated deterministically under test.
    Injecting this port lets a use case obtain an id without calling into ``uuid``
    or the value-object factory directly.

    **Who implements it.** An infrastructure adapter wrapping the platform's UUID v7
    generation. Tests inject a sequence-driven fake for reproducible ids.

    **Who consumes it.** Use cases that must mint an id before handing it to a
    domain factory (e.g. :meth:`UserId.from_uuid` at registration, session ids).

    Contract note: the returned value must be a UUID **version 7**; downstream
    value objects (:class:`UserId`) reject any other version.
    """

    def new(self) -> uuid.UUID:
        """Return a brand-new time-ordered UUID version 7."""
        ...


# ---------------------------------------------------------------------------
# Event publication port
# ---------------------------------------------------------------------------


@runtime_checkable
class EventPublisher(Protocol):
    """Port: dispatch recorded domain events to the world outside the aggregate.

    **Why it exists.** Domain methods only *return* events; they never publish
    them (ARCH-001 §4.8). Some component must carry those facts to consumers —
    other bounded contexts, projections, side-effect handlers — and use cases must
    do so without binding to a concrete bus.

    **Who implements it.** An infrastructure adapter writing to the transactional
    outbox / message bus (Celery/Kafka) so publication commits atomically with the
    aggregate ``save``. Tests use a recording fake.

    **Who consumes it.** Every command handler, after persisting the aggregate:
    it forwards the events the domain method returned.

    Contract note: takes a :class:`~collections.abc.Sequence` so a handler can pass
    the event list a domain method returned as-is; an empty sequence is a valid
    no-op.
    """

    def publish(self, events: Sequence[DomainEvent]) -> None:
        """Publish ``events`` in order to the platform's event transport."""
        ...


# ---------------------------------------------------------------------------
# Email-verification token port
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class VerificationToken:
    """The decoded contents of an email-verification token.

    A framework-free carrier the confirm-email use case reads after the token
    service verifies a token's integrity: *which* account it is for
    (:attr:`user_id`) and *when* the link was issued (:attr:`issued_at`), the
    instant the domain checks against
    :class:`~apps.identity.domain.policies.EmailVerificationPolicy` to decide
    whether the link has expired. It carries no secret — the signed token is the
    secret; this is only its verified payload.
    """

    user_id: UserId
    issued_at: datetime


@runtime_checkable
class VerificationTokenService(Protocol):
    """Port: mint and verify the signed token behind an email-verification link.

    **Why it exists.** Turning "this account should verify its email" into an
    opaque, tamper-evident link — and later proving a presented link is authentic —
    needs a concrete signing key and codec. That is infrastructure detail: a use
    case must trigger it (on ``UserRegistered`` / a resend) and check it (on
    confirmation) without binding to Django's signer, a JWT, or any URL shape.

    **Who implements it.** An infrastructure adapter over the platform's signing
    facility (Django's ``TimestampSigner`` / ``dumps``), which also knows the web
    client's base URL and so can render the full user-facing link. Tests use a
    reversible in-memory fake.

    **Who consumes it.** The verification-email side-effect handler (to
    :meth:`issue_link` on registration/resend) and the confirm-email use case (to
    :meth:`verify` the token a user returns).

    Contract notes: :meth:`issue_link` returns a complete, user-clickable URL and
    stamps the token with ``issued_at`` so the *domain* — not this adapter — owns
    the expiry rule. :meth:`verify` raises
    :class:`~apps.identity.application.exceptions.InvalidVerificationTokenError`
    for any token whose signature does not check out (malformed, tampered), never a
    sentinel; a *well-formed but stale* link is not rejected here — its ``issued_at``
    travels back out so the domain policy can decide expiry (a distinct ``410``).
    """

    def issue_link(self, *, user_id: UserId, issued_at: datetime) -> str:
        """Mint a signed token for ``user_id`` stamped ``issued_at`` and return its link."""
        ...

    def verify(self, token: str) -> VerificationToken:
        """Verify ``token``'s integrity and return its payload, or raise on failure."""
        ...


# ---------------------------------------------------------------------------
# Session-token port
# ---------------------------------------------------------------------------


@runtime_checkable
class TokenService(Protocol):
    """Port: issue, rotate, and revoke the session's JWT pair.

    **Why it exists.** Minting and validating JWTs needs a concrete signing key,
    algorithm, and a rotation/blacklist mechanism — infrastructure detail that must
    not leak into a use case. The domain models a credential only as an opaque
    :class:`~apps.identity.domain.value_objects.PasswordHash` and knows nothing of
    sessions or tokens; this port is where the token lifecycle lives, keeping the
    login/refresh/logout use cases framework-free (ARCH-001 §11, API-000 §17).

    **Who implements it.** An infrastructure adapter over ``djangorestframework-
    simplejwt`` (issuing the access/refresh pair, rotating on refresh, blacklisting
    on rotation/logout). Tests substitute a deterministic in-memory fake.

    **Who consumes it.** The login edge (after
    :class:`~apps.identity.application.handlers.user_handlers.AuthenticateUserHandler`
    has verified credentials) calls :meth:`issue`; the refresh use case calls
    :meth:`rotate`; the logout use case calls :meth:`revoke`.

    Contract notes: ``subject`` is the account's opaque id string
    (:meth:`~apps.identity.domain.value_objects.UserId.json`). :meth:`rotate` and
    :meth:`revoke` MUST raise
    :class:`~apps.identity.application.exceptions.InvalidTokenError` for any
    unusable token (malformed, expired, wrong type, already rotated) rather than
    returning a sentinel — the caller never inspects token internals. Rotation
    invalidates the presented refresh token so it cannot be replayed.
    """

    def issue(self, *, subject: str) -> TokenPairDto:
        """Issue a fresh access + refresh pair for the account ``subject``."""
        ...

    def rotate(self, *, refresh_token: str) -> TokenPairDto:
        """Validate ``refresh_token``, invalidate it, and issue a new pair."""
        ...

    def revoke(self, *, refresh_token: str) -> None:
        """Blacklist ``refresh_token`` so the session can no longer be renewed."""
        ...
