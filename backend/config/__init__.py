"""VT Platform backend project package.

Ensures the Celery application is imported when Django starts so shared_task
autodiscovery works (ARCH-001 §7.5).
"""

from .celery import app as celery_app

__all__ = ("celery_app",)
