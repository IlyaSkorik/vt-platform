"""Закэшированные на заявке ссылки начинают помнить id жанра.

Заморозка редактирования теперь жанровая, и «можно ли ещё править эту заявку»
отвечается по жанрам её номеров. Заявка их не грузит — у неё есть кэш-снимок на
каждый номер, — поэтому id жанра переезжает в снимок.

Отдельно от уже лежащего там ``nomination``: сейчас в нём и правда id, но поле
описано как подпись на пути к человекочитаемой, и правило, завязанное на него,
сломалось бы молча в тот день, когда обещание выполнят. Отсюда и добивка: для
старых строк копируем, дальше пишет сам маппер.

Данные только в JSON, схема не меняется.
"""

from django.db import migrations


def copy_nomination_into_its_own_key(apps, schema_editor):
    """Проставить ``nomination_id`` в снимках, записанных до его появления."""
    ApplicationModel = apps.get_model("applications", "ApplicationModel")
    for application in ApplicationModel.objects.exclude(submission_refs=[]).iterator(chunk_size=500):
        refs = application.submission_refs or []
        changed = False
        for ref in refs:
            if ref.get("nomination_id"):
                continue
            # ``nomination`` is the nomination id today — see the module docstring.
            ref["nomination_id"] = ref.get("nomination") or None
            changed = True
        if changed:
            ApplicationModel.objects.filter(id=application.id).update(submission_refs=refs)


def drop_the_key(apps, schema_editor):
    """Убрать ключ обратно — заявки читаются кодом, который его не ждёт."""
    ApplicationModel = apps.get_model("applications", "ApplicationModel")
    for application in ApplicationModel.objects.exclude(submission_refs=[]).iterator(chunk_size=500):
        refs = application.submission_refs or []
        changed = False
        for ref in refs:
            if "nomination_id" in ref:
                del ref["nomination_id"]
                changed = True
        if changed:
            ApplicationModel.objects.filter(id=application.id).update(submission_refs=refs)


class Migration(migrations.Migration):
    dependencies = [
        ("applications", "0009_waitlist"),
    ]

    operations = [
        migrations.RunPython(copy_nomination_into_its_own_key, drop_the_key),
    ]
