"""Organizer routes for the Programs bounded context.

Mounted under ``/api/v1/`` (ARCH-001 §14, API-000 §2). Everything lives under
``staff/`` because building a running order is organizer work; the one public read has
its own router (:mod:`apps.programs.presentation.public_urls`).
"""

from __future__ import annotations

from django.urls import path

from .views import (
    ProgramCandidatesView,
    ProgramCollectionView,
    ProgramColumnCollectionView,
    ProgramColumnDetailView,
    ProgramDetailView,
    ProgramExportView,
    ProgramItemCellsView,
    ProgramItemCollectionView,
    ProgramItemDetailView,
    ProgramItemNumbersView,
    ProgramItemOrderView,
    ProgramItemsFillView,
    ProgramMediaArchiveView,
    ProgramMusicArchiveView,
    ProgramProgressView,
    ProgramShareCollectionView,
    ProgramShareDetailView,
)

app_name = "programs"

urlpatterns = [
    path("staff/programs", ProgramCollectionView.as_view(), name="collection"),
    path("staff/programs/<str:program_id>", ProgramDetailView.as_view(), name="detail"),
    path("staff/programs/<str:program_id>/candidates", ProgramCandidatesView.as_view(), name="candidates"),
    path("staff/programs/<str:program_id>/items", ProgramItemCollectionView.as_view(), name="items"),
    path("staff/programs/<str:program_id>/items/fill", ProgramItemsFillView.as_view(), name="items-fill"),
    path("staff/programs/<str:program_id>/items/order", ProgramItemOrderView.as_view(), name="items-order"),
    path("staff/programs/<str:program_id>/items/numbers", ProgramItemNumbersView.as_view(), name="items-numbers"),
    path("staff/programs/<str:program_id>/items/<str:item_id>", ProgramItemDetailView.as_view(), name="item-detail"),
    path("staff/programs/<str:program_id>/items/<str:item_id>/cells", ProgramItemCellsView.as_view(), name="item-cells"),
    path("staff/programs/<str:program_id>/columns", ProgramColumnCollectionView.as_view(), name="columns"),
    path("staff/programs/<str:program_id>/columns/<str:column_id>", ProgramColumnDetailView.as_view(), name="column-detail"),
    path("staff/programs/<str:program_id>/progress", ProgramProgressView.as_view(), name="progress"),
    path("staff/programs/<str:program_id>/export.pdf", ProgramExportView.as_view(), name="export-pdf"),
    path("staff/programs/<str:program_id>/music.zip", ProgramMusicArchiveView.as_view(), name="music-archive"),
    path("staff/programs/<str:program_id>/media.zip", ProgramMediaArchiveView.as_view(), name="media-archive"),
    path("staff/programs/<str:program_id>/shares", ProgramShareCollectionView.as_view(), name="shares"),
    path("staff/programs/<str:program_id>/shares/<str:share_id>", ProgramShareDetailView.as_view(), name="share-detail"),
]
