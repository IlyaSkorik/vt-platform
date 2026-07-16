from __future__ import annotations

from django.urls import path

from .views import (
    OrganizerProcessingActionView,
    OrganizerProcessingBulkView,
    OrganizerProcessingExportView,
    OrganizerProcessingWorkspaceView,
)

app_name = "organizer-processing"

urlpatterns = [
    path("staff/applications/workspace", OrganizerProcessingWorkspaceView.as_view(), name="workspace"),
    path("staff/applications/bulk", OrganizerProcessingBulkView.as_view(), name="bulk"),
    path("staff/applications/export", OrganizerProcessingExportView.as_view(), name="export"),
    path(
        "staff/applications/<str:submission_id>/actions/<str:action>",
        OrganizerProcessingActionView.as_view(),
        name="action",
    ),
]
