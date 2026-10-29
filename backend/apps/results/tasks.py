"""Celery-задачи контекста Results (автообнаружение по имени модуля).

Тонкие: поднять прогон и записать его исход на долговечную строку задания
(:class:`PublicationJobModel`), чтобы клиент мог её опросить. Работа — выпуск дипломов
со степенями и письма участникам опубликованного протокола — линейна по числу строк и
на большой номинации длиннее, чем любой прокси держит соединение; строка задания
переживает и перезапуск воркера, и закрытую вкладку.
"""

from __future__ import annotations

from celery import shared_task


@shared_task(name="results.finish_publication")  # type: ignore[untyped-decorator]  # celery ships no stubs
def finish_publication(job_id: str) -> None:
    """Довести одну публикацию: дипломы со степенями, затем письма участникам.

    Всё, что может пойти не так, остаётся на строке задания, а не только в логе
    воркера: организатор, нажавший «Опубликовать», — единственный, кто может с этим
    что-то сделать, и единственный, кто не узнает об упавшей джобе, если она сама не
    скажет.
    """
    from django.utils import timezone

    from apps.results.composition import build_protocol_service
    from apps.results.infrastructure.models import PublicationJobModel, PublicationJobStatusChoices
    from apps.results.presentation.api.v1.publication_jobs import result_json

    job = PublicationJobModel.objects.filter(id=job_id).first()
    if job is None:
        return

    job.status = PublicationJobStatusChoices.RUNNING
    job.updated_at = timezone.now()
    job.save(update_fields=["status", "updated_at"])

    try:
        outcome = build_protocol_service().complete_publication(str(job.protocol_id), notify=job.notify)
    except Exception as exc:
        job.status = PublicationJobStatusChoices.FAILED
        job.error = str(exc)[:2000]
    else:
        job.status = PublicationJobStatusChoices.COMPLETED
        job.result = result_json(outcome)
        job.error = ""
    job.updated_at = timezone.now()
    job.save(update_fields=["status", "result", "error", "updated_at"])
