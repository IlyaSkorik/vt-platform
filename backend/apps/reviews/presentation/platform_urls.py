"""The platform operator's routes into the Reviews context.

Kept beside the context that owns the data rather than in ``apps.platform``: the
console borrows this context's reads, it does not reimplement them.
"""

from __future__ import annotations

from django.urls import path

from .api.v1.platform_views import PlatformReviewCollectionView, PlatformReviewDetailView

app_name = "platform_reviews"

urlpatterns = [
    path("platform/reviews", PlatformReviewCollectionView.as_view(), name="collection"),
    path("platform/reviews/<str:review_id>", PlatformReviewDetailView.as_view(), name="detail"),
]
