"""Bootstrap smoke tests.

Verify the infrastructure foundation loads correctly: settings import, all
bounded-context apps register, and the typed configuration is available. These
assert structure only — no business behaviour exists yet.

Written as a ``SimpleTestCase`` so they are discovered by both ``pytest`` and
``python manage.py test`` (Django's unittest runner). They require no database.
"""

from __future__ import annotations

from typing import cast

from django.apps import apps
from django.conf import settings
from django.test import SimpleTestCase

BOUNDED_CONTEXTS = [
    "identity",
    "participants",
    "institutions",
    "competitions",
    "applications",
    "performances",
    "judging",
    "results",
    "finance",
    "notifications",
    "analytics",
    "audit",
]


class BootstrapFoundationTests(SimpleTestCase):
    """Structural assertions about the backend bootstrap."""

    def test_all_bounded_contexts_are_installed(self) -> None:
        installed_labels = {config.label for config in apps.get_app_configs()}
        for context in BOUNDED_CONTEXTS:
            self.assertIn(context, installed_labels, f"missing bounded context: {context}")

    def test_localization_is_utc_and_russian(self) -> None:
        self.assertEqual(settings.TIME_ZONE, "UTC")
        self.assertTrue(settings.USE_TZ)
        self.assertEqual(settings.LANGUAGE_CODE, "ru")

    def test_jwt_authentication_is_configured(self) -> None:
        auth_classes = cast(
            "tuple[str, ...]",
            settings.REST_FRAMEWORK["DEFAULT_AUTHENTICATION_CLASSES"],
        )
        self.assertTrue(any("JWTAuthentication" in cls for cls in auth_classes))

    def test_typed_settings_are_loaded(self) -> None:
        from config.settings.env import get_settings

        typed = get_settings()
        self.assertEqual(typed.time_zone, "UTC")
        self.assertEqual(typed.language_code, "ru")
