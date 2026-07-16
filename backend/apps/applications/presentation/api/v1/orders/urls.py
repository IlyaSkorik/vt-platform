"""URL routes for the Application (order) API endpoints.

Noun-resource paths only (API-000 §3.3): submitting an order *creates* a placement,
requesting payment *creates* a payment-request, and so on. Mounted under
``/api/v1/`` by :mod:`apps.applications.presentation.urls`.
"""

from __future__ import annotations

from django.urls import path

from apps.applications.presentation.api.v1.orders.views import (
    ApplicationCancellationView,
    ApplicationCollectionView,
    ApplicationConsentsView,
    ApplicationDetailView,
    ApplicationEducationalOrganizationView,
    ApplicationPaymentRequestView,
    ApplicationPaymentView,
    ApplicationPlacementView,
    ApplicationReceiptView,
    ApplicationServiceDetailView,
    ApplicationServicesView,
    ApplicationSubmissionDetailView,
    ApplicationSubmissionsView,
)

app_name = "applications"

urlpatterns = [
    path("applications", ApplicationCollectionView.as_view(), name="collection"),
    path("applications/<str:application_id>", ApplicationDetailView.as_view(), name="detail"),
    path("applications/<str:application_id>/submissions", ApplicationSubmissionsView.as_view(), name="submissions"),
    path("applications/<str:application_id>/submissions/<str:submission_id>", ApplicationSubmissionDetailView.as_view(), name="submission-detail"),
    path("applications/<str:application_id>/services", ApplicationServicesView.as_view(), name="services"),
    path("applications/<str:application_id>/services/<str:service_id>", ApplicationServiceDetailView.as_view(), name="service-detail"),
    path("applications/<str:application_id>/consents", ApplicationConsentsView.as_view(), name="consents"),
    path(
        "applications/<str:application_id>/educational-organization",
        ApplicationEducationalOrganizationView.as_view(),
        name="educational-organization",
    ),
    path("applications/<str:application_id>/placement", ApplicationPlacementView.as_view(), name="placement"),
    path("applications/<str:application_id>/payment-request", ApplicationPaymentRequestView.as_view(), name="payment-request"),
    path("applications/<str:application_id>/payment", ApplicationPaymentView.as_view(), name="payment"),
    path("applications/<str:application_id>/receipt", ApplicationReceiptView.as_view(), name="receipt"),
    path("applications/<str:application_id>/cancellation", ApplicationCancellationView.as_view(), name="cancellation"),
]
