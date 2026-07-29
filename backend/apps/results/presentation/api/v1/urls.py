"""Organizer routes for the Results bounded context.

Mounted under ``/api/v1/`` (ARCH-001 §14, API-000 §2). Everything lives under ``staff/``
because entering and publishing results is organizer work; the two public reads have their
own router (:mod:`apps.results.presentation.public_urls`).
"""

from __future__ import annotations

from django.urls import path

from .views import (
    ProtocolAwardsView,
    ProtocolCandidatesView,
    ProtocolCollectionView,
    ProtocolDetailView,
    ProtocolPublicationView,
    ProtocolRowCollectionView,
    ProtocolRowDetailView,
    ProtocolRowNumbersView,
    ProtocolRowOrderView,
    ProtocolRowSyncView,
)

app_name = "results"

urlpatterns = [
    path("staff/protocols", ProtocolCollectionView.as_view(), name="collection"),
    path("staff/protocols/<str:protocol_id>", ProtocolDetailView.as_view(), name="detail"),
    path("staff/protocols/<str:protocol_id>/candidates", ProtocolCandidatesView.as_view(), name="candidates"),
    path("staff/protocols/<str:protocol_id>/rows", ProtocolRowCollectionView.as_view(), name="rows"),
    path("staff/protocols/<str:protocol_id>/rows/sync", ProtocolRowSyncView.as_view(), name="rows-sync"),
    path("staff/protocols/<str:protocol_id>/rows/order", ProtocolRowOrderView.as_view(), name="rows-order"),
    path("staff/protocols/<str:protocol_id>/rows/numbers", ProtocolRowNumbersView.as_view(), name="rows-numbers"),
    path("staff/protocols/<str:protocol_id>/rows/<str:row_id>", ProtocolRowDetailView.as_view(), name="row-detail"),
    # The results themselves: one endpoint for a single award and a whole nomination alike.
    path("staff/protocols/<str:protocol_id>/awards", ProtocolAwardsView.as_view(), name="awards"),
    path("staff/protocols/<str:protocol_id>/publication", ProtocolPublicationView.as_view(), name="publication"),
]
