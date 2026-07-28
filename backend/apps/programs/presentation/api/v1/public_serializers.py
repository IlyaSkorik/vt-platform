"""Response serializers for the public program screen (anyone-facing).

A deliberately smaller shape than the organizer's: no ids, no submission references,
no version. Whatever is not in this contract cannot leak through a public link.
"""

from __future__ import annotations

from drf_spectacular.utils import inline_serializer
from rest_framework import serializers

__all__ = ["PublicProgramEnvelopeSerializer", "PublicProgramSerializer"]


class PublicProgramItemSerializer(serializers.Serializer[dict[str, object]]):
    """One line of the program as an audience, a host or an engineer reads it."""

    position = serializers.IntegerField()
    kind = serializers.CharField()
    title = serializers.CharField()
    performer = serializers.CharField(allow_null=True)
    teachers = serializers.ListField(child=serializers.CharField())
    organization = serializers.CharField(allow_null=True)
    durationSeconds = serializers.IntegerField()
    startsAt = serializers.DateTimeField(allow_null=True)
    note = serializers.CharField(allow_null=True)


class PublicProgramSerializer(serializers.Serializer[dict[str, object]]):
    """What a public link resolves to."""

    name = serializers.CharField()
    slug = serializers.CharField()
    competitionTitle = serializers.CharField(allow_null=True)
    nomination = serializers.CharField(allow_null=True)
    startsAt = serializers.DateTimeField(allow_null=True)
    totalSeconds = serializers.IntegerField()
    items = PublicProgramItemSerializer(many=True)


# The platform's ``{data, meta}`` envelope. Declared inline because ``data`` is a
# serializer attribute in DRF, and the wire contract's field name wins.
PublicProgramEnvelopeSerializer = inline_serializer(
    name="PublicProgramEnvelope",
    fields={
        "data": PublicProgramSerializer(),
        "meta": serializers.DictField(),
    },
)
