"""Serializers for the participant's documents edge ("Мои документы").

Output-only, read-model serializers: they render the flat
:class:`ParticipantDocumentView` DTOs into the platform's ``{data, meta}`` envelope
with camelCase field names (API-000 §5). They validate no input — the cabinet list
is a GET with no body — and are independent of the organizer workspace's
serializers.
"""

from __future__ import annotations

from rest_framework import serializers

from apps.diplomas.presentation.api.v1.diplomas.serializers import DOCUMENT_TYPES

__all__ = [
    "ParticipantDocumentSerializer",
    "ParticipantDocumentsEnvelopeSerializer",
]


class _MetaSerializer(serializers.Serializer[dict[str, object]]):
    """Response envelope metadata (API-000 §5)."""

    requestId = serializers.CharField()


class ParticipantDocumentSerializer(serializers.Serializer[dict[str, object]]):
    """One document the participant may download.

    ``number`` and ``degree`` are null for kinds that have neither — a thank-you
    letter is not numbered and ranks nothing — so the client renders the row from
    what is present rather than from the kind.
    """

    id = serializers.UUIDField()
    # Dotted source: the DTO carries the ``DocumentType`` enum, and the wire wants
    # its value.
    documentType = serializers.ChoiceField(source="document_type.value", choices=DOCUMENT_TYPES)
    number = serializers.CharField(allow_null=True)
    participantName = serializers.CharField(source="participant_name", allow_null=True)
    competitionTitle = serializers.CharField(source="competition_title", allow_null=True)
    nomination = serializers.CharField(allow_null=True)
    degree = serializers.CharField(allow_null=True)
    #: Who the document is addressed to; empty when it belongs to the performance.
    recipient = serializers.CharField(allow_blank=True)
    #: Stored ``/media/…`` reference, resolved client-side against the API origin.
    fileUrl = serializers.CharField(source="file_url")
    issuedAt = serializers.DateTimeField(source="issued_at", allow_null=True)


class ParticipantDocumentsEnvelopeSerializer(serializers.Serializer[dict[str, object]]):
    """The full ``GET /me/documents`` response envelope."""

    data = ParticipantDocumentSerializer(many=True)
    meta = _MetaSerializer()
