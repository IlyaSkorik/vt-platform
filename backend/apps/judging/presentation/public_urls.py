"""URLconf entry point for the unauthenticated hall board."""

from __future__ import annotations

from apps.judging.presentation.api.v1.public_urls import app_name, urlpatterns

__all__ = ["app_name", "urlpatterns"]
