"""The platform operator's window onto every review on the platform.

Lives in this context rather than in ``apps.platform`` for the same reason the
purge screen's queries do not: reading reviews is what Reviews owns, and a console
that queried another context's tables directly would be a second, quieter copy of
this one's rules. What ``apps.platform`` supplies is the permission class.

This is the only read in the context that is not scoped to one organization. It
exists so a complaint about what somebody wrote — a name that should not be there,
a photograph that should not have been taken — can be looked at and acted on by
the one party above both the organizer and the author.
"""

from __future__ import annotations

import uuid

from drf_spectacular.utils import OpenApiResponse, extend_schema
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.identity.infrastructure.auth import CredentialAwareJWTAuthentication
from apps.platform.presentation.permissions import IsPlatformAdministrator
from apps.reviews.composition import build_review_service
from apps.reviews.domain.exceptions import ReviewError, ReviewNotFoundError
from apps.reviews.presentation.api.v1 import resources
from apps.reviews.presentation.api.v1.problems import envelope, review_problem
from apps.reviews.presentation.api.v1.serializers import ReviewProblemDetailSerializer, ReviewSerializer

_TAG = "Platform Reviews"

__all__ = ["PlatformReviewCollectionView", "PlatformReviewDetailView"]

_PROBLEM_RESPONSES = {
    403: OpenApiResponse(ReviewProblemDetailSerializer, description="Not a platform operator."),
    404: OpenApiResponse(ReviewProblemDetailSerializer, description="Not found."),
}


class _OperatorView(APIView):
    """The platform operator, and nobody else.

    Deliberately not module-gated: whether an organization was sold the reviews
    block decides what *they* may do, not whether the operator may look at what
    was collected while they held it.
    """

    authentication_classes = (CredentialAwareJWTAuthentication,)
    permission_classes = (IsAuthenticated, IsPlatformAdministrator)

    def _problem(self, error: ReviewError, request: Request) -> Response:
        return review_problem(error, instance=request.get_full_path(), request=request)


class PlatformReviewCollectionView(_OperatorView):
    """``GET`` every review on the platform, newest first."""

    @extend_schema(
        tags=[_TAG],
        operation_id="platform_reviews_list",
        summary="List every review on the platform",
        request=None,
        responses={200: ReviewSerializer(many=True), **_PROBLEM_RESPONSES},
    )
    def get(self, request: Request) -> Response:
        reviews = build_review_service().all_reviews()
        return envelope([resources.review(row) for row in reviews], request)


class PlatformReviewDetailView(_OperatorView):
    """``DELETE`` any review, whoever it belongs to."""

    @extend_schema(
        tags=[_TAG],
        operation_id="platform_reviews_delete",
        summary="Remove any review",
        request=None,
        responses={204: OpenApiResponse(description="Removed."), **_PROBLEM_RESPONSES},
    )
    def delete(self, request: Request, review_id: str) -> Response:
        try:
            parsed = uuid.UUID(review_id)
        except (ValueError, TypeError):
            return self._problem(ReviewNotFoundError("Отзыв не найден."), request)
        try:
            build_review_service().remove(parsed)
        except ReviewError as exc:
            return self._problem(exc, request)
        return Response(status=204)
