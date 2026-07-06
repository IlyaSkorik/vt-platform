"""Celery application for the VT Platform backend.

Configures the distributed task queue used for asynchronous work — media
post-processing, notification fan-out, PDF generation, scheduled deadline
transitions, and analytics projections (ARCH-001 §7.5). Broker and result
backend are Redis, read from the typed settings via Django settings.

No tasks are defined during bootstrap; task modules are autodiscovered from
each bounded context later.
"""

from __future__ import annotations

import os

from celery import Celery

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.development")

app = Celery("vt_platform")
app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks()
