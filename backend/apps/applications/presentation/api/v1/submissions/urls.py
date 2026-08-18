"""URL routes for the Submission attachment endpoints.

Mounted under ``/api/v1/`` by :mod:`apps.applications.presentation.urls`.
"""

from __future__ import annotations

from django.urls import path

from apps.applications.presentation.api.v1.submissions.content_views import (
    SubmissionDetailView,
    SubmissionParticipantDetailView,
    SubmissionParticipantMembersView,
    SubmissionParticipantsView,
    SubmissionPerformanceView,
    SubmissionPriceView,
    SubmissionTeacherDetailView,
    SubmissionTeachersView,
)
from apps.applications.presentation.api.v1.submissions.views import (
    SubmissionAttachmentDetailView,
    SubmissionAttachmentsView,
)

app_name = "submissions"

urlpatterns = [
    path("submissions/<str:submission_id>", SubmissionDetailView.as_view(), name="detail"),
    path("submissions/<str:submission_id>/performance", SubmissionPerformanceView.as_view(), name="performance"),
    path("submissions/<str:submission_id>/participants", SubmissionParticipantsView.as_view(), name="participants"),
    path(
        "submissions/<str:submission_id>/participants/<str:participant_id>",
        SubmissionParticipantDetailView.as_view(),
        name="participant-detail",
    ),
    path(
        "submissions/<str:submission_id>/participants/<str:participant_id>/members",
        SubmissionParticipantMembersView.as_view(),
        name="participant-members",
    ),
    path("submissions/<str:submission_id>/teachers", SubmissionTeachersView.as_view(), name="teachers"),
    path("submissions/<str:submission_id>/teachers/<str:teacher_id>", SubmissionTeacherDetailView.as_view(), name="teacher-detail"),
    path("submissions/<str:submission_id>/price", SubmissionPriceView.as_view(), name="price"),
    path("submissions/<str:submission_id>/attachments", SubmissionAttachmentsView.as_view(), name="attachments"),
    path(
        "submissions/<str:submission_id>/attachments/<str:attachment_id>",
        SubmissionAttachmentDetailView.as_view(),
        name="attachment-detail",
    ),
]
