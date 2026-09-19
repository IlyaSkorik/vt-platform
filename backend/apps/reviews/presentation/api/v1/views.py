"""Organizer REST edge for the Reviews bounded context.

Thin adapters over :class:`~apps.reviews.application.services.ReviewService`:
parse, delegate, render. Every endpoint is staff-gated *and* module-gated — an
organization that was not sold the reviews block is refused here, not merely shown
a panel without the menu item.

The page is read into existence. ``GET`` on it mints the organization's page the
first time anybody opens the screen, because the alternative is a "create page"
button whose only effect is to enable the button beside it — and because the link
must come into being exactly once, before anyone prints it.
"""

from __future__ import annotations

import io
import uuid

import qrcode
from django.http import HttpResponse
from django.http.response import HttpResponseBase
from drf_spectacular.utils import OpenApiResponse, extend_schema
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.identity.infrastructure.auth import CredentialAwareJWTAuthentication
from apps.organization.domain.value_objects import OrganizationModule
from apps.organization.presentation.permissions import IsModuleEnabled, IsOrganizationStaff
from apps.organization.presentation.scope import callers_organization_id
from apps.reviews.application.commands import UpdateReviewPageCommand
from apps.reviews.composition import build_review_service
from apps.reviews.domain.exceptions import ReviewError, ReviewNotFoundError
from apps.reviews.presentation.api.v1 import resources
from apps.reviews.presentation.api.v1.problems import envelope, review_problem
from apps.reviews.presentation.api.v1.serializers import (
    ReviewPageSerializer,
    ReviewProblemDetailSerializer,
    ReviewSerializer,
    UpdateReviewPageRequestSerializer,
)

_TAG = "Reviews"

__all__ = ["ReviewCollectionView", "ReviewDetailView", "ReviewPageQrView", "ReviewPageView"]

_PROBLEM_RESPONSES = {
    400: OpenApiResponse(ReviewProblemDetailSerializer, description="Malformed."),
    403: OpenApiResponse(ReviewProblemDetailSerializer, description="Module not connected, or not staff."),
    404: OpenApiResponse(ReviewProblemDetailSerializer, description="Not found."),
}


class _StaffView(APIView):
    """Authenticated organization staff, whose organization holds the module."""

    authentication_classes = (CredentialAwareJWTAuthentication,)
    permission_classes = (
        IsAuthenticated,
        IsOrganizationStaff,
        IsModuleEnabled.of(OrganizationModule.REVIEWS),
    )

    def _problem(self, error: ReviewError, request: Request) -> Response:
        return review_problem(error, instance=request.get_full_path(), request=request)

    def _organization(self, request: Request) -> uuid.UUID | None:
        return callers_organization_id(request)


class ReviewPageView(_StaffView):
    """``GET`` the organization's review page; ``PATCH`` its wording and switch."""

    @extend_schema(
        tags=[_TAG],
        operation_id="reviews_get_page",
        summary="The organization's review page (created on first read)",
        request=None,
        responses={200: ReviewPageSerializer, **_PROBLEM_RESPONSES},
    )
    def get(self, request: Request) -> Response:
        organization_id = self._organization(request)
        if organization_id is None:  # pragma: no cover - the staff gate precedes this
            return self._problem(ReviewNotFoundError("Страница отзывов не найдена."), request)
        try:
            page = build_review_service().page_of(organization_id)
        except ReviewError as exc:
            return self._problem(exc, request)
        return envelope(resources.review_page(page), request)

    @extend_schema(
        tags=[_TAG],
        operation_id="reviews_update_page",
        summary="Reword the page, or start and stop collecting",
        request=UpdateReviewPageRequestSerializer,
        responses={200: ReviewPageSerializer, **_PROBLEM_RESPONSES},
    )
    def patch(self, request: Request) -> Response:
        serializer = UpdateReviewPageRequestSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        payload = serializer.validated_data
        organization_id = self._organization(request)
        if organization_id is None:  # pragma: no cover - the staff gate precedes this
            return self._problem(ReviewNotFoundError("Страница отзывов не найдена."), request)

        service = build_review_service()
        # The page is minted here too: an organizer who lands on the screen and
        # immediately edits the heading must not be told there is nothing to edit.
        service.page_of(organization_id)
        command = UpdateReviewPageCommand(
            organization_id=str(organization_id),
            title=str(payload["title"]) if "title" in payload else None,
            intro=str(payload["intro"]) if "intro" in payload else None,
            accepting=bool(payload["accepting"]) if "accepting" in payload else None,
        )
        try:
            page = service.update_page(command)
        except ReviewError as exc:
            return self._problem(exc, request)
        return envelope(resources.review_page(page), request)


class ReviewPageQrView(_StaffView):
    """``GET`` the QR code that goes on the banner."""

    @extend_schema(
        tags=[_TAG],
        operation_id="reviews_page_qr",
        summary="Download the page's QR code",
        request=None,
        responses={200: OpenApiResponse(description="A PNG of the public review link.")},
    )
    def get(self, request: Request) -> HttpResponseBase:
        organization_id = self._organization(request)
        if organization_id is None:  # pragma: no cover - the staff gate precedes this
            return self._problem(ReviewNotFoundError("Страница отзывов не найдена."), request)
        try:
            page = build_review_service().page_of(organization_id)
        except ReviewError as exc:
            return self._problem(exc, request)

        url = request.build_absolute_uri(f"/reviews/{page.slug}")
        image = qrcode.make(url)
        payload = io.BytesIO()
        image.save(payload, format="PNG")
        response = HttpResponse(payload.getvalue(), content_type="image/png")
        response["Content-Disposition"] = f'attachment; filename="qr-reviews-{page.slug}.png"'
        return response


class ReviewCollectionView(_StaffView):
    """``GET`` everything left on this organization's page, newest first."""

    @extend_schema(
        tags=[_TAG],
        operation_id="reviews_list",
        summary="List the reviews left on the organization's page",
        request=None,
        responses={200: ReviewSerializer(many=True), **_PROBLEM_RESPONSES},
    )
    def get(self, request: Request) -> Response:
        organization_id = self._organization(request)
        if organization_id is None:  # pragma: no cover - the staff gate precedes this
            return envelope([], request)
        reviews = build_review_service().own_reviews(organization_id)
        return envelope([resources.review(row) for row in reviews], request)


class ReviewDetailView(_StaffView):
    """``DELETE`` one note."""

    @extend_schema(
        tags=[_TAG],
        operation_id="reviews_delete",
        summary="Remove a review",
        description="Another organization's review answers 404, not 403.",
        request=None,
        responses={204: OpenApiResponse(description="Removed."), **_PROBLEM_RESPONSES},
    )
    def delete(self, request: Request, review_id: str) -> Response:
        organization_id = self._organization(request)
        if organization_id is None:  # pragma: no cover - the staff gate precedes this
            return self._problem(ReviewNotFoundError("Отзыв не найден."), request)
        try:
            parsed = uuid.UUID(review_id)
        except (ValueError, TypeError):
            # A malformed id gets the same answer as somebody else's: the caller
            # learns only that they have nothing here.
            return self._problem(ReviewNotFoundError("Отзыв не найден."), request)
        try:
            build_review_service().remove(parsed, organization_id=organization_id)
        except ReviewError as exc:
            return self._problem(exc, request)
        return Response(status=204)
