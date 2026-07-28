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
    ProgramDetailView,
    ProgramItemCollectionView,
    ProgramItemDetailView,
    ProgramItemOrderView,
    ProgramItemsFillView,
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
    path("staff/programs/<str:program_id>/items/<str:item_id>", ProgramItemDetailView.as_view(), name="item-detail"),
    path("staff/programs/<str:program_id>/shares", ProgramShareCollectionView.as_view(), name="shares"),
    path("staff/programs/<str:program_id>/shares/<str:share_id>", ProgramShareDetailView.as_view(), name="share-detail"),
]
