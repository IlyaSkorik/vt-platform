"""Django AppConfig for the Reviews bounded context.

Reviews owns **what the audience said afterwards**: a page an organizer prints a
QR of onto a banner, and the notes people leave through it — a few words, a name
if they feel like giving one, sometimes a photograph from the hall.

Three decisions shape the whole context.

**The page belongs to the organization, not to a festival.** A banner is printed
once and stands at every event the organizer runs; a link that changed per
festival would be a new banner each season. The festival is instead *named on the
review* — the person picks it from a short list, or does not, and a review that
names nothing is still a review.

**Nothing here is published.** The notes are read in the organizer's workspace and
in the platform operator's console, and nowhere else. That is why this context has
no moderation states: there is no audience to protect from an unapproved note, and
a workflow that exists only to gate an empty stage is a workflow nobody runs.

**The consent is part of the record, not a checkbox that was on the page.** A
review carries the version of the wording its author accepted and the instant they
accepted it (LEGAL-001 §13.3), and a :class:`Review` cannot be constructed without
one. The alternative — trusting that the form had the box — is a legal basis that
lives in a template rather than in the database.
"""

from __future__ import annotations

from django.apps import AppConfig


class ReviewsConfig(AppConfig):
    """App configuration for the Reviews bounded context."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.reviews"
    label = "reviews"
    verbose_name = "Reviews"

    def ready(self) -> None:
        """Register the ORM models and admin, which live under ``infrastructure/``.

        Models and admin are deliberately not in the default ``<app>/models.py`` /
        ``<app>/admin.py`` but under ``infrastructure/`` (ARCH-001 §7.2, §14), so
        Django's automatic discovery does not find them — import them here to
        register the models with the app registry and their admin bindings.
        """
        from apps.reviews.infrastructure import admin, models  # noqa: F401
