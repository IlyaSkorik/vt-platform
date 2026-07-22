"""DB-backed tests for the periodic unpaid-order auto-cancel sweep (Celery Beat)."""

from __future__ import annotations

from datetime import timedelta

import pytest
from django.utils import timezone

pytestmark = pytest.mark.django_db


def _application(*, status: str, submitted_delta_hours: float | None, receipt: dict | None = None):
    from apps.applications.infrastructure.models import ApplicationModel
    from apps.applications.infrastructure.models.base import uuid7

    submitted_at = (
        timezone.now() - timedelta(hours=submitted_delta_hours) if submitted_delta_hours is not None else None
    )
    return ApplicationModel.objects.create(
        competition_id=uuid7(),
        applicant_id=uuid7(),
        status=status,
        submitted_at=submitted_at,
        payment_receipt=receipt,
        total_price=None,
    )


def test_sweep_cancels_overdue_unpaid_application(settings) -> None:
    from apps.applications.tasks import sweep_unpaid_applications

    settings.APPLICATION_PAYMENT_WINDOW_HOURS = 48
    app = _application(status="SUBMITTED", submitted_delta_hours=49)

    sweep_unpaid_applications()

    app.refresh_from_db()
    assert app.status == "CANCELLED"


def test_sweep_keeps_application_with_receipt(settings) -> None:
    from apps.applications.tasks import sweep_unpaid_applications

    settings.APPLICATION_PAYMENT_WINDOW_HOURS = 48
    app = _application(
        status="SUBMITTED",
        submitted_delta_hours=49,
        receipt={"file_reference": "receipt.pdf", "uploaded_at": timezone.now().isoformat()},
    )

    sweep_unpaid_applications()

    app.refresh_from_db()
    assert app.status == "SUBMITTED"


def test_sweep_keeps_application_within_window(settings) -> None:
    from apps.applications.tasks import sweep_unpaid_applications

    settings.APPLICATION_PAYMENT_WINDOW_HOURS = 48
    app = _application(status="SUBMITTED", submitted_delta_hours=1)

    sweep_unpaid_applications()

    app.refresh_from_db()
    assert app.status == "SUBMITTED"
