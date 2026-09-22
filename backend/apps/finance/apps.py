"""Django AppConfig for the Finance bounded context.

Finance owns **the platform's own money**, as opposed to the organizers'. What an
organization charges a participant is theirs and lives in Applications; what the
platform is owed for that is derived from their terms and lives in the console's
projection. Neither is typed in by anybody. What the platform *spends* is — a
server bill, a contractor, an advertisement — and that is what this context holds.

Two decisions shape it.

**A cost may name an organization, or name none.** Attributed to a client, it sits
against the commission that client pays and answers "are we in the black on this
one?". Attributed to nobody, it is the platform's own overhead — and forcing such
a cost onto some organization would quietly make that organization's line a lie.

**The arithmetic lives next door, not here.** Income minus expenses is computed in
the operator's dashboard projection, which already holds the commission figures.
This context does not fetch them: an expense book that knew what the platform
earned would be a second, quieter copy of the billing rules.
"""

from __future__ import annotations

from django.apps import AppConfig


class FinanceConfig(AppConfig):
    """App configuration for the Finance bounded context."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.finance"
    label = "finance"
    verbose_name = "Finance"

    def ready(self) -> None:
        """Register the ORM models and admin, which live under ``infrastructure/``.

        Models and admin are deliberately not in the default ``<app>/models.py`` /
        ``<app>/admin.py`` but under ``infrastructure/`` (ARCH-001 §7.2, §14), so
        Django's automatic discovery does not find them — import them here to
        register the models with the app registry and their admin bindings.
        """
        from apps.finance.infrastructure import admin, models  # noqa: F401
