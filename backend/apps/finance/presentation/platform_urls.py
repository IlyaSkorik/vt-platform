"""The platform operator's routes into the Finance context.

Kept beside the context that owns the data rather than in ``apps.platform``: the
console borrows this context's use cases, it does not reimplement them. There is
no non-platform route file here on purpose — these books have one audience.
"""

from __future__ import annotations

from django.urls import path

from .api.v1.platform_views import (
    PlatformCommissionPaymentCollectionView,
    PlatformCommissionPaymentDetailView,
    PlatformExpenseCollectionView,
    PlatformExpenseDetailView,
)

app_name = "platform_finance"

urlpatterns = [
    path("platform/expenses", PlatformExpenseCollectionView.as_view(), name="collection"),
    path("platform/expenses/<str:expense_id>", PlatformExpenseDetailView.as_view(), name="detail"),
    # The other side of the books: commission that actually arrived. A ledger of its
    # own rather than an expense with a negative sign — the two are filtered, totalled
    # and read separately, and one table with a sign column would make every read of
    # either one remember to exclude the other.
    path("platform/commission-payments", PlatformCommissionPaymentCollectionView.as_view(), name="commission-payments"),
    path(
        "platform/commission-payments/<str:payment_id>",
        PlatformCommissionPaymentDetailView.as_view(),
        name="commission-payment-detail",
    ),
]
