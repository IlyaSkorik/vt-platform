"""The unauthenticated route: one board per slug."""

from __future__ import annotations

from django.urls import path

from .public_views import PublicBoardView

app_name = "judging-public"

urlpatterns = [
    path("public/judging/board/<str:slug>", PublicBoardView.as_view(), name="board"),
]
