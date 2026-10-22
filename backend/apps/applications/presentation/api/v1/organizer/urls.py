from __future__ import annotations

from django.urls import path

from .attachment_views import OrganizerSubmissionAttachmentDetailView, OrganizerSubmissionAttachmentsView
from .content_views import OrganizerSubmissionContentView
from .participants_views import (
    OrganizerParticipantRegistryCollectionView,
    OrganizerParticipantRegistryDetailView,
    OrganizerParticipantRegistryExportView,
)
from .views import (
    OrganizerProcessingActionView,
    OrganizerProcessingBulkView,
    OrganizerProcessingDocumentsArchiveView,
    OrganizerProcessingExportView,
    OrganizerProcessingWorkspaceView,
)

app_name = "organizer-processing"

urlpatterns = [
    path("staff/applications/workspace", OrganizerProcessingWorkspaceView.as_view(), name="workspace"),
    path("staff/applications/bulk", OrganizerProcessingBulkView.as_view(), name="bulk"),
    path("staff/applications/export", OrganizerProcessingExportView.as_view(), name="export"),
    path("staff/applications/documents.zip", OrganizerProcessingDocumentsArchiveView.as_view(), name="documents-archive"),
    path(
        "staff/applications/<str:submission_id>/actions/<str:action>",
        OrganizerProcessingActionView.as_view(),
        name="action",
    ),
    path(
        "staff/applications/<str:submission_id>/content",
        OrganizerSubmissionContentView.as_view(),
        name="content",
    ),
    path(
        "staff/applications/<str:submission_id>/attachments",
        OrganizerSubmissionAttachmentsView.as_view(),
        name="attachments",
    ),
    path(
        "staff/applications/<str:submission_id>/attachments/<str:attachment_id>",
        OrganizerSubmissionAttachmentDetailView.as_view(),
        name="attachment-detail",
    ),
    path(
        "staff/participants",
        OrganizerParticipantRegistryCollectionView.as_view(),
        name="participants",
    ),
    path(
        "staff/participants/export",
        OrganizerParticipantRegistryExportView.as_view(),
        name="participants-export",
    ),
    path(
        "staff/participants/<str:participant_key>",
        OrganizerParticipantRegistryDetailView.as_view(),
        name="participants-detail",
    ),
]
