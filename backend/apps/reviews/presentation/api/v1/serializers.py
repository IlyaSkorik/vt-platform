"""Request/response serializers for the Reviews REST API v1.

Request serializers validate shape only — lengths and types the domain would
otherwise have to re-derive from a raw payload. Every *rule* (a note with no
words, a page that has stopped collecting, a consent that is missing) stays in the
domain, so it holds no matter which edge asks.

Response serializers exist so drf-spectacular renders an accurate OpenAPI 3.1
contract (API-000 §25); the views build their bodies from DTOs.
"""

from __future__ import annotations

from drf_spectacular.utils import inline_serializer
from rest_framework import serializers

from apps.reviews.domain.value_objects import (
    AUTHOR_NAME_MAX,
    PAGE_INTRO_MAX,
    PAGE_TITLE_MAX,
    REVIEW_TEXT_MAX,
)

__all__ = [
    "PublicPageSerializer",
    "ReviewPageSerializer",
    "ReviewProblemDetailSerializer",
    "ReviewSerializer",
    "SubmitReviewRequestSerializer",
    "UpdateReviewPageRequestSerializer",
]


#: RFC 9457 problem document (API-000 §8).
#:
#: Assembled inline rather than declared as a ``Serializer`` subclass, exactly as
#: Voting does it: a problem document has a field called ``instance``, and that name
#: already belongs to ``BaseSerializer`` — declaring it as a class attribute is a
#: type error before it is anything else.
ReviewProblemDetailSerializer = inline_serializer(
    name="ReviewProblemDetail",
    fields={
        "type": serializers.URLField(),
        "title": serializers.CharField(),
        "status": serializers.IntegerField(),
        "detail": serializers.CharField(),
        "instance": serializers.CharField(),
        "requestId": serializers.CharField(),
    },
)


class UpdateReviewPageRequestSerializer(serializers.Serializer[dict[str, object]]):
    """Rewording the page, or switching collection on and off.

    Every field is optional and an omitted one means "leave as it was": the
    wording form and the open/close switch are two controls on one screen, and
    neither should have to resend the other's value to avoid clobbering it.
    """

    title = serializers.CharField(max_length=PAGE_TITLE_MAX, required=False)
    intro = serializers.CharField(max_length=PAGE_INTRO_MAX, required=False, allow_blank=True)
    accepting = serializers.BooleanField(required=False)


class SubmitReviewRequestSerializer(serializers.Serializer[dict[str, object]]):
    """A note arriving from the public page.

    ``consentAccepted`` is a required ``true`` rather than an optional flag: the
    one thing this endpoint must not accept is a note whose author never agreed to
    it being kept, and a field that could be left out would make that a matter of
    what the form happened to send. ``consentType`` and ``consentVersion`` say
    *what* they agreed to and *which wording* of it — the same pair the rest of
    the platform records a consent as, and what makes the record answerable later
    (LEGAL-001 §13.3).

    Photographs do not appear here: they arrive as files on the same multipart
    request and are validated by ``files.store_photo``, which is the only place
    that knows what the storage will take.
    """

    text = serializers.CharField(max_length=REVIEW_TEXT_MAX, trim_whitespace=False)
    consentType = serializers.CharField(max_length=64)
    consentVersion = serializers.CharField(max_length=64)
    consentAccepted = serializers.BooleanField()
    # Signing is optional, and blank is how a phone form sends "left empty".
    authorName = serializers.CharField(max_length=AUTHOR_NAME_MAX, required=False, allow_blank=True)
    competitionId = serializers.UUIDField(required=False, allow_null=True)


class ReviewPageSerializer(serializers.Serializer[dict[str, object]]):
    """The page as its owner administers it."""

    id = serializers.CharField()
    slug = serializers.CharField()
    title = serializers.CharField()
    intro = serializers.CharField(allow_blank=True)
    accepting = serializers.BooleanField()
    reviewCount = serializers.IntegerField()
    createdAt = serializers.DateTimeField()
    updatedAt = serializers.DateTimeField()


class PublicPageSerializer(serializers.Serializer[dict[str, object]]):
    """The page as a stranger with a phone sees it."""

    slug = serializers.CharField()
    title = serializers.CharField()
    intro = serializers.CharField(allow_blank=True)
    organizationName = serializers.CharField(allow_blank=True)
    accepting = serializers.BooleanField()
    festivals = inline_serializer(
        name="ReviewFestivalOption",
        fields={"id": serializers.CharField(), "title": serializers.CharField()},
        many=True,
    )


class ReviewSerializer(serializers.Serializer[dict[str, object]]):
    """One note as the organizer (or the platform operator) reads it."""

    id = serializers.CharField()
    authorName = serializers.CharField(allow_null=True)
    text = serializers.CharField()
    photos = serializers.ListField(child=serializers.CharField())
    competitionId = serializers.CharField(allow_null=True)
    competitionTitle = serializers.CharField(allow_null=True)
    submittedAt = serializers.DateTimeField()
    consentType = serializers.CharField()
    consentVersion = serializers.CharField()
    consentAcceptedAt = serializers.DateTimeField()
    organizationId = serializers.CharField()
    organizationName = serializers.CharField(allow_null=True)
