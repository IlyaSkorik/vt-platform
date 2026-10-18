"""One letter per teacher per genre.

An addressed document used to be identified by its performance, so a teacher who
entered five acts in one genre held five thank-you letters. It is identified by
``(competition, genre, recipient)`` from here on, which needs the genre on the
row — and needs the duplicates already in the table gone before the constraint
that enforces it can be added.

Three steps, in order: add the column, fill it in and collapse the duplicates,
then add the constraint. The data step is reversible in the only sense that
matters — it soft-deletes rather than deletes, so a festival that already handed
out one of the discarded letters still has the row behind its URL.
"""

from __future__ import annotations

from django.db import migrations, models


def _recipient_key(name: str) -> str:
    """How two recipient names are compared for sameness.

    Mirrors ``apps.diplomas.application.issued_documents._recipient_key``: the
    names were typed by applicants, so the same teacher reaches the table with
    different spacing and case on different entries.
    """
    return " ".join(str(name or "").split()).casefold()


def fill_category_and_collapse_duplicates(apps, schema_editor):
    """Backfill ``category_id`` from each document's entry, then keep one per teacher.

    The genre comes from the live submission rather than from the frozen snapshot,
    because the snapshot stores the genre's *title* and the identity needs its id.
    A document whose submission is gone keeps a null genre: it can no longer be
    placed in one, and the partial constraint below simply never applies to it —
    Postgres treats a null as distinct from every other, including another null.

    The survivor of a duplicate set is the **oldest**: it is the one whose PDF has
    been in the organizer's archive and in a cabinet the longest, so discarding it
    in favour of a newer row would be the one choice that could break a link
    somebody already holds.
    """
    IssuedDocumentModel = apps.get_model("diplomas", "IssuedDocumentModel")
    SubmissionModel = apps.get_model("applications", "SubmissionModel")

    rows = list(
        IssuedDocumentModel.objects.filter(deleted_at__isnull=True).order_by("created_at").values("id", "submission_id", "document_type", "recipient")
    )
    if not rows:
        return

    category_of = {}
    submission_ids = {row["submission_id"] for row in rows}
    for submission_id, performance in SubmissionModel.objects.filter(id__in=submission_ids).values_list("id", "performance"):
        nomination_id = (performance or {}).get("nomination_id")
        if nomination_id:
            category_of[submission_id] = nomination_id

    by_category = {}
    for row in rows:
        category_id = category_of.get(row["submission_id"])
        if category_id is None:
            continue
        by_category.setdefault(category_id, []).append(row)

    for category_id, members in by_category.items():
        IssuedDocumentModel.objects.filter(id__in=[row["id"] for row in members]).update(category_id=category_id)

    # The duplicates the new identity creates: same genre, same kind, same person.
    # Only addressed documents can have them — an unaddressed one is still one per
    # performance, which the older constraint already guaranteed.
    discarded: list = []
    for category_id, members in by_category.items():
        kept = set()
        for row in members:
            key = _recipient_key(row["recipient"])
            if not key:
                continue
            identity = (category_id, row["document_type"], key)
            if identity in kept:
                discarded.append(row["id"])
            else:
                kept.add(identity)
    if discarded:
        from django.utils import timezone

        IssuedDocumentModel.objects.filter(id__in=discarded).update(deleted_at=timezone.now())


def unfill(apps, schema_editor):
    """Clear the column. The soft-deleted duplicates are deliberately left alone.

    Reviving them would re-create exactly the rows this migration was written to
    get rid of, and nothing downstream needs them back: the letters that survived
    are the ones whose URLs are in circulation.
    """
    IssuedDocumentModel = apps.get_model("diplomas", "IssuedDocumentModel")
    IssuedDocumentModel.objects.update(category_id=None)


class Migration(migrations.Migration):
    dependencies = [
        ("diplomas", "0021_assignment_discipline"),
        ("applications", "0009_waitlist"),
    ]

    operations = [
        migrations.AddField(
            model_name="issueddocumentmodel",
            name="category_id",
            field=models.UUIDField(blank=True, default=None, null=True),
        ),
        migrations.AddIndex(
            model_name="issueddocumentmodel",
            index=models.Index(fields=["competition_id", "category_id"], name="diplomas_is_competi_c9c7b8_idx"),
        ),
        migrations.RunPython(fill_category_and_collapse_duplicates, unfill),
        migrations.AddConstraint(
            model_name="issueddocumentmodel",
            constraint=models.UniqueConstraint(
                condition=models.Q(("deleted_at__isnull", True), models.Q(("recipient", ""), _negated=True)),
                fields=("competition_id", "category_id", "document_type", "recipient"),
                name="diplomas_issued_unique_recipient_per_category",
            ),
        ),
    ]
