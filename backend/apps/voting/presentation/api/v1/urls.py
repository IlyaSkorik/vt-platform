"""Organizer routes for the Voting bounded context.

Mounted under ``/api/v1/`` (ARCH-001 §14, API-000 §2). Everything lives under
``staff/`` because assembling a ballot is organizer work; the two public endpoints
have their own router (:mod:`apps.voting.presentation.public_urls`).
"""

from __future__ import annotations

from django.urls import path

from .views import (
    BallotCloseView,
    BallotCollectionView,
    BallotDetailView,
    BallotNomineeCollectionView,
    BallotNomineeDetailView,
    BallotNomineeImportView,
    BallotNomineeOrderView,
    BallotNomineeTemplateView,
    BallotOpenView,
    BallotQrView,
    BallotResultsView,
    BallotSeedView,
)

app_name = "voting"

urlpatterns = [
    path("staff/ballots", BallotCollectionView.as_view(), name="collection"),
    path("staff/ballots/<str:ballot_id>", BallotDetailView.as_view(), name="detail"),
    path("staff/ballots/<str:ballot_id>/open", BallotOpenView.as_view(), name="open"),
    path("staff/ballots/<str:ballot_id>/close", BallotCloseView.as_view(), name="close"),
    path("staff/ballots/<str:ballot_id>/nominees", BallotNomineeCollectionView.as_view(), name="nominees"),
    # Listed before the `<nominee_id>` pattern so the literal routes win — otherwise
    # "order" and "import" would be read as nominees with those ids.
    path("staff/ballots/<str:ballot_id>/nominees/order", BallotNomineeOrderView.as_view(), name="nominees-order"),
    path("staff/ballots/<str:ballot_id>/nominees/import", BallotNomineeImportView.as_view(), name="nominees-import"),
    path("staff/ballots/<str:ballot_id>/nominees/template.xlsx", BallotNomineeTemplateView.as_view(), name="nominees-template"),
    path("staff/ballots/<str:ballot_id>/nominees/<str:nominee_id>", BallotNomineeDetailView.as_view(), name="nominee-detail"),
    path("staff/ballots/<str:ballot_id>/seed", BallotSeedView.as_view(), name="seed"),
    path("staff/ballots/<str:ballot_id>/results.xlsx", BallotResultsView.as_view(), name="results"),
    path("staff/ballots/<str:ballot_id>/qr.png", BallotQrView.as_view(), name="qr"),
]
