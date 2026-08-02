"""Give every existing competition the readable address it will be linked by.

The slug column arrives empty, and a competition without one keeps answering at
its UUID — nothing breaks. But the sitemap and every link the catalog renders
prefer the slug, so leaving the existing festivals on UUIDs would mean the ones
already published are the only ones search never learns to read.

Derived from title and season together, because a festival that runs annually
carries the same title every year and only the season tells the two apart.
Assigned once here and never recomputed: a slug that chases a renamed title
breaks the links already in circulation.
"""

from __future__ import annotations

from django.db import migrations

from shared.utils.slugs import unique_slug


def backfill_slugs(apps, schema_editor):
    CompetitionModel = apps.get_model("competitions", "CompetitionModel")

    taken = set(
        CompetitionModel.objects.exclude(slug=None).values_list("slug", flat=True),
    )

    for competition in CompetitionModel.objects.filter(slug=None).order_by("created_at"):
        slug = unique_slug(
            f"{competition.title} {competition.season}",
            # A title of nothing but unmappable characters still needs an address,
            # and the id is the one thing guaranteed unique.
            fallback=f"competition-{str(competition.id)[:8]}",
            is_taken=lambda candidate: candidate in taken,
        )
        taken.add(slug)
        competition.slug = slug
        competition.save(update_fields=["slug"])


def clear_slugs(apps, schema_editor):
    CompetitionModel = apps.get_model("competitions", "CompetitionModel")
    CompetitionModel.objects.update(slug=None)


class Migration(migrations.Migration):
    dependencies = [
        ("competitions", "0017_competition_slug"),
    ]

    operations = [
        migrations.RunPython(backfill_slugs, clear_slugs),
    ]
