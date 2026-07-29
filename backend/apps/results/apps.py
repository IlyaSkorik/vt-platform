"""Django AppConfig for the Results bounded context.

Results owns **what the jury decided, and the act of making it public**. Its aggregate is
the protocol: one nomination's table of acts in the order they performed, each carrying the
award it was given, plus the revision of those results that is currently published.

Three boundaries define this context, and each is worth naming:

* it references Applications and Competitions **by id only**, and reads their names live, so
  a corrected surname shows on the protocol at once;
* it is *seeded* from Programs and then owns its copy, so a running order rearranged after
  the ceremony cannot move a result;
* it is the **only** context that writes ``award.degree`` into Diplomas, and it does so at
  exactly one moment - publication - because before that there is no result to put on a
  document.

Distinct from Judging, which will own scoring and how a decision is reached. Results owns
the decision once it has been reached (DATA-001 §3.10).
"""

from __future__ import annotations

from django.apps import AppConfig


class ResultsConfig(AppConfig):
    """App configuration for the Results bounded context."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.results"
    label = "results"
    verbose_name = "Results"

    def ready(self) -> None:
        """Register the ORM models and admin, which live under ``infrastructure/``.

        Models and admin are deliberately not in the default ``<app>/models.py`` /
        ``<app>/admin.py`` but under ``infrastructure/`` (ARCH-001 §7.2, §14), so Django's
        automatic discovery does not find them - import them here to register the models
        with the app registry and their admin bindings.
        """
        from apps.results.infrastructure import admin, models  # noqa: F401
