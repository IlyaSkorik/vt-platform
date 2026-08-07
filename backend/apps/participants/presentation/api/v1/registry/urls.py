from __future__ import annotations

from django.urls import path

from apps.participants.presentation.api.v1.registry.views import (
    EducationalOrganizationArchiveView,
    EducationalOrganizationCollectionView,
    EducationalOrganizationDetailView,
    ParticipantArchiveView,
    ParticipantAvatarUploadView,
    ParticipantRegistryCollectionView,
    ParticipantRegistryDetailView,
)

app_name = "participant_registry"

urlpatterns = [
    path("participants/registry", ParticipantRegistryCollectionView.as_view(), name="collection"),
    # Must precede the "<participant_id>" pattern, or "avatar" is read as an id.
    path("participants/registry/avatar", ParticipantAvatarUploadView.as_view(), name="avatar"),
    path("participants/registry/<str:participant_id>", ParticipantRegistryDetailView.as_view(), name="detail"),
    path(
        "participants/registry/<str:participant_id>/archive",
        ParticipantArchiveView.as_view(),
        name="archive",
    ),
    path(
        "participants/organizations",
        EducationalOrganizationCollectionView.as_view(),
        name="organizations",
    ),
    path(
        "participants/organizations/<str:organization_id>",
        EducationalOrganizationDetailView.as_view(),
        name="organizations-detail",
    ),
    path(
        "participants/organizations/<str:organization_id>/archive",
        EducationalOrganizationArchiveView.as_view(),
        name="organizations-archive",
    ),
]
