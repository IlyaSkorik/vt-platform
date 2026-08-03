"""DB-backed tests for the periodic unpaid-order auto-cancel sweep (Celery Beat)."""

from __future__ import annotations

from datetime import timedelta
from typing import TYPE_CHECKING, Any

import pytest
from django.utils import timezone

if TYPE_CHECKING:
    from pytest_django.fixtures import SettingsWrapper

    from apps.applications.infrastructure.models import ApplicationModel

pytestmark = pytest.mark.django_db


def _application(*, status: str, submitted_delta_hours: float | None, receipts: list[dict[str, Any]] | None = None) -> ApplicationModel:
    from apps.applications.infrastructure.models import ApplicationModel
    from apps.applications.infrastructure.models.base import uuid7

    submitted_at = timezone.now() - timedelta(hours=submitted_delta_hours) if submitted_delta_hours is not None else None
    return ApplicationModel.objects.create(
        competition_id=uuid7(),
        applicant_id=uuid7(),
        status=status,
        submitted_at=submitted_at,
        payment_receipts=receipts or [],
        total_price=None,
    )


def _receipt(reference: str) -> dict[str, Any]:
    from apps.applications.infrastructure.models.base import uuid7

    return {"id": str(uuid7()), "file_reference": reference, "uploaded_at": timezone.now().isoformat()}


def test_sweep_cancels_overdue_unpaid_application(settings: SettingsWrapper) -> None:
    from apps.applications.tasks import sweep_unpaid_applications

    settings.APPLICATION_PAYMENT_WINDOW_HOURS = 48
    app = _application(status="SUBMITTED", submitted_delta_hours=49)

    sweep_unpaid_applications()

    app.refresh_from_db()
    assert app.status == "CANCELLED"


def test_sweep_keeps_application_with_receipt(settings: SettingsWrapper) -> None:
    from apps.applications.tasks import sweep_unpaid_applications

    settings.APPLICATION_PAYMENT_WINDOW_HOURS = 48
    app = _application(status="SUBMITTED", submitted_delta_hours=49, receipts=[_receipt("receipt.pdf")])

    sweep_unpaid_applications()

    app.refresh_from_db()
    assert app.status == "SUBMITTED"


def test_sweep_keeps_application_paid_in_several_transfers(settings: SettingsWrapper) -> None:
    """One of several part-payments is still proof that payment started."""
    from apps.applications.tasks import sweep_unpaid_applications

    settings.APPLICATION_PAYMENT_WINDOW_HOURS = 48
    app = _application(
        status="SUBMITTED",
        submitted_delta_hours=49,
        receipts=[_receipt("first-half.pdf"), _receipt("second-half.pdf")],
    )

    sweep_unpaid_applications()

    app.refresh_from_db()
    assert app.status == "SUBMITTED"


def test_sweep_keeps_application_within_window(settings: SettingsWrapper) -> None:
    from apps.applications.tasks import sweep_unpaid_applications

    settings.APPLICATION_PAYMENT_WINDOW_HOURS = 48
    app = _application(status="SUBMITTED", submitted_delta_hours=1)

    sweep_unpaid_applications()

    app.refresh_from_db()
    assert app.status == "SUBMITTED"
