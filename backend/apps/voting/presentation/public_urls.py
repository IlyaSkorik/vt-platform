"""Public voting routes (anyone-facing).

Mounted separately from the organizer router so the public edge shares no routing,
auth or namespace with the staff constructor. The write here is the point of the
whole context: it is how somebody in a hall votes, and it carries no credential
beyond the link they were handed.
"""

from __future__ import annotations

from django.urls import path

from .api.v1.public_views import PublicBallotDetailView, PublicBallotVoteView

app_name = "public_voting"

urlpatterns = [
    path("public/ballots/<str:slug>", PublicBallotDetailView.as_view(), name="detail"),
    path("public/ballots/<str:slug>/votes", PublicBallotVoteView.as_view(), name="votes"),
]
