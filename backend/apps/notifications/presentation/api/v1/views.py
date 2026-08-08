"""The cabinet notification feed's REST edge.

``GET  /api/v1/me/notifications``            — the recipient's entries and unread count
``POST /api/v1/me/notifications/read``       — mark the whole feed read
``POST /api/v1/me/notifications/{id}/read``  — mark one entry read

Authenticated but **not** staff-gated: this is a person's own cabinet. Every
operation is scoped to the caller's own id, never to an id from the request, so one
account can neither read nor mark another's feed.

There is no write endpoint. Notifications are produced by whatever actually happened
— an order was placed, an organizer asked for a correction, results went up — and a
client that could post its own would be able to tell a person something the platform
never did.
"""

from __future__ import annotations

import uuid
from typing import Any, Final

from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import status as http
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.identity.infrastructure.auth import CredentialAwareJWTAuthentication
from apps.notifications.infrastructure import feed
from apps.notifications.presentation.api.v1.serializers import (
    NotificationFeedEnvelopeSerializer,
    NotificationSerializer,
    ReadReceiptEnvelopeSerializer,
)

_TAG = "Notifications"
_REQUEST_ID_HEADER: Final = "X-Request-ID"


def _recipient_uuid(raw_user_id: object) -> uuid.UUID:
    """The caller's own id as a UUID.

    ``request.user`` is typed by django-stubs as a generic Django user, whose ``id``
    is an ``int``; this platform's accounts are keyed by UUID, so the value is
    re-read rather than passed straight through. A subject that is not a UUID at all
    is folded into a deterministic one, so the lookup stays total instead of raising
    — it simply matches no notifications.
    """
    text = str(raw_user_id).strip()
    try:
        return uuid.UUID(text)
    except ValueError:
        return uuid.uuid5(uuid.NAMESPACE_URL, f"notification-recipient:{text}")


def _envelope(request: Request, data: Any, *, status: int = 200) -> Response:
    supplied = request.headers.get(_REQUEST_ID_HEADER)
    rid = str(supplied) if supplied else str(uuid.uuid4())
    return Response({"data": data, "meta": {"requestId": rid}}, status=status, headers={_REQUEST_ID_HEADER: rid})


class _AuthenticatedView(APIView):
    authentication_classes = (CredentialAwareJWTAuthentication,)
    permission_classes = (IsAuthenticated,)


class MyNotificationsView(_AuthenticatedView):
    """GET /api/v1/me/notifications — the caller's feed."""

    @extend_schema(
        tags=[_TAG],
        operation_id="listMyNotifications",
        summary="List my notifications",
        parameters=[
            OpenApiParameter(
                name="limit",
                type=int,
                required=False,
                description="How many entries to return, newest first (capped server-side).",
            )
        ],
        request=None,
        responses={http.HTTP_200_OK: NotificationFeedEnvelopeSerializer},
    )
    def get(self, request: Request) -> Response:
        recipient = _recipient_uuid(request.user.pk)
        try:
            limit = int(request.query_params.get("limit", 50))
        except (TypeError, ValueError):
            # A junk limit is the client's problem to fix, but it is no reason to
            # refuse somebody their own feed — fall back to the default page.
            limit = 50
        items = feed.recent_for(recipient, limit=limit)
        return _envelope(
            request,
            {
                "items": NotificationSerializer(items, many=True).data,
                "unreadCount": feed.unread_count_for(recipient),
            },
        )


class MyNotificationsReadView(_AuthenticatedView):
    """POST /api/v1/me/notifications/read — mark the whole feed read."""

    @extend_schema(
        tags=[_TAG],
        operation_id="markAllNotificationsRead",
        summary="Mark every notification read",
        request=None,
        responses={http.HTTP_200_OK: ReadReceiptEnvelopeSerializer},
    )
    def post(self, request: Request) -> Response:
        recipient = _recipient_uuid(request.user.pk)
        marked = feed.mark_all_read(recipient)
        return _envelope(request, {"unreadCount": feed.unread_count_for(recipient), "markedCount": marked})


class MyNotificationReadView(_AuthenticatedView):
    """POST /api/v1/me/notifications/{id}/read — mark one entry read."""

    @extend_schema(
        tags=[_TAG],
        operation_id="markNotificationRead",
        summary="Mark one notification read",
        request=None,
        responses={http.HTTP_200_OK: ReadReceiptEnvelopeSerializer},
    )
    def post(self, request: Request, notification_id: str) -> Response:
        recipient = _recipient_uuid(request.user.pk)
        try:
            target = uuid.UUID(str(notification_id))
        except ValueError:
            # Not an id at all — same answer as an id belonging to somebody else.
            # Marking something read is idempotent by nature, so "nothing changed"
            # is the honest response, and a 404 here would let a caller probe which
            # ids exist.
            return _envelope(request, {"unreadCount": feed.unread_count_for(recipient), "markedCount": 0})
        marked = feed.mark_read(recipient, target)
        return _envelope(request, {"unreadCount": feed.unread_count_for(recipient), "markedCount": 1 if marked else 0})
