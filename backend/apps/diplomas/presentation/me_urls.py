"""Participant-facing document routes ("Мои документы").

Mounted separately from the organizer :mod:`~apps.diplomas.presentation.urls`
router: this edge is authenticated but not staff-gated, and it shares no routing or
namespace with the staff diplomas workspace.
"""

from __future__ import annotations

from django.urls import path

from .api.v1.me_views import MyDocumentsView, MyIndividualDiplomasArchiveView

app_name = "my_documents"

urlpatterns = [
    path("me/documents", MyDocumentsView.as_view(), name="documents"),
    path("me/documents/archive", MyIndividualDiplomasArchiveView.as_view(), name="documents-archive"),
]
