"""Serializers for the public diploma verification edge.

Output-only, read-model serializers: they render the flat
:class:`DiplomaVerificationView` DTO into the platform's ``{data, meta}`` envelope
with camelCase field names (API-000 §5). They validate no input — verification is
a GET with no body — and are deliberately independent of the organizer diploma
workspace's serializers.
"""

from __future__ import annotations

from rest_framework import serializers

__all__ = [
    "DiplomaVerificationEnvelopeSerializer",
    "DiplomaVerificationSerializer",
]


class DiplomaVerificationMetaSerializer(serializers.Serializer[object]):
    """Response envelope metadata (API-000 §5)."""

    requestId = serializers.CharField()


class DiplomaVerificationSerializer(serializers.Serializer[object]):
    """One verified diploma as shown on its public authenticity page.

    Every printed fact is nullable because a snapshot may legitimately lack it
    (no organization, no teacher, an undated competition). Two nulls carry a
    specific meaning the client renders on:

    * ``degree`` — the jury result is not published yet.
    * ``officialPdfUrl`` — the official PDF does not exist yet, so no download.
    """

    number = serializers.CharField()
    participantName = serializers.CharField(source="participant_name", allow_null=True)
    memberName = serializers.CharField(source="member_name", allow_null=True)
    competitionTitle = serializers.CharField(source="competition_title", allow_null=True)
    competitionDate = serializers.CharField(source="competition_date", allow_null=True)
    nomination = serializers.CharField(allow_null=True)
    performance = serializers.CharField(allow_null=True)
    teacher = serializers.CharField(allow_null=True)
    organization = serializers.CharField(allow_null=True)
    degree = serializers.CharField(allow_null=True)
    issueDate = serializers.DateTimeField(source="issue_date", allow_null=True)
    officialPdfUrl = serializers.CharField(source="official_pdf_url", allow_null=True)
    verified = serializers.BooleanField()


class DiplomaVerificationEnvelopeSerializer(serializers.Serializer[object]):
    """The full ``GET /public/diplomas/verify/{token}`` response envelope."""

    # `data` is the envelope's own wire key (API-000 §5), shadowing DRF's
    # `Serializer.data` property; this class exists only to describe the schema.
    data = DiplomaVerificationSerializer()  # type: ignore[assignment]
    meta = DiplomaVerificationMetaSerializer()
