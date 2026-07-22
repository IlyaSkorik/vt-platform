"""Celery tasks for the Applications bounded context (autodiscovered by name).

Tasks are thin: they resolve the framework-free use case from the composition root
and run it. Business logic lives in the application layer, never here.
"""

from __future__ import annotations

from celery import shared_task


@shared_task(name="applications.auto_cancel_unpaid_application")
def auto_cancel_unpaid_application(application_id: str) -> None:
    """Auto-cancel an order whose payment receipt never arrived within the window.

    A no-op if a receipt was attached, the order was paid, or it already left a
    cancellable state (the handler re-checks), so a late or duplicate run is safe.
    """
    from apps.applications.presentation.api.v1.orders.composition import build_auto_cancel_unpaid_handler

    build_auto_cancel_unpaid_handler().handle(application_id)
