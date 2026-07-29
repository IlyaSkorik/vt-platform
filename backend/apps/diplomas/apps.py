"""Django AppConfig for the Diplomas bounded context.

Diplomas is a standalone organizer workspace (not a competition setting): it owns
the reusable diploma **template library** and the **assignment** mechanism that
binds a template to a (competition, nomination) pair. Templates are self-contained
entities — one template may be assigned across many competitions and nominations.
"""

from __future__ import annotations

from django.apps import AppConfig


class DiplomasConfig(AppConfig):
    """App configuration for the Diplomas bounded context."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.diplomas"
    label = "diplomas"
    verbose_name = "Diplomas"

    def ready(self) -> None:
        """Register the ORM models and admin, which live under ``infrastructure/``.

        Models and admin are deliberately not in the default ``<app>/models.py`` /
        ``<app>/admin.py`` but under ``infrastructure/`` (ARCH-001 §7.2, §14), so
        Django's automatic discovery does not find them - import them here to
        register the models with the app registry and their admin bindings.
        """
        from apps.diplomas.infrastructure import admin, models  # noqa: F401

        # Tell the PDF font registry where uploaded faces live. Injected here rather than
        # imported inside the registry: that module is loaded by the renderer, including in a
        # Celery worker, and a direct import of the repository would put a database
        # dependency inside the one component that must work with nothing else wired up.
        from apps.diplomas.infrastructure.fonts import DjangoFontFaceRepository, FontFileCache
        from apps.diplomas.infrastructure.pdf.fonts import set_uploaded_face_source

        # `materialize` is what makes an uploaded font work on object storage: reportlab embeds
        # a font by opening a file, and in production the file is in S3. It is called for the
        # one face a render draws, not for the whole library.
        cache = FontFileCache()
        set_uploaded_face_source(
            DjangoFontFaceRepository().faces,
            materialize=lambda face: cache.local_path(reference=face.reference, name=face.registered_name),
        )
