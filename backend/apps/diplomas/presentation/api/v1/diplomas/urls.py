from __future__ import annotations

from django.urls import path

from .views import (
    DiplomaAssignmentDetailView,
    DiplomaAssignmentsView,
    DiplomaTemplateDocumentView,
    DiplomaTemplateLayoutView,
    DiplomaTemplatesView,
)

app_name = "diplomas"

urlpatterns = [
    path("staff/diplomas/templates", DiplomaTemplatesView.as_view(), name="templates"),
    path(
        "staff/diplomas/templates/<str:template_id>/document",
        DiplomaTemplateDocumentView.as_view(),
        name="template-document",
    ),
    path(
        "staff/diplomas/templates/<str:template_id>/layout",
        DiplomaTemplateLayoutView.as_view(),
        name="template-layout",
    ),
    path("staff/diplomas/assignments", DiplomaAssignmentsView.as_view(), name="assignments"),
    path(
        "staff/diplomas/assignments/<str:assignment_id>",
        DiplomaAssignmentDetailView.as_view(),
        name="assignment-detail",
    ),
]
