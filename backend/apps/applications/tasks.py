"""Celery tasks for the Applications bounded context (autodiscovered by name).

Tasks are thin: they resolve the framework-free use case from the composition root
and run it. Business logic lives in the application layer, never here.
"""

from __future__ import annotations

from datetime import timedelta

from celery import shared_task
from django.conf import settings
from django.utils import timezone


@shared_task(name="applications.sweep_unpaid_applications")  # type: ignore[untyped-decorator]  # celery ships no stubs
def sweep_unpaid_applications() -> None:
    """Auto-cancel submitted orders whose payment receipt never arrived in time.

    A durable, restart-proof alternative to per-order ETA jobs: Celery Beat runs this
    periodically, it recomputes the overdue set from the database (orders submitted
    longer than the payment window ago, still awaiting payment, with no receipt), and
    cancels each through the idempotent auto-cancel use case. Nothing is lost if the
    web app, worker, or beat restarts, because the source of truth is the DB.
    """
    from apps.applications.infrastructure.models import ApplicationModel
    from apps.applications.presentation.api.v1.orders.composition import build_auto_cancel_unpaid_handler

    cutoff = timezone.now() - timedelta(hours=settings.APPLICATION_PAYMENT_WINDOW_HOURS)
    # "No receipt" is now an empty list, not a null column: one receipt of several
    # is still proof that payment started, so any entry at all spares the order.
    overdue_ids = list(
        ApplicationModel.objects.filter(
            deleted_at__isnull=True,
            status__in=["SUBMITTED", "WAITING_PAYMENT"],
            payment_receipts=[],
            submitted_at__isnull=False,
            submitted_at__lte=cutoff,
        ).values_list("id", flat=True)
    )
    if not overdue_ids:
        return
    handler = build_auto_cancel_unpaid_handler()
    for application_id in overdue_ids:
        handler.handle(str(application_id))


@shared_task(name="applications.notify_application_revisions")  # type: ignore[untyped-decorator]  # celery ships no stubs
def notify_application_revisions() -> int:
    """Tell organizers about orders that were edited after being submitted.

    An order stays editable while registration is open, so an applicant can change a
    performance the organizer has already read. Each such edit is journalled as it
    happens; this run folds every pending edit of an order into one letter, then marks
    those journal rows reported.

    Durable and re-runnable for the same reason as the sweep above: the journal in the
    database is the source of truth, so nothing is lost to a restart, and a row already
    stamped as reported is never sent again. Orders still being edited are skipped by
    the use case's quiet period and picked up by a later run.
    """
    from apps.applications.presentation.api.v1.orders.composition import build_notify_revisions_handler

    return int(build_notify_revisions_handler().handle())
