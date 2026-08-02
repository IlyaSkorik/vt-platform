"""Serializers for the composition edge — OpenAPI schema shape only.

These serializers exist purely so drf-spectacular renders an accurate OpenAPI 3.1
contract for ``GET /users/me`` (API-000 §25). The view builds the response body
directly from DTOs; nothing here validates a request.
"""

from __future__ import annotations

from drf_spectacular.utils import inline_serializer
from rest_framework import serializers

__all__ = [
    "CurrentUserResponseSerializer",
    "StaffMembershipSerializer",
    "UserResourceSerializer",
]


class UserResourceSerializer(serializers.Serializer[dict[str, object]]):
    """The Identity user resource (mirrors ``user_resource`` / API-001 §4.1)."""

    id = serializers.UUIDField()
    type = serializers.ChoiceField(choices=["user"])
    email = serializers.EmailField()
    displayName = serializers.CharField()
    status = serializers.ChoiceField(choices=["registered", "active", "suspended", "deleted"])
    emailVerified = serializers.BooleanField()
    phone = serializers.CharField(allow_null=True, required=False)
    phoneVerified = serializers.BooleanField(required=False)
    mfaEnabled = serializers.BooleanField(required=False)
    locale = serializers.CharField(required=False)
    createdAt = serializers.DateTimeField()
    updatedAt = serializers.DateTimeField()


class StaffMembershipSerializer(serializers.Serializer[dict[str, object]]):
    """The compact staff-membership read model (Organization), or null."""

    role = serializers.CharField()
    status = serializers.ChoiceField(choices=["PENDING", "ACTIVE", "REVOKED"])
    organizationId = serializers.UUIDField(required=False)


# The envelope is built with ``inline_serializer`` because its top-level ``data``
# field would otherwise shadow DRF's reserved ``Serializer.data`` attribute. It
# exists only to shape the OpenAPI contract (API-000 §7).

CurrentUserResourceSerializer = inline_serializer(
    name="CurrentUser",
    fields={
        "user": UserResourceSerializer(),
        "staffMembership": StaffMembershipSerializer(allow_null=True),
        "platformAdmin": serializers.BooleanField(),
    },
)

CurrentUserResponseSerializer = inline_serializer(
    name="CurrentUserResponse",
    fields={
        "data": CurrentUserResourceSerializer,
        "meta": inline_serializer(
            name="CurrentUserMeta",
            fields={"requestId": serializers.CharField()},
        ),
    },
)
