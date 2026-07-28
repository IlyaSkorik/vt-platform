"""Response serializers for the public programme screen (anyone-facing).

A table and nothing else: the columns the organizer published, and one row of cells per
item. Deliberately smaller than the organizer's shape - no ids, no submission references,
no version - and cells exist only for published columns, so a column the organizer left
out cannot be recovered from the response.
"""

from __future__ import annotations

from drf_spectacular.utils import inline_serializer
from rest_framework import serializers

__all__ = ["PublicProgramEnvelopeSerializer", "PublicProgramSerializer"]


#: One published column: its stable key and the header it is printed under. Declared
#: inline because ``label`` is a serializer attribute in DRF, and the wire contract's
#: field name wins.
PublicProgramColumnSerializer = inline_serializer(
    name="PublicProgramColumn",
    fields={
        "key": serializers.CharField(),
        "label": serializers.CharField(),
        "custom": serializers.BooleanField(),
    },
    many=True,
)


class PublicProgramRowSerializer(serializers.Serializer[dict[str, object]]):
    """One row of the table. ``cells`` is aligned with ``columns``.

    ``progress`` is what makes a screen live; ``id`` is present only on the host's edition,
    where it is the handle their controls act on.
    """

    kind = serializers.CharField()
    cells = serializers.ListField(child=serializers.CharField(allow_blank=True))
    progress = serializers.CharField()
    id = serializers.UUIDField(allow_null=True)


class PublicProgramSerializer(serializers.Serializer[dict[str, object]]):
    """What a public link resolves to."""

    name = serializers.CharField()
    slug = serializers.CharField()
    competitionTitle = serializers.CharField(allow_null=True)
    nomination = serializers.CharField(allow_null=True)
    startsAt = serializers.DateTimeField(allow_null=True)
    totalSeconds = serializers.IntegerField()
    #: Whether the reader of this link may drive the running order (the host's edition).
    controlsRunningOrder = serializers.BooleanField()
    columns = PublicProgramColumnSerializer
    rows = PublicProgramRowSerializer(many=True)


# The platform's ``{data, meta}`` envelope. Declared inline because ``data`` is a
# serializer attribute in DRF, and the wire contract's field name wins.
PublicProgramEnvelopeSerializer = inline_serializer(
    name="PublicProgramEnvelope",
    fields={
        "data": PublicProgramSerializer(),
        "meta": serializers.DictField(),
    },
)
