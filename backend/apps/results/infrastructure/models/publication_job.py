"""``PublicationJobModel`` — одна публикация протокола, доводимая в фоне.

Модель персистентности, и только. Публикация делится надвое: страница становится
публичной в самом запросе (это решение организатора, оно обязано отработать при нём),
а дипломы и письма — работа, линейная по числу строк, и на номинации в полтораста
номеров она длиннее, чем любой прокси между организатором и воркером держит
соединение. Ровно по этой причине так устроены печатный пакет и генерация документов
(``diplomas_print_job``, ``diplomas_document_job``); здесь то же самое для итогов.

Строка — долговечный статус этой работы: она переживает перезапуск воркера, и по ней
организатор видит, чем кончилось, даже если закрыл вкладку сразу после нажатия.
"""

from __future__ import annotations

from django.db import models

from .base import BasePersistenceModel

__all__ = ["PublicationJobModel", "PublicationJobStatusChoices"]


class PublicationJobStatusChoices(models.TextChoices):
    """Жизненный цикл публикации. Те же четыре состояния, что у джоб дипломов."""

    PENDING = "PENDING", "Pending"
    RUNNING = "RUNNING", "Running"
    COMPLETED = "COMPLETED", "Completed"
    FAILED = "FAILED", "Failed"


class PublicationJobModel(BasePersistenceModel):
    """Строка одной фоновой доводки публикации (только персистентность)."""

    protocol_id = models.UUIDField()
    # Та же ссылка id-ом, что и везде в контексте (ARCH-001 §9.2): нужна, чтобы найти
    # все доводки фестиваля, не поднимая протоколы.
    competition_id = models.UUIDField()

    # Решение из диалога публикации, принятое до того, как работа началась: воркер
    # обязан отправить (или не отправить) письма по тому, что выбрал организатор, а не
    # по умолчанию.
    notify = models.BooleanField(default=True)

    # Какую ревизию протокола эта доводка выпускает. Не управляет поведением — служит
    # ответом на «а это про ту публикацию или про прошлую» в поддержке и в логе.
    revision = models.PositiveIntegerField(default=0)

    status = models.CharField(
        max_length=16,
        choices=PublicationJobStatusChoices.choices,
        default=PublicationJobStatusChoices.PENDING,
    )

    # Итог прогона целиком, а не по колонкам: это ровно тот объект, которым раньше
    # отвечал сам запрос, так что клиент, дождавшийся джобы, читает прежнюю форму. Пуст,
    # пока прогон не кончился.
    result = models.JSONField(default=dict, blank=True)

    error = models.TextField(blank=True, default="")

    # Кто нажал. Запрос это знает, воркер — нет.
    actor_id = models.UUIDField(null=True, blank=True, default=None)

    class Meta(BasePersistenceModel.Meta):
        db_table = "results_publication_job"
        verbose_name = "publication job"
        verbose_name_plural = "publication jobs"
        indexes = [
            *BasePersistenceModel.Meta.indexes,
            # Чтение всегда одно и то же: последняя джоба этого протокола.
            models.Index(fields=["protocol_id", "-created_at"]),
            models.Index(fields=["status"]),
        ]
        constraints = [
            *BasePersistenceModel.Meta.constraints,
            models.CheckConstraint(
                condition=models.Q(status__in=PublicationJobStatusChoices.values),
                name="results_publication_job_status_valid",
            ),
        ]

    def __str__(self) -> str:
        return f"PublicationJob {self.id} ({self.status})"
