"""``DjangoPrintPackageWorkspace`` — the infra side of print-package generation.

Loads a template's fields and backing PDF, renders diploma PDFs (reportlab/pypdf),
and stores the per-diploma PDFs and the final ZIP in ``default_storage`` - a ``/media/…``
path locally, an object in a bucket in a deployment, and the reference it hands back is
whatever that storage says the file's URL is.

Keys here carry an unguessable token, which is what keeps a public-read bucket safe: a
diploma's number and its competition's id are both public, so without it the whole
registry could be walked by counting.
"""

from __future__ import annotations

import hashlib
import hmac
import shutil
import tempfile
import uuid
import zipfile
from collections.abc import Sequence
from pathlib import PurePosixPath
from urllib.parse import unquote

from django.conf import settings
from django.core.files.base import ContentFile, File
from django.core.files.storage import Storage, default_storage, storages
from django.utils.text import slugify

from apps.diplomas.application.interfaces import TemplateAssets
from apps.diplomas.domain.value_objects import DiplomaSnapshot
from apps.diplomas.infrastructure.models import TemplateDocumentModel
from apps.diplomas.infrastructure.pdf.qr import verification_url
from apps.diplomas.infrastructure.pdf.renderer import render_diploma_pdf, render_place_sheet_pdf
from apps.diplomas.presentation.api.v1.diplomas import composition

__all__ = ["DjangoPrintPackageWorkspace", "storage_key_of"]

#: An ASCII key that no real file uses, minted only to find out what a reference looks
#: like in front of the key. Never read or written.
_BASE_PROBE_KEY = "__reference_base_probe__"

#: How much of an archive is held in memory before the spool rolls over to disk. Small
#: bundles never touch the filesystem; a festival's full diploma set always does.
_ARCHIVE_SPOOL_BYTES = 4 * 1024 * 1024

#: Read size when copying one document into the archive.
_COPY_CHUNK_BYTES = 256 * 1024

#: Moves both archive keys when it is bumped, and nothing else.
#:
#: The headers are fixed from now on, but a browser that already cached the old archive
#: URL under the year-long ``immutable`` was told it never has to ask again, and it will
#: not — the fix cannot reach it. A different key is a different URL, which is the only
#: thing that does. One orphaned archive per competition stays behind at the old key;
#: bump this only when there is a reason as good as that one.
_ARCHIVE_KEY_SALT = "2"


def storage_key_of(reference: str) -> str:
    """Turn a stored reference back into the storage key it was minted from.

    The inverse of :func:`_reference`, and it has to work for both shapes a reference
    takes: ``/media/diplomas/…`` on a filesystem and an absolute bucket URL in a
    deployment. Asking the storage for its own base rather than matching on ``/media/``
    keeps the two symmetric.

    The unquoting is the part that matters: a reference is a URL, so a document named
    after "Петрова Ольга" arrives percent-encoded, while the object itself is stored
    under the name as written. Keys in this module come from slugify, uuids and diploma
    numbers, so there is no literal ``%`` for this to misread.
    """
    base = _reference_base()
    trimmed = reference[len(base) :] if base and reference.startswith(base) else reference.lstrip("/")
    return unquote(trimmed)


def _reference_base() -> str:
    """Everything a reference carries in front of the key.

    Derived by minting a URL for a sentinel key and cutting it off, rather than asking for
    the URL of an empty one: S3 rejects a zero-length key outright, so the obvious version
    of this works on a filesystem and raises in a deployment.
    """
    probe = default_storage.url(_BASE_PROBE_KEY)
    return probe[: probe.index(_BASE_PROBE_KEY)] if _BASE_PROBE_KEY in probe else ""


def _reference(key: str) -> str:
    """The URL a stored file is reachable at - whatever the configured storage says."""
    return default_storage.url(key)


def _replaceable() -> Storage:
    """The storage to write a key that will be written again through.

    Same bucket, same keys, same URLs - it differs only in the ``Cache-Control`` it
    puts on the object. Everything written here is written *back* sooner or later: a
    corrected protocol re-renders a diploma onto its own key, and every print run
    replaces the competition's archive. The default storage promises a year of
    ``immutable`` for those URLs, which is exactly how a browser answers the next
    download out of its own disk cache - reproducibly in Opera, and sooner or later
    everywhere - and hands the organizer the archive from the previous run.

    Reading, deleting and minting a URL still go through ``default_storage``: the two
    instances address the same objects, and only the write carries the header.
    """
    return storages["replaceable"]


def _unguessable(*parts: str) -> str:
    """A short, stable token that cannot be derived from the parts without the secret.

    Diploma keys are otherwise perfectly predictable - a competition id that appears in
    public URLs and a diploma number that increments - so in a public-read bucket the
    whole registry could be walked by counting. This makes each key unguessable while
    keeping it *stable*: regenerating a diploma lands on the same key and replaces the
    file, rather than leaving an orphan behind at a key nobody can compute again.

    Keyed on ``SECRET_KEY``, so rotating it changes where future files are written.
    Already-issued diplomas keep working: their reference is stored in the database and
    the object it points at is untouched.
    """
    digest = hmac.new(settings.SECRET_KEY.encode(), "/".join(parts).encode(), hashlib.sha256)
    return digest.hexdigest()[:16]


class DjangoPrintPackageWorkspace:
    """Concrete ``PrintPackageWorkspace`` over Django storage + the PDF renderer."""

    def load_template(self, template_id: uuid.UUID) -> TemplateAssets | None:
        document = TemplateDocumentModel.objects.filter(template__id=template_id, deleted_at__isnull=True).order_by("-created_at").first()
        if document is None:
            return None
        key = storage_key_of(document.file_reference)
        if not default_storage.exists(key):
            return None
        with default_storage.open(key, "rb") as handle:
            backing_pdf = handle.read()
        layout = composition.get_template_layout(str(template_id))
        return TemplateAssets(fields=list(layout["fields"]), backing_pdf=backing_pdf, name=document.template.name)

    def render(
        self,
        *,
        assets: TemplateAssets,
        snapshot: DiplomaSnapshot,
        number: str,
        verification_token: str,
    ) -> bytes:
        # The public verification domain is configuration, so the URL is built here
        # (infrastructure) rather than passed down from the application service. An
        # empty token means an unverifiable kind — no URL, so the renderer's QR
        # block prints nothing even if one were left in the layout.
        return render_diploma_pdf(
            fields=assets.fields,
            backing_pdf=assets.backing_pdf,
            snapshot=snapshot,
            number=number,
            verification_url=verification_url(verification_token) if verification_token else None,
        )

    def render_place_sheet(self, *, assets: TemplateAssets, degree: str) -> bytes | None:
        return render_place_sheet_pdf(fields=assets.fields, backing_pdf=assets.backing_pdf, degree=degree)

    def store_pdf(self, *, competition_id: uuid.UUID, number: str, data: bytes) -> str:
        # The number stays in the key - an organizer looking at the bucket should be able
        # to see which diploma this is - but the token in front of it is what stops the
        # registry from being enumerated by counting numbers up from one.
        token = _unguessable("print", str(competition_id), number)
        key = f"diplomas/print/{competition_id}/{token}/{number}.pdf"
        if default_storage.exists(key):
            default_storage.delete(key)
        _replaceable().save(key, ContentFile(data))
        return _reference(key)

    def store_official_pdf(self, *, competition_id: uuid.UUID, number: str, data: bytes) -> str:
        # The participant's own copy, kept in its own tree rather than overwriting the
        # print copy: the two differ by the degree, both are legitimately wanted at once
        # (an organizer prints blanks before the ceremony and hands out the awarded ones
        # after), and one key for both would mean publishing the results destroyed the
        # print set. Same unguessable prefix scheme, with its own salt.
        token = _unguessable("official", str(competition_id), number)
        key = f"diplomas/official/{competition_id}/{token}/{number}.pdf"
        if default_storage.exists(key):
            # Re-rendered by a corrected protocol: the participant's URL must not change,
            # so the object behind it is replaced in place.
            default_storage.delete(key)
        _replaceable().save(key, ContentFile(data))
        return _reference(key)

    def store_document_pdf(
        self,
        *,
        competition_id: uuid.UUID,
        document_type: str,
        submission_id: uuid.UUID,
        data: bytes,
        recipient: str = "",
    ) -> str:
        # Keyed by kind, performance and recipient: these documents have no number,
        # and a per-teacher kind issues several per performance — without the
        # recipient in the key each would overwrite the last. They stay out of the
        # diploma print tree so the two are never bundled together.
        #
        # The recipient is slugified rather than hashed because the participant
        # downloads the file by this name, and "blagodarnost-petrova-olga.pdf" is
        # worth more to them than an opaque digest. Unicode is kept, so Cyrillic
        # names survive.
        suffix = f"-{slugify(recipient, allow_unicode=True)}" if recipient.strip() else ""
        token = _unguessable("documents", str(competition_id), document_type.lower(), str(submission_id), suffix)
        key = f"diplomas/documents/{competition_id}/{document_type.lower()}/{token}/{submission_id}{suffix}.pdf"
        if default_storage.exists(key):
            default_storage.delete(key)
        _replaceable().save(key, ContentFile(data))
        return _reference(key)

    def store_zip(self, *, competition_id: uuid.UUID, items: list[tuple[str, str]], extras: Sequence[tuple[str, bytes]] = ()) -> str:
        # The archive is the whole set in one file, so it is the most valuable object in
        # the bucket and gets the same unguessable token as the diplomas inside it.
        #
        # ``_ARCHIVE_KEY_SALT`` is what moves the archive off the URL browsers were told
        # to keep for a year — see its comment. Only the token changes; the path around
        # it reads the same.
        token = _unguessable("print-zip", _ARCHIVE_KEY_SALT, str(competition_id))
        return self._store_archive(key=f"diplomas/print/{competition_id}/{token}/Diplomas.zip", items=items, extras=extras)

    def store_documents_zip(self, *, competition_id: uuid.UUID, document_type: str, items: list[tuple[str, str]]) -> str:
        # Named after the kind ("ThankYou.zip"), because the file name is what the
        # organizer sees in the downloads folder next to the diplomas archive. Kept
        # inside the kind's own tree, so it neither collides with the diploma set
        # nor with another kind's bundle.
        kind = document_type.lower()
        filename = "".join(part.capitalize() for part in document_type.split("_"))
        token = _unguessable("documents-zip", _ARCHIVE_KEY_SALT, str(competition_id), kind)
        return self._store_archive(key=f"diplomas/documents/{competition_id}/{kind}/{token}/{filename}.zip", items=items)

    @staticmethod
    def _store_archive(*, key: str, items: list[tuple[str, str]], extras: Sequence[tuple[str, bytes]] = ()) -> str:
        """ZIP up ``(arcname, reference)`` pairs at ``key``, replacing any previous.

        Streamed on purpose, member by member and chunk by chunk, through a spool that
        rolls over to disk. One archive holds every diploma of a competition, and every
        diploma is a full copy of the template it was rendered over - so a festival with
        3 000 participants and a 2 MB template produces a ~6 GB archive. Built in memory,
        that alone would exhaust a server twice over, and the ``getvalue()`` it used to
        end with doubled it again. Peak memory is now one chunk plus the spool threshold,
        whatever the tirage.

        ``extras`` are written from memory instead of copied out of storage. They are
        not streamed because they cannot grow with the tirage: the place sheets are a
        fixed handful per template, each a blank page with one line of text on it.
        """
        with tempfile.SpooledTemporaryFile(max_size=_ARCHIVE_SPOOL_BYTES) as spool:
            with zipfile.ZipFile(spool, "w", zipfile.ZIP_DEFLATED) as archive:
                for arcname, reference in items:
                    storage_key = storage_key_of(reference)
                    if not default_storage.exists(storage_key):
                        continue
                    with default_storage.open(storage_key, "rb") as source, archive.open(arcname, "w") as target:
                        shutil.copyfileobj(source, target, length=_COPY_CHUNK_BYTES)
                for arcname, data in extras:
                    archive.writestr(arcname, data)
            spool.seek(0)
            if default_storage.exists(key):
                default_storage.delete(key)
            # A file object rather than bytes: the storage reads it in chunks, so the
            # archive is never resident in full - locally or on the way to a bucket.
            _replaceable().save(key, File(spool, name=PurePosixPath(key).name))
        return _reference(key)
