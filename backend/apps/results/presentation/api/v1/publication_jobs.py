"""Фоновая доводка публикации: поставить задание и прочитать его.

Живёт на краю, а не в сервисе, по той же причине, что и у дипломов
(:mod:`apps.diplomas.presentation.api.v1.diplomas.documents`): строка задания — это
способ ответить клиенту, пока работа не доделана, а не часть правил протокола.
Сервис про неё ничего не знает и знать не должен — он умеет опубликовать и умеет
довести публикацию, а чем именно это запущено, его не касается. Сам прогон — в
:mod:`apps.results.tasks`, там же, где и у дипломов.

Форма ``result`` выбрана не свободно: это ровно тот объект, которым прежде отвечал сам
``POST``. Клиент, дождавшийся джобы, читает прежние поля — ему пришлось научиться
ждать, а не читать заново.
"""

from __future__ import annotations

import datetime
import uuid
from typing import Any

from django.utils import timezone

from apps.results.application.dto import PublicationResultView
from apps.results.infrastructure.models import PublicationJobModel, PublicationJobStatusChoices

__all__ = [
    "STALE_AFTER",
    "job_json",
    "latest_publication_job",
    "result_json",
    "start_publication",
    "unfinished_publication_job",
]

#: Состояния, в которых работа ещё идёт: по ним клиент решает, опрашивать ли дальше, а
#: эндпоинт — не поставлена ли уже такая же джоба.
UNFINISHED = (PublicationJobStatusChoices.PENDING, PublicationJobStatusChoices.RUNNING)

#: После какого возраста незаконченная джоба перестаёт считаться идущей.
#:
#: Воркер, убитый между «взял задачу» и «записал исход», оставляет строку в ``RUNNING``
#: навсегда. Без срока годности одна такая строка запирала бы номинацию: публиковать
#: нельзя, потому что «предыдущая ещё доводится», а она уже никогда не доведётся. Полчаса
#: — заведомо больше самого долгого реального прогона (полторы сотни номеров с именными
#: дипломами коллективов) и заведомо меньше, чем организатор готов ждать в день
#: фестиваля.
STALE_AFTER = datetime.timedelta(minutes=30)


def job_json(job: PublicationJobModel) -> dict[str, Any]:
    """Одно задание так, как его опрашивает клиент.

    ``result`` пуст, пока прогон не кончился, и остаётся пустым при провале — там, где
    он провалился, говорит ``error``.
    """
    return {
        "jobId": str(job.id),
        "protocolId": str(job.protocol_id),
        "revision": job.revision,
        "notify": job.notify,
        "status": job.status,
        "result": job.result or None,
        "error": job.error or None,
        "createdAt": job.created_at,
        "updatedAt": job.updated_at,
    }


def result_json(view: PublicationResultView) -> dict[str, Any]:
    """Итог прогона на проводе — те же счётчики, что показывал диалог публикации."""
    return {
        "diplomasAwarded": view.diplomas_awarded,
        "diplomasCreated": view.diplomas_created,
        "diplomasMissing": view.diplomas_missing,
        "lettersSent": view.letters_sent,
        "lettersSkipped": view.letters_skipped,
    }


def unfinished_publication_job(protocol_id: uuid.UUID) -> PublicationJobModel | None:
    """Доводка этого протокола, которая прямо сейчас идёт, если она есть.

    Брошенная строка (см. :data:`STALE_AFTER`) идущей не считается: иначе один убитый
    воркер запирал бы номинацию навсегда.
    """
    return (
        PublicationJobModel.objects.filter(
            protocol_id=protocol_id,
            status__in=UNFINISHED,
            created_at__gte=timezone.now() - STALE_AFTER,
        )
        .order_by("-created_at")
        .first()
    )


def latest_publication_job(protocol_id: uuid.UUID) -> PublicationJobModel | None:
    """Последняя доводка этого протокола — та, про которую спрашивает экран."""
    return PublicationJobModel.objects.filter(protocol_id=protocol_id).order_by("-created_at").first()


def start_publication(
    *,
    protocol_id: uuid.UUID,
    competition_id: uuid.UUID,
    revision: int,
    notify: bool,
    actor_id: uuid.UUID | None = None,
) -> dict[str, Any]:
    """Поставить доводку опубликованного протокола в очередь; вернуть задание.

    Вызывается уже после того, как протокол опубликован: страница публична, что бы
    дальше ни случилось с этой джобой. Потому и ставится она последней — задание,
    созданное до публикации, было бы обещанием, которого никто не давал.
    """
    job = PublicationJobModel.objects.create(
        protocol_id=protocol_id,
        competition_id=competition_id,
        revision=revision,
        notify=notify,
        actor_id=actor_id,
    )
    from apps.results.tasks import finish_publication

    finish_publication.delay(str(job.id))
    job.refresh_from_db()
    return job_json(job)
