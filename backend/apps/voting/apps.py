"""Django AppConfig for the Voting bounded context.

Voting owns the **audience's verdict**: a ballot, the nominees on it, and the
votes cast by people in the hall. It is the one context on this platform that is
deliberately usable on its own.

That is the point of it. A festival that is not ready to move onto the platform
still needs an audience vote, and it must be able to have one without first
creating a competition, entering a taxonomy, and collecting applications. So a
ballot belongs to an *organization*, and its link to a competition is optional
(``competition_id`` may be null).

What makes that work without becoming two features is that a nominee carries its
own display data — name, act, photo — rather than a reference to somebody
else's. When the festival does live here, the list is seeded from the programme
in one step; when it does not, the same list is typed in or imported from Excel.
Everything downstream — the voting page, the count, the results — reads the
ballot's own rows and cannot tell the two apart.

Votes are **not** part of the ballot aggregate. There are thousands of them, they
are append-only, and loading them into memory to accept one more would be absurd;
they have their own table and their own repository (ARCH-001 §13.4).
"""

from __future__ import annotations

from django.apps import AppConfig


class VotingConfig(AppConfig):
    """App configuration for the Voting bounded context."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.voting"
    label = "voting"
    verbose_name = "Voting"

    def ready(self) -> None:
        """Register the ORM models and admin, which live under ``infrastructure/``.

        Models and admin are deliberately not in the default ``<app>/models.py`` /
        ``<app>/admin.py`` but under ``infrastructure/`` (ARCH-001 §7.2, §14), so
        Django's automatic discovery does not find them — import them here to
        register the models with the app registry and their admin bindings.
        """
        from apps.voting.infrastructure import admin, models  # noqa: F401
