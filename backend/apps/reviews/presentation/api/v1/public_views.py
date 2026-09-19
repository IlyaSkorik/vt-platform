"""Public reviews edge (anyone-facing).

Two endpoints and no authentication: whoever holds the link reads the page and
leaves a note on it, with no account. The slug *is* the credential — minted per
organization from a confusable-free alphabet, never derived from its name — so a
page cannot be found by guessing, and a retired link is indistinguishable from one
that never existed.

A page that has stopped collecting still answers its ``GET``, with ``accepting``
false. The banner is printed on cloth and will outlive the season; somebody who
walked over to it deserves a sentence rather than a dead end.

Leaving a note is throttled in its own bucket, far below the anonymous default: a
person writing a review sends one request, and it carries photographs.

**Why the whole thing is one multipart request.** Uploading photographs first and
submitting them by reference would mean an endpoint that writes bytes for
strangers with nothing yet attached to them, and every abandoned form would leave
files behind. One request means a photograph is only ever stored as part of a note
that was accepted — and the handful that are stored before a *later* validation
fails are removed again below, so the storage holds nothing orphaned.
"""

from __future__ import annotations

from typing import Any

from django.core.files.storage import default_storage
from drf_spectacular.utils import OpenApiResponse, extend_schema
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.permissions import AllowAny
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView

from apps.reviews.application.commands import SubmitReviewCommand
from apps.reviews.composition import build_review_service
from apps.reviews.domain.exceptions import ConsentRequiredError, InvalidReviewDataError, ReviewError
from apps.reviews.domain.value_objects import PHOTOS_MAX
from apps.reviews.presentation.api.v1 import resources
from apps.reviews.presentation.api.v1.files import PhotoRejectedError, store_photo
from apps.reviews.presentation.api.v1.problems import envelope, problem_response, review_problem
from apps.reviews.presentation.api.v1.serializers import (
    PublicPageSerializer,
    ReviewProblemDetailSerializer,
    ReviewSerializer,
    SubmitReviewRequestSerializer,
)

_TAG = "Public Reviews"

__all__ = ["PublicReviewPageView", "PublicReviewSubmitView"]

_PROBLEM_RESPONSES = {
    400: OpenApiResponse(ReviewProblemDetailSerializer, description="Malformed."),
    404: OpenApiResponse(ReviewProblemDetailSerializer, description="No page behind this link."),
    422: OpenApiResponse(ReviewProblemDetailSerializer, description="Closed, or sent without consent."),
    429: OpenApiResponse(ReviewProblemDetailSerializer, description="Too many submissions."),
}


class _PublicView(APIView):
    """Anyone, with no account. The slug is the only credential."""

    authentication_classes = ()
    permission_classes = (AllowAny,)

    def _problem(self, error: ReviewError, request: Request) -> Response:
        return review_problem(error, instance=request.get_full_path(), request=request)


class PublicReviewPageView(_PublicView):
    """``GET`` the page behind a scanned code."""

    @extend_schema(
        tags=[_TAG],
        operation_id="public_review_page",
        summary="The review page behind a public link",
        request=None,
        responses={200: PublicPageSerializer, **_PROBLEM_RESPONSES},
    )
    def get(self, request: Request, slug: str) -> Response:
        try:
            page = build_review_service().public_page(slug)
        except ReviewError as exc:
            return self._problem(exc, request)
        return envelope(resources.public_page(page), request)


class PublicReviewSubmitView(_PublicView):
    """``POST`` a note, with up to five photographs, in one multipart request."""

    parser_classes = (MultiPartParser, FormParser)
    throttle_classes = (ScopedRateThrottle,)
    throttle_scope = "review_submit"

    @extend_schema(
        tags=[_TAG],
        operation_id="public_review_submit",
        summary="Leave a review",
        description=(
            "Multipart. `text`, `consentVersion` and `consentAccepted=true` are required; "
            "`authorName` and `competitionId` are optional, and up to five `photos` files may be attached."
        ),
        request={
            "multipart/form-data": {
                "type": "object",
                "properties": {
                    "text": {"type": "string"},
                    "consentType": {"type": "string"},
                    "consentVersion": {"type": "string"},
                    "consentAccepted": {"type": "boolean"},
                    "authorName": {"type": "string"},
                    "competitionId": {"type": "string", "format": "uuid"},
                    "photos": {"type": "array", "items": {"type": "string", "format": "binary"}},
                },
                "required": ["text", "consentType", "consentVersion", "consentAccepted"],
            }
        },
        responses={201: ReviewSerializer, **_PROBLEM_RESPONSES},
    )
    def post(self, request: Request, slug: str) -> Response:
        serializer = SubmitReviewRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        payload: dict[str, Any] = serializer.validated_data

        if not payload.get("consentAccepted"):
            # Refused before anything is written: a note whose author did not agree
            # to it being kept is not a note this platform may store at all.
            return self._problem(
                ConsentRequiredError("Без согласия на обработку персональных данных отзыв не сохраняется."),
                request,
            )

        uploads = request.FILES.getlist("photos")
        if len(uploads) > PHOTOS_MAX:
            return self._problem(InvalidReviewDataError(f"К отзыву можно приложить не больше {PHOTOS_MAX} фотографий."), request)

        stored: list[str] = []
        try:
            for uploaded in uploads:
                stored.append(store_photo(uploaded, slug=str(slug)))
        except PhotoRejectedError as exc:
            _discard(stored)
            return problem_response(
                status=400,
                type_suffix="bad-request",
                title="Bad request",
                detail=str(exc),
                instance=request.get_full_path(),
                request=request,
            )

        command = SubmitReviewCommand(
            slug=str(slug),
            text=str(payload["text"]),
            consent_code=str(payload["consentType"]),
            consent_version=str(payload["consentVersion"]),
            author_name=str(payload.get("authorName") or "") or None,
            competition_id=str(payload["competitionId"]) if payload.get("competitionId") else None,
            photos=tuple(stored),
        )
        try:
            review = build_review_service().submit(command)
        except ReviewError as exc:
            # The note was refused, so its photographs have nothing to belong to.
            _discard(stored)
            return self._problem(exc, request)
        return envelope(resources.review(review), request, status=201)


def _discard(references: list[str]) -> None:
    """Remove photographs stored for a note that was not accepted after all.

    Best-effort: a storage that refuses to delete must not turn a validation
    message into a 500 for the person who is still trying to leave a review.
    """
    for reference in references:
        try:
            default_storage.delete(reference)
        except Exception:
            continue
