"""URL routes for the Identity authentication endpoints (API-001 §4).

Noun-resource paths only — never verbs (API-000 §3.3): logging in *creates* a
session (``POST /auth/sessions``), logging out *deletes* the current session
(``DELETE /auth/sessions/current``), and refreshing exchanges a token under the
``token`` sub-resource. Mounted under ``/api/v1/`` by
:mod:`apps.identity.presentation.urls`.
"""

from __future__ import annotations

from django.urls import path

from apps.identity.presentation.api.v1.auth.views import (
    CurrentSessionView,
    EmailVerificationConfirmationView,
    EmailVerificationRequestView,
    RegistrationView,
    SessionCollectionView,
    TokenRefreshView,
    CurrentUserView,
)

app_name = "auth"

urlpatterns = [
    path("auth/registration", RegistrationView.as_view(), name="registration"),
    path(
        "auth/email-verification/requests",
        EmailVerificationRequestView.as_view(),
        name="email-verification-requests",
    ),
    path(
        "auth/email-verification/confirmations",
        EmailVerificationConfirmationView.as_view(),
        name="email-verification-confirmations",
    ),
    path("auth/sessions", SessionCollectionView.as_view(), name="sessions"),
    path("auth/sessions/current", CurrentSessionView.as_view(), name="session-current"),
    path("auth/token/refresh", TokenRefreshView.as_view(), name="token-refresh"),
    path("users/me", CurrentUserView.as_view(), name="users-me"),
]
