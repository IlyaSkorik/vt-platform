"""Response serializers for the two public Results endpoints.

Their own module, and their own shapes, because a public protocol is read by anyone: these
serializers describe a **document**, not the entries behind it. There is no row id, no
submission id and no participant contact anywhere in here, and keeping the public contract
in a separate file from the organizer's is what makes adding a field to one an obviously
deliberate act rather than a leak.
"""

from __future__ import annotations

from drf_spectacular.utils import inline_serializer
from rest_framework import serializers

from apps.results.domain.value_objects import AwardKind

__all__ = ["PublicProtocolEnvelopeSerializer", "PublishedProtocolListEnvelopeSerializer"]

_AWARD_VALUES = [kind.value for kind in AwardKind]


class _PublicProtocolRowSerializer(serializers.Serializer[dict[str, object]]):
    """One row of the published table.

    ``cells`` is aligned with the view's ``columns``: a column the organizer did not publish
    produces no cell, so a hidden column cannot be read off the wire. ``award`` is carried
    for styling only - Гран-при is drawn differently - and is null on an undecided row.
    """

    cells = serializers.ListField(child=serializers.CharField(allow_blank=True))
    award = serializers.ChoiceField(choices=_AWARD_VALUES, allow_null=True)


class _PublicProtocolSerializer(serializers.Serializer[dict[str, object]]):
    """A published protocol: its heading, its columns and its rows."""

    name = serializers.CharField()
    slug = serializers.CharField()
    competitionTitle = serializers.CharField(allow_null=True)
    nomination = serializers.CharField(allow_null=True)
    #: Which publication of these results this is. Shown on the page so a corrected
    #: protocol is visibly a correction rather than a silently different document.
    revision = serializers.IntegerField()
    publishedAt = serializers.DateTimeField(allow_null=True)
    columns = inline_serializer(
        name="PublicProtocolColumn",
        fields={"key": serializers.CharField(), "label": serializers.CharField()},
        many=True,
    )
    rows = _PublicProtocolRowSerializer(many=True)


class _PublishedProtocolLinkSerializer(serializers.Serializer[dict[str, object]]):
    """One entry of a competition's "Результаты" section: a link, and what it is."""

    nomination = serializers.CharField(allow_null=True)
    name = serializers.CharField()
    slug = serializers.CharField()
    path = serializers.CharField()
    revision = serializers.IntegerField()
    publishedAt = serializers.DateTimeField(allow_null=True)


# The platform's ``{data, meta}`` envelopes. Declared inline because ``data`` is a
# serializer attribute in DRF, and the wire contract's field name wins.
PublicProtocolEnvelopeSerializer = inline_serializer(
    name="PublicProtocolEnvelope",
    fields={"data": _PublicProtocolSerializer(), "meta": serializers.DictField()},
)

PublishedProtocolListEnvelopeSerializer = inline_serializer(
    name="PublishedProtocolListEnvelope",
    fields={"data": _PublishedProtocolLinkSerializer(many=True), "meta": serializers.DictField()},
)
