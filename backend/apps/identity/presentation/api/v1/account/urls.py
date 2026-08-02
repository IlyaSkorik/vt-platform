"""URL routes for the account self-service endpoints.

Sub-resources of ``/users/me``, whose ``GET`` lives in the composition app: the
account is composed from several contexts to read, but each of these values
belongs to Identity alone to write.
"""

from __future__ import annotations

from django.urls import path

from apps.identity.presentation.api.v1.account.views import (
    AccountEmailView,
    AccountPasswordView,
    AccountPhoneView,
)

app_name = "account"

urlpatterns = [
    path("users/me/password", AccountPasswordView.as_view(), name="password"),
    path("users/me/email", AccountEmailView.as_view(), name="email"),
    path("users/me/phone", AccountPhoneView.as_view(), name="phone"),
]
