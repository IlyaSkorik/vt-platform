"""Serializers for the cabinet notification feed.

Output-only read-model serializers: they render rows into the platform's
``{data, meta}`` envelope with camelCase field names (API-000 §5). Nothing here
validates input — the feed is a GET plus two bodyless POSTs.
"""

from __future__ import annotations

from rest_framework import serializers

from apps.notifications.infrastructure.models import NotificationKind

__all__ = [
    "NotificationFeedEnvelopeSerializer",
    "NotificationSerializer",
    "ReadReceiptEnvelopeSerializer",
]

_KINDS = [choice[0] for choice in NotificationKind.choices]


class _MetaSerializer(serializers.Serializer[object]):
    """Response envelope metadata (API-000 §5)."""

    requestId = serializers.CharField()


class NotificationSerializer(serializers.Serializer[object]):
    """One entry in the feed, already in the words the recipient reads."""

    id = serializers.UUIDField()
    kind = serializers.ChoiceField(choices=_KINDS)
    title = serializers.CharField()
    body = serializers.CharField(allow_blank=True)
    #: A cabinet path (``/cabinet/applications/<id>``), empty when there is nowhere
    #: to go — the client renders a plain row rather than a dead link.
    link = serializers.CharField(allow_blank=True)
    createdAt = serializers.DateTimeField(source="created_at")
    readAt = serializers.DateTimeField(source="read_at", allow_null=True)


class _FeedSerializer(serializers.Serializer[object]):
    """The feed itself: the entries plus the count the bell renders."""

    items = NotificationSerializer(many=True)
    unreadCount = serializers.IntegerField()


class NotificationFeedEnvelopeSerializer(serializers.Serializer[object]):
    """The full ``GET /me/notifications`` response envelope."""

    # `data` is the envelope's own wire key (API-000 §5), shadowing DRF's
    # `Serializer.data` property; this class only ever describes the schema.
    data = _FeedSerializer()  # type: ignore[assignment]
    meta = _MetaSerializer()


class _ReadReceiptSerializer(serializers.Serializer[object]):
    """What changed, so the client can reconcile without refetching the feed."""

    unreadCount = serializers.IntegerField()
    markedCount = serializers.IntegerField()


class ReadReceiptEnvelopeSerializer(serializers.Serializer[object]):
    """The response envelope of both "mark read" endpoints."""

    data = _ReadReceiptSerializer()  # type: ignore[assignment]
    meta = _MetaSerializer()
