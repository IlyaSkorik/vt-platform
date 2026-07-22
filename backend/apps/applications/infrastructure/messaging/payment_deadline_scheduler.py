"""``CeleryPaymentDeadlineScheduler`` — defers the unpaid-order auto-cancellation.

Concrete adapter for the :class:`~apps.applications.application.interfaces.
PaymentDeadlineScheduler` port. It enqueues the ``auto_cancel_unpaid_application``
Celery task to run at the payment deadline; the task re-checks the order state, so
a receipt attached before then makes it a no-op.

Under eager settings (the test suite runs tasks synchronously) scheduling is
skipped — otherwise a 48-hour timer would fire immediately during a submit test and
cancel the order it just created. The deferred behaviour is covered by unit-testing
:class:`AutoCancelUnpaidApplicationHandler` directly.
"""

from __future__ import annotations

from datetime import datetime

from django.conf import settings

__all__ = ["CeleryPaymentDeadlineScheduler"]


class CeleryPaymentDeadlineScheduler:
    """Payment-deadline scheduler (``PaymentDeadlineScheduler`` port) over Celery."""

    def schedule_auto_cancel(self, *, application_id: str, run_at: datetime) -> None:
        if getattr(settings, "CELERY_TASK_ALWAYS_EAGER", False):
            return
        from apps.applications.tasks import auto_cancel_unpaid_application

        auto_cancel_unpaid_application.apply_async((application_id,), eta=run_at)
