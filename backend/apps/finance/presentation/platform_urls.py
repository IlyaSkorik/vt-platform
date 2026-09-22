"""The platform operator's routes into the Finance context.

Kept beside the context that owns the data rather than in ``apps.platform``: the
console borrows this context's use cases, it does not reimplement them. There is
no non-platform route file here on purpose — the expense book has one audience.
"""

from __future__ import annotations

from django.urls import path

from .api.v1.platform_views import PlatformExpenseCollectionView, PlatformExpenseDetailView

app_name = "platform_finance"

urlpatterns = [
    path("platform/expenses", PlatformExpenseCollectionView.as_view(), name="collection"),
    path("platform/expenses/<str:expense_id>", PlatformExpenseDetailView.as_view(), name="detail"),
]
