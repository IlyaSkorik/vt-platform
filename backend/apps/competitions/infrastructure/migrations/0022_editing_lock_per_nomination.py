"""Замок редактирования переезжает с фестиваля на жанр.

Фестиваль заканчивает жанры по одному: вокал судят в субботу и его программу уже
собирают, пока хореография ещё принимает заявки. Один выключатель на весь конкурс
заставлял организатора выбирать между «заморозить то, что не готово» и «оставить
открытым то, что готово».

Порядок операций здесь — не формальность: колонка на жанре появляется первой,
замороженные фестивали переносятся на все свои жанры тем же моментом, и только
потом уходит колонка фестиваля. Обратная миграция складывает жанры назад в один
момент — самый ранний из них, потому что именно он отвечает на вопрос «когда у
меня закрылось редактирование» для того, кто спросит первым.
"""

from django.db import migrations, models


def lock_nominations_of_frozen_competitions(apps, schema_editor):
    """Перенести момент заморозки фестиваля на все его жанры."""
    CompetitionModel = apps.get_model("competitions", "CompetitionModel")
    CategoryModel = apps.get_model("competitions", "CategoryModel")
    for competition_id, locked_at in CompetitionModel.objects.exclude(editing_locked_at=None).values_list("id", "editing_locked_at"):
        CategoryModel.objects.filter(competition_id=competition_id).update(editing_locked_at=locked_at)


def freeze_competitions_with_any_locked_nomination(apps, schema_editor):
    """Сложить замки жанров обратно в один на фестивале — по самому раннему."""
    from django.db.models import Min

    CompetitionModel = apps.get_model("competitions", "CompetitionModel")
    CategoryModel = apps.get_model("competitions", "CategoryModel")
    rows = (
        CategoryModel.objects.exclude(editing_locked_at=None)
        .values("competition_id")
        .annotate(earliest=Min("editing_locked_at"))
    )
    for row in rows:
        CompetitionModel.objects.filter(id=row["competition_id"]).update(editing_locked_at=row["earliest"])


class Migration(migrations.Migration):
    dependencies = [
        ("competitions", "0021_editing_lock"),
    ]

    operations = [
        migrations.AddField(
            model_name="categorymodel",
            name="editing_locked_at",
            field=models.DateTimeField(blank=True, default=None, null=True),
        ),
        migrations.RunPython(
            lock_nominations_of_frozen_competitions,
            freeze_competitions_with_any_locked_nomination,
        ),
        migrations.RemoveField(
            model_name="competitionmodel",
            name="editing_locked_at",
        ),
    ]
