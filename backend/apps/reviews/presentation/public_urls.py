"""Public review routes (anyone-facing).

Mounted separately from the organizer router so the public edge shares no routing,
auth or namespace with the workspace. The write here is the point of the whole
context: it is how somebody in a foyer says what they thought, and it carries no
credential beyond the code they scanned.
"""

from __future__ import annotations

from django.urls import path

from .api.v1.public_views import PublicReviewPageView, PublicReviewSubmitView

app_name = "public_reviews"

urlpatterns = [
    path("public/reviews/<str:slug>", PublicReviewPageView.as_view(), name="page"),
    # A path of its own rather than a POST on the one above, so the submission's
    # throttle bucket cannot also brake people merely opening the page.
    path("public/reviews/<str:slug>/entries", PublicReviewSubmitView.as_view(), name="submit"),
]
