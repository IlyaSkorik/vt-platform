"""Django AppConfig for the Judging bounded context.

Judging owns **how a festival decides**: the criteria a jury is given, the panel that
fills them in, the marks themselves, and the award scale that turns a total into a
result with a name on it.

It is switchable per festival. A competition set to ``PROTOCOLS`` never creates a
scorecard here — its jury works on paper and somebody types the outcome into a protocol
— and every scoring use case refuses outright rather than quietly accepting marks
nobody will read. What such a festival *does* use from this context is the award scale,
because that is the vocabulary its protocols are written in.

Two aggregates that could have been one are deliberately apart: an act's open/closed
state, and each judge's sheet. Five judges press send within the same second in a hall,
and a single aggregate would make four of those writes lose a concurrency race on venue
wifi. See the module docstring of ``domain/entities.py``.
"""

from __future__ import annotations

from django.apps import AppConfig


class JudgingConfig(AppConfig):
    """App configuration for the Judging bounded context."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.judging"
    label = "judging"
    verbose_name = "Judging"

    def ready(self) -> None:
        """Register the ORM models and admin, which live under ``infrastructure/``.

        Models and admin are deliberately not in the default ``<app>/models.py`` /
        ``<app>/admin.py`` but under ``infrastructure/`` (ARCH-001 §7.2, §14), so
        Django's automatic discovery does not find them — import them here to
        register the models with the app registry and their admin bindings.
        """
        from apps.judging.infrastructure import admin, models  # noqa: F401
