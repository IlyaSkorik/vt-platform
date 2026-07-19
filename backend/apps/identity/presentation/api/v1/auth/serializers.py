"""Serializers for the Identity authentication endpoints (API-001 §4).

Serializers here do exactly one job: **validate the request's JSON shape** — field
presence, types, and simple format (a well-formed email, a non-empty password).
They enforce no business rules: password *strength* is a domain policy
(:class:`~apps.identity.domain.policies.PasswordPolicy`), uniqueness and account
state are decided by the use cases, and credential verification is the login
handler's job. A serializer never touches the ORM, hashes nothing, and issues no
token.

Request fields use the API's camelCase wire names; the view maps validated data
onto the application command. The response serializers are declared purely so
drf-spectacular can render an accurate OpenAPI 3.1 contract (API-000 §25) — the
views build the response envelopes directly from DTOs.

Registration note: the frozen ``User`` domain models a person's name as a
structured :class:`~apps.identity.domain.value_objects.FullName` (given / family /
optional patronymic), so registration accepts ``firstName``/``lastName`` rather
than a single free-text display name; the account's display name is derived from
them (API-001 §4.1, reconciled with the ratified domain model).
"""

from __future__ import annotations

from drf_spectacular.utils import inline_serializer
from rest_framework import serializers

__all__ = [
    "PasswordResetConfirmSerializer",
    "PasswordResetRequestSerializer",
    "RegistrationRequestSerializer",
    "SessionCreateRequestSerializer",
    "TokenRefreshRequestSerializer",
]


# ---------------------------------------------------------------------------
# Request serializers (validation only)
# ---------------------------------------------------------------------------


class RegistrationRequestSerializer(serializers.Serializer[dict[str, object]]):
    """Validate a new-account registration request body (API-001 §4.1)."""

    email = serializers.EmailField()
    password = serializers.CharField(write_only=True, trim_whitespace=False, style={"input_type": "password"})
    firstName = serializers.CharField()
    lastName = serializers.CharField()
    middleName = serializers.CharField(required=False, allow_null=True)
    phone = serializers.CharField(required=False, allow_null=True)
    locale = serializers.CharField(required=False, allow_null=True)
    timezone = serializers.CharField(required=False, allow_null=True)


class SessionCreateRequestSerializer(serializers.Serializer[dict[str, object]]):
    """Validate a login (session-creation) request body (API-001 §4.4)."""

    email = serializers.CharField()
    password = serializers.CharField(write_only=True, trim_whitespace=False, style={"input_type": "password"})


class EmailVerificationRequestSerializer(serializers.Serializer[dict[str, object]]):
    """Validate a (re)send-verification request body (API-001 §4.2).

    Public: the caller names the address to send a fresh link to. The handler is
    anti-enumeration, so a well-formed but unregistered address still yields 202.
    """

    email = serializers.EmailField()


class EmailVerificationConfirmSerializer(serializers.Serializer[dict[str, object]]):
    """Validate an email-verification confirmation body (API-001 §4.2).

    The emailed token is the proof of ownership; no session is required.
    """

    token = serializers.CharField()


class PasswordResetRequestSerializer(serializers.Serializer[dict[str, object]]):
    """Validate a password-reset request body (API-001 §4.7).

    Public: the caller names the address to email a reset link to. The handler is
    anti-enumeration, so a well-formed but unregistered/unverified address still
    yields 202.
    """

    email = serializers.EmailField()


class PasswordResetConfirmSerializer(serializers.Serializer[dict[str, object]]):
    """Validate a password-reset confirmation body (API-001 §4.7).

    The emailed token is the proof of ownership; no session is required. Password
    *strength* is a domain policy enforced by the use case, not here — this only
    checks field shape.
    """

    token = serializers.CharField()
    newPassword = serializers.CharField(write_only=True, trim_whitespace=False, style={"input_type": "password"})


class TokenRefreshRequestSerializer(serializers.Serializer[dict[str, object]]):
    """Validate a token-refresh request body (API-001 §4.5).

    ``refreshToken`` is optional: web clients present the token via the httpOnly
    cookie and send an empty body, while native clients send it here.
    """

    refreshToken = serializers.CharField(required=False)


# ---------------------------------------------------------------------------
# Response serializers (OpenAPI schema only; API-000 §7, §25)
# ---------------------------------------------------------------------------


class MetaSerializer(serializers.Serializer[dict[str, object]]):
    """The ``meta`` envelope block (API-000 §7.3)."""

    requestId = serializers.CharField()


class UserResourceSerializer(serializers.Serializer[dict[str, object]]):
    """A user account resource (API-001 §4.1, §4.8)."""

    id = serializers.UUIDField()
    type = serializers.CharField(default="user")
    email = serializers.EmailField()
    displayName = serializers.CharField()
    status = serializers.CharField()
    emailVerified = serializers.BooleanField()
    phoneVerified = serializers.BooleanField()
    mfaEnabled = serializers.BooleanField()
    locale = serializers.CharField()
    createdAt = serializers.DateTimeField()
    updatedAt = serializers.DateTimeField()


class UserSummarySerializer(serializers.Serializer[dict[str, object]]):
    """The compact user summary embedded in a session resource (API-001 §4.4)."""

    id = serializers.UUIDField()
    type = serializers.CharField(default="user")
    displayName = serializers.CharField()
    emailVerified = serializers.BooleanField()


class SessionResourceSerializer(serializers.Serializer[dict[str, object]]):
    """The session resource returned on login (API-001 §4.4).

    ``refreshToken`` is present for native clients; web clients receive the same
    value as an httpOnly cookie and can ignore it.
    """

    type = serializers.CharField(default="session")
    accessToken = serializers.CharField()
    tokenType = serializers.CharField(default="Bearer")
    expiresIn = serializers.IntegerField()
    refreshToken = serializers.CharField(required=False)
    user = UserSummarySerializer()


class TokenResourceSerializer(serializers.Serializer[dict[str, object]]):
    """The refreshed-session resource (API-001 §4.5)."""

    type = serializers.CharField(default="session")
    accessToken = serializers.CharField()
    tokenType = serializers.CharField(default="Bearer")
    expiresIn = serializers.IntegerField()
    refreshToken = serializers.CharField(required=False)


# The envelope and problem serializers are built with ``inline_serializer`` because
# their top-level ``data``/``errors`` fields would otherwise shadow DRF's own
# reserved ``Serializer.data`` / ``Serializer.errors`` attributes. They exist only
# to shape the OpenAPI contract (API-000 §7, §8).

RegistrationResponseSerializer = inline_serializer(
    name="RegistrationResponse",
    fields={"data": UserResourceSerializer(), "meta": MetaSerializer()},
)

EmailVerificationResponseSerializer = inline_serializer(
    name="EmailVerificationResponse",
    fields={"data": UserResourceSerializer(), "meta": MetaSerializer()},
)

SessionResponseSerializer = inline_serializer(
    name="SessionResponse",
    fields={"data": SessionResourceSerializer(), "meta": MetaSerializer()},
)

TokenRefreshResponseSerializer = inline_serializer(
    name="TokenRefreshResponse",
    fields={"data": TokenResourceSerializer(), "meta": MetaSerializer()},
)

ProblemDetailSerializer = inline_serializer(
    name="ProblemDetail",
    fields={
        "type": serializers.URLField(),
        "title": serializers.CharField(),
        "status": serializers.IntegerField(),
        "detail": serializers.CharField(),
        "instance": serializers.CharField(),
        "requestId": serializers.CharField(),
        "code": serializers.CharField(required=False),
        "errors": serializers.ListField(child=serializers.DictField(), required=False),
    },
)
