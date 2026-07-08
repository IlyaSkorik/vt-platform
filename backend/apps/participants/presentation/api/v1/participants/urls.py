"""URL routes for the Participants API endpoints.

Noun-resource paths only — never verbs (API-000 §3.3): verifying a participant
*creates* a verification sub-resource, activating *creates* an activation, and
verifying a guardian link *creates* its verification. Mounted under ``/api/v1/`` by
:mod:`apps.participants.presentation.urls`.
"""

from __future__ import annotations

from django.urls import path

from apps.participants.presentation.api.v1.participants.views import (
    GuardianLinkCollectionView,
    GuardianLinkVerificationView,
    ParticipantActivationView,
    ParticipantCollectionView,
    ParticipantDetailView,
    ParticipantVerificationView,
)

app_name = "participants"

urlpatterns = [
    path("participants", ParticipantCollectionView.as_view(), name="collection"),
    path("participants/<str:participant_id>", ParticipantDetailView.as_view(), name="detail"),
    path(
        "participants/<str:participant_id>/guardian-links",
        GuardianLinkCollectionView.as_view(),
        name="guardian-links",
    ),
    path(
        "participants/<str:participant_id>/guardian-links/<str:guardian_id>/verification",
        GuardianLinkVerificationView.as_view(),
        name="guardian-link-verification",
    ),
    path(
        "participants/<str:participant_id>/verification",
        ParticipantVerificationView.as_view(),
        name="verification",
    ),
    path(
        "participants/<str:participant_id>/activation",
        ParticipantActivationView.as_view(),
        name="activation",
    ),
]
