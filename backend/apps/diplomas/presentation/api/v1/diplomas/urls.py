from __future__ import annotations

from django.urls import path

from .views import (
    DiplomaAssignmentDetailView,
    DiplomaAssignmentsView,
    DiplomaPreviewApplicationsView,
    DiplomaPreviewBindingsView,
    DiplomaPrintJobDetailView,
    DiplomaPrintPackageView,
    DiplomaRegistryDetailView,
    DiplomaRegistryView,
    DiplomaTemplateDocumentView,
    DiplomaTemplateLayoutView,
    DiplomaTemplatesView,
)

app_name = "diplomas"

urlpatterns = [
    path("staff/diplomas/templates", DiplomaTemplatesView.as_view(), name="templates"),
    path("staff/diplomas/registry", DiplomaRegistryView.as_view(), name="registry"),
    path(
        "staff/diplomas/registry/<str:diploma_id>",
        DiplomaRegistryDetailView.as_view(),
        name="registry-detail",
    ),
    path(
        "staff/diplomas/print-package",
        DiplomaPrintPackageView.as_view(),
        name="print-package",
    ),
    path(
        "staff/diplomas/print-package/<str:job_id>",
        DiplomaPrintJobDetailView.as_view(),
        name="print-job-detail",
    ),
    path(
        "staff/diplomas/preview/applications",
        DiplomaPreviewApplicationsView.as_view(),
        name="preview-applications",
    ),
    path(
        "staff/diplomas/preview/bindings",
        DiplomaPreviewBindingsView.as_view(),
        name="preview-bindings",
    ),
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
