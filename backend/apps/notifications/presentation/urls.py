"""Cabinet notification-feed routes.

Mounted under ``/api/v1/`` beside the other participant-facing "me" edges (see
``apps.diplomas.presentation.me_urls``): authenticated, not staff-gated, and scoped
to the caller's own account.
"""

from __future__ import annotations

from django.urls import path

from apps.notifications.presentation.api.v1.views import (
    MyNotificationReadView,
    MyNotificationsReadView,
    MyNotificationsView,
)

app_name = "notifications"

urlpatterns = [
    path("me/notifications", MyNotificationsView.as_view(), name="feed"),
    path("me/notifications/read", MyNotificationsReadView.as_view(), name="read-all"),
    path("me/notifications/<str:notification_id>/read", MyNotificationReadView.as_view(), name="read-one"),
]
