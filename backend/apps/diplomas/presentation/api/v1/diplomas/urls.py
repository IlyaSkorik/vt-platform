from __future__ import annotations

from django.urls import path

from .fonts import DiplomaFontDetailView, DiplomaFontsView
from .views import (
    DiplomaAssignmentDetailView,
    DiplomaAssignmentsView,
    DiplomaGenerationArchiveView,
    DiplomaPreviewApplicationsView,
    DiplomaPreviewBindingsView,
    DiplomaPrintJobDetailView,
    DiplomaPrintPackageSummaryView,
    DiplomaPrintPackageView,
    DiplomaRegistryDetailView,
    DiplomaRegistryView,
    DiplomaTemplateDocumentView,
    DiplomaTemplateLayoutView,
    DiplomaTemplatesView,
    DocumentGenerationView,
)

app_name = "diplomas"

urlpatterns = [
    path("staff/diplomas/templates", DiplomaTemplatesView.as_view(), name="templates"),
    # The font library: the catalog the editor's dropdown is built from, and the uploads
    # that extend it beyond the families the platform happens to ship.
    path("staff/diplomas/fonts", DiplomaFontsView.as_view(), name="fonts"),
    path("staff/diplomas/fonts/<str:font_id>", DiplomaFontDetailView.as_view(), name="font-detail"),
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
    # Must precede the "<job_id>" pattern so "summary" is not read as a job id.
    path(
        "staff/diplomas/print-package/summary",
        DiplomaPrintPackageSummaryView.as_view(),
        name="print-package-summary",
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
    # Non-registry documents (thank-you letters today), generated per nomination
    # from that nomination's own template of the kind.
    path(
        "staff/diplomas/documents/generate",
        DocumentGenerationView.as_view(),
        name="generate-documents",
    ),
    # The history of completed generation runs, of every document kind.
    path(
        "staff/diplomas/generation-archive",
        DiplomaGenerationArchiveView.as_view(),
        name="generation-archive",
    ),
    path("staff/diplomas/assignments", DiplomaAssignmentsView.as_view(), name="assignments"),
    path(
        "staff/diplomas/assignments/<str:assignment_id>",
        DiplomaAssignmentDetailView.as_view(),
        name="assignment-detail",
    ),
]
