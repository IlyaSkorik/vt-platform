"""Публикация протокола через реальный REST-край: ответ сразу, дипломы — в фоне.

Набор держит ровно тот шов, ради которого публикация разделена надвое. Запрос обязан
вернуться, когда страница стала публичной, а не когда выпущен последний диплом: на
номинации в полтораста номеров второе длиннее, чем клиент и прокси готовы ждать, и
организатору показывали ошибку на опубликованном протоколе.

В тестовой конфигурации Celery исполняет задачи на месте (``CELERY_TASK_ALWAYS_EAGER``),
поэтому джоба здесь успевает дойти до ``COMPLETED`` внутри запроса. Проверяется не это,
а форма: ``POST`` отвечает `202`, протоколом и заданием, а итог живёт на задании и
читается отдельным ``GET`` — тем самым, которым экран опрашивает работу.
"""

from __future__ import annotations

from datetime import timedelta
from typing import Any

import pytest
from django.utils import timezone
from rest_framework.test import APIClient

from apps.results.infrastructure.models import PublicationJobModel, PublicationJobStatusChoices
from apps.results.presentation.api.v1.publication_jobs import STALE_AFTER

from .conftest import seed_act

pytestmark = pytest.mark.django_db

_PROTOCOLS = "/api/v1/staff/protocols"


def _protocol_with_a_result(staff_client: APIClient, competition: dict[str, Any]) -> dict[str, Any]:
    """Протокол одной номинации с проставленным результатом — то, что можно публиковать."""
    competition_id = str(competition["id"])
    category_id = str(competition["categories"][0]["id"])
    seed_act(competition_id, category_id, "Песня А")

    created = staff_client.post(
        _PROTOCOLS,
        {"competitionId": competition_id, "nominationId": category_id},
        format="json",
    )
    assert created.status_code == 201, created.data
    protocol = created.data["data"]
    row_id = protocol["rows"][0]["id"]
    awarded = staff_client.put(
        f"{_PROTOCOLS}/{protocol['id']}/awards",
        {"awards": [{"rowId": row_id, "award": "LAUREATE_I"}]},
        format="json",
    )
    assert awarded.status_code == 200, awarded.data
    result: dict[str, Any] = awarded.data["data"]
    return result


class TestPublishing:
    def test_publishing_answers_with_the_public_protocol_and_a_job(self, staff_client: APIClient, competition: dict[str, Any]) -> None:
        protocol = _protocol_with_a_result(staff_client, competition)

        published = staff_client.post(f"{_PROTOCOLS}/{protocol['id']}/publication", {"notify": False}, format="json")

        assert published.status_code == 202, published.data
        body = published.data["data"]
        # Страница публична уже в ответе: статус, ревизия и ссылка окончательны.
        assert body["protocol"]["status"] == "PUBLISHED"
        assert body["protocol"]["revision"] == 1
        assert body["protocol"]["slug"]
        # А дипломы и письма — принятая к исполнению работа со своей строкой.
        assert body["job"]["protocolId"] == protocol["id"]
        assert body["job"]["status"] in {status.value for status in PublicationJobStatusChoices}
        assert body["job"]["notify"] is False

    def test_the_outcome_is_read_off_the_job(self, staff_client: APIClient, competition: dict[str, Any]) -> None:
        protocol = _protocol_with_a_result(staff_client, competition)
        staff_client.post(f"{_PROTOCOLS}/{protocol['id']}/publication", {"notify": False}, format="json")

        job = staff_client.get(f"{_PROTOCOLS}/{protocol['id']}/publication")

        assert job.status_code == 200, job.data
        body = job.data["data"]
        assert body["status"] == PublicationJobStatusChoices.COMPLETED.value
        # Те же счётчики, которыми раньше отвечал сам POST, — клиенту пришлось научиться
        # ждать, а не читать заново.
        assert body["result"]["diplomasMissing"] == 1
        assert body["result"]["lettersSent"] == 0
        assert body["error"] is None

    def test_a_protocol_that_was_never_published_has_no_job(self, staff_client: APIClient, competition: dict[str, Any]) -> None:
        protocol = _protocol_with_a_result(staff_client, competition)

        job = staff_client.get(f"{_PROTOCOLS}/{protocol['id']}/publication")

        # ``null``, а не 404: «ещё не публиковали» — нормальный ответ на нормальный вопрос.
        assert job.status_code == 200, job.data
        assert job.data["data"] is None

    def test_publishing_over_a_run_that_is_still_going_is_refused(self, staff_client: APIClient, competition: dict[str, Any]) -> None:
        protocol = _protocol_with_a_result(staff_client, competition)
        staff_client.post(f"{_PROTOCOLS}/{protocol['id']}/publication", {"notify": False}, format="json")
        # Воркер, который ещё не доработал: два прогона по одной номинации перевыпускали
        # бы одни и те же файлы с двух сторон.
        PublicationJobModel.objects.filter(protocol_id=protocol["id"]).update(status=PublicationJobStatusChoices.RUNNING)

        again = staff_client.post(f"{_PROTOCOLS}/{protocol['id']}/publication", {"notify": False}, format="json")

        assert again.status_code == 409, again.data
        assert "доводится" in again.data["detail"]

    def test_a_run_abandoned_by_a_dead_worker_does_not_lock_the_nomination(self, staff_client: APIClient, competition: dict[str, Any]) -> None:
        # Воркер, убитый между «взял задачу» и «записал исход», оставляет строку в
        # RUNNING навсегда. Без срока годности она запирала бы номинацию: публиковать
        # нельзя, потому что предыдущая «ещё доводится», а она уже не доведётся.
        protocol = _protocol_with_a_result(staff_client, competition)
        staff_client.post(f"{_PROTOCOLS}/{protocol['id']}/publication", {"notify": False}, format="json")
        PublicationJobModel.objects.filter(protocol_id=protocol["id"]).update(
            status=PublicationJobStatusChoices.RUNNING,
            created_at=timezone.now() - STALE_AFTER - timedelta(minutes=1),
        )

        again = staff_client.post(f"{_PROTOCOLS}/{protocol['id']}/publication", {"notify": False}, format="json")

        assert again.status_code == 202, again.data
        assert PublicationJobModel.objects.filter(protocol_id=protocol["id"]).count() == 2

    def test_a_protocol_with_no_results_is_refused_before_any_job_is_made(self, staff_client: APIClient, competition: dict[str, Any]) -> None:
        competition_id = str(competition["id"])
        category_id = str(competition["categories"][0]["id"])
        seed_act(competition_id, category_id, "Песня А")
        created = staff_client.post(
            _PROTOCOLS,
            {"competitionId": competition_id, "nominationId": category_id},
            format="json",
        )
        protocol_id = created.data["data"]["id"]

        refused = staff_client.post(f"{_PROTOCOLS}/{protocol_id}/publication", {"notify": False}, format="json")

        assert refused.status_code == 422, refused.data
        # Задание ставится последним, уже по опубликованному протоколу: иначе оно было бы
        # обещанием, которого никто не давал.
        assert not PublicationJobModel.objects.filter(protocol_id=protocol_id).exists()
