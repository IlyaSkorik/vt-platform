"""Organizer routes for the Reviews bounded context.

Mounted under ``/api/v1/`` (ARCH-001 §14, API-000 §2). Everything lives under
``staff/`` because administering the page is organizer work; the public endpoints
and the operator's console have their own routers.
"""

from __future__ import annotations

from django.urls import path

from .views import ReviewCollectionView, ReviewDetailView, ReviewPageQrView, ReviewPageView

app_name = "reviews"

urlpatterns = [
    # One page per organization, so it is addressed by the caller's own membership
    # rather than by an id the client would first have to learn.
    path("staff/reviews/page", ReviewPageView.as_view(), name="page"),
    path("staff/reviews/page/qr.png", ReviewPageQrView.as_view(), name="page-qr"),
    path("staff/reviews", ReviewCollectionView.as_view(), name="collection"),
    path("staff/reviews/<str:review_id>", ReviewDetailView.as_view(), name="detail"),
]
