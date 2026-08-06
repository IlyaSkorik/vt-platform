"""Serializers for the account self-service endpoints.

Shape validation only, as everywhere else in this context: presence, type and
simple format. Password *strength* is a domain policy, uniqueness is decided by
the use case, and whether the current password is right is the handler's business.

Response serializers exist so drf-spectacular renders an accurate contract; each
of these endpoints answers with the same user resource every other Identity
endpoint does, because the only thing a client needs afterwards is the account as
it now stands.
"""

from __future__ import annotations

from drf_spectacular.utils import inline_serializer
from rest_framework import serializers

from apps.identity.presentation.api.v1.auth.serializers import MetaSerializer, UserResourceSerializer

__all__ = [
    "AccountConsentRequestSerializer",
    "AccountConsentsResponseSerializer",
    "AccountEmailRequestSerializer",
    "AccountPasswordRequestSerializer",
    "AccountPhoneRequestSerializer",
    "AccountResponseSerializer",
]


class AccountPasswordRequestSerializer(serializers.Serializer[dict[str, object]]):
    """``PUT /users/me/password`` — the account holder replaces their own password."""

    currentPassword = serializers.CharField(write_only=True, trim_whitespace=False, style={"input_type": "password"})
    newPassword = serializers.CharField(write_only=True, trim_whitespace=False, style={"input_type": "password"})


class AccountEmailRequestSerializer(serializers.Serializer[dict[str, object]]):
    """``PUT /users/me/email`` — move the account to another address."""

    email = serializers.EmailField()
    currentPassword = serializers.CharField(write_only=True, trim_whitespace=False, style={"input_type": "password"})


class AccountPhoneRequestSerializer(serializers.Serializer[dict[str, object]]):
    """``PUT /users/me/phone`` — set or replace the account's phone number."""

    phone = serializers.CharField()


class AccountConsentRequestSerializer(serializers.Serializer[dict[str, object]]):
    """``POST /users/me/consents`` — record one accepted consent.

    ``version`` is the version of the *text the client displayed*, not a version the
    server picks: the record has to say what the person actually read (LEGAL-001
    §13.3). ``subjectParticipantId`` is set when an adult consents for a child, so a
    later withdrawal resolves to the right participant.
    """

    consentType = serializers.CharField(max_length=32)
    version = serializers.CharField(max_length=64)
    purpose = serializers.CharField(max_length=255, required=False, allow_null=True)
    subjectParticipantId = serializers.UUIDField(required=False, allow_null=True)


class ConsentRecordSerializer(serializers.Serializer[dict[str, object]]):
    """One entry of the consent journal, as the API renders it."""

    id = serializers.CharField()
    consentType = serializers.CharField()
    version = serializers.CharField()
    status = serializers.CharField()
    purpose = serializers.CharField(allow_null=True)
    subjectParticipantId = serializers.CharField(allow_null=True)
    grantedAt = serializers.DateTimeField(allow_null=True)
    expiresAt = serializers.DateTimeField(allow_null=True)
    withdrawnAt = serializers.DateTimeField(allow_null=True)


AccountConsentsResponseSerializer = inline_serializer(
    name="AccountConsentsResponse",
    fields={"data": ConsentRecordSerializer(many=True), "meta": MetaSerializer()},
)


AccountResponseSerializer = inline_serializer(
    name="AccountResponse",
    fields={"data": UserResourceSerializer(), "meta": MetaSerializer()},
)
