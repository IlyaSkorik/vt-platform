"""Serializers for the Public Festival Catalog edge.

Output-only, read-model serializers: they render the flat
:class:`PublicFestivalView` DTOs into the platform's ``{data, meta}`` envelope
with camelCase field names (API-000 §5). They validate no input — the catalog is
a GET with no body — and are deliberately independent of the organizer control
panel's serializers.
"""

from __future__ import annotations

from rest_framework import serializers

__all__ = [
    "PublicFestivalListEnvelopeSerializer",
    "PublicFestivalSerializer",
]


class PublicCatalogMetaSerializer(serializers.Serializer):
    """Response envelope metadata (API-000 §5)."""

    requestId = serializers.CharField()


class PublicFestivalOrganizerSerializer(serializers.Serializer):
    """Organizer identity for a catalog card."""

    id = serializers.CharField()
    name = serializers.CharField()
    logo = serializers.CharField(allow_null=True)


class PublicFestivalFormatSerializer(serializers.Serializer):
    """A participation format with its normalized display mode."""

    name = serializers.CharField()
    mode = serializers.CharField(allow_null=True)


class PublicFestivalPricingSerializer(serializers.Serializer):
    """The "from X" price summary."""

    amountFrom = serializers.DecimalField(
        source="amount_from", max_digits=12, decimal_places=2, allow_null=True
    )
    currency = serializers.CharField(allow_null=True)
    multiple = serializers.BooleanField()


class PublicFestivalSerializer(serializers.Serializer):
    """One competition as rendered in the public catalog."""

    id = serializers.CharField()
    title = serializers.CharField()
    season = serializers.CharField()
    description = serializers.CharField(allow_null=True)
    status = serializers.CharField()
    organizer = PublicFestivalOrganizerSerializer()
    city = serializers.CharField(allow_null=True)
    venueName = serializers.CharField(source="venue_name", allow_null=True)
    venueAddress = serializers.CharField(source="venue_address", allow_null=True)
    coverImage = serializers.CharField(source="cover_image", allow_null=True)
    competitionStart = serializers.DateField(source="competition_start", allow_null=True)
    competitionEnd = serializers.DateField(source="competition_end", allow_null=True)
    registrationStart = serializers.DateField(source="registration_start", allow_null=True)
    registrationEnd = serializers.DateField(source="registration_end", allow_null=True)
    applicationDeadline = serializers.DateTimeField(source="application_deadline", allow_null=True)
    pricing = PublicFestivalPricingSerializer()
    formats = PublicFestivalFormatSerializer(many=True)
    modes = serializers.ListField(child=serializers.CharField())
    categories = serializers.ListField(child=serializers.CharField())
    createdAt = serializers.DateTimeField(source="created_at", allow_null=True)
    updatedAt = serializers.DateTimeField(source="updated_at", allow_null=True)


class PublicFestivalListEnvelopeSerializer(serializers.Serializer):
    """The full ``GET /public/festivals`` response envelope."""

    data = PublicFestivalSerializer(many=True)
    meta = PublicCatalogMetaSerializer()
