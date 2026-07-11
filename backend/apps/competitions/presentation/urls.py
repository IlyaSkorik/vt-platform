"""Competition API routes."""

from __future__ import annotations

from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .api.v1.views import CompetitionViewSet

app_name = "competitions"

router = DefaultRouter(trailing_slash=False)
router.register(
    r"competitions",
    CompetitionViewSet,
    basename="competition",
)

urlpatterns = [
    path(
        "",
        include(router.urls),
    ),
]
