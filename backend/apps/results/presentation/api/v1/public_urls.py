"""The two unauthenticated Results routes.

Kept in their own module (and mounted by their own root include) so nothing public is ever
added by editing the staff router, and a reader of ``config/urls.py`` can see at a glance
which of this context's endpoints need no account.
"""

from __future__ import annotations

from django.urls import path

from .public_views import PublicCompetitionResultsView, PublicProtocolDetailView

app_name = "results-public"

urlpatterns = [
    # The published protocol itself - what a participant opens from the letter or the page.
    path("public/protocols/<str:slug>", PublicProtocolDetailView.as_view(), name="protocol"),
    # Which protocols a competition has published - the landing page's "Результаты".
    path("public/competitions/<str:competition_id>/results", PublicCompetitionResultsView.as_view(), name="competition-results"),
]
