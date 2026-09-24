"""URLconf entry point for the Judging bounded context (organizer + jury)."""

from __future__ import annotations

from apps.judging.presentation.api.v1.urls import app_name, urlpatterns

__all__ = ["app_name", "urlpatterns"]
