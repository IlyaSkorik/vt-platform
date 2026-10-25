"""Конфигурация сценарных тестов.

Подключение к PostgreSQL берётся из настроек Django (pytest-django): сценарии
ходят в живую БД, не в SQLite. ORM в самих тестах не используется.
"""

from __future__ import annotations

import io
import os
from pathlib import Path

import pytest
from django.core.management import call_command

from tests.journeys.actors import (
    ActorFactory,
    Bootstrap,
    Mailbox,
    MailhogMailbox,
    OutboxMailbox,
)

_JOURNEYS_DIR = Path(__file__).resolve().parent


def pytest_collection_modifyitems(items: list[pytest.Item]) -> None:
    """Все сценарии идут в транзакционном режиме."""
    for item in items:
        if _JOURNEYS_DIR in item.path.resolve().parents:
            item.add_marker(pytest.mark.django_db(transaction=True))


@pytest.fixture
def mailbox() -> Mailbox:
    url = os.environ.get("JOURNEY_MAILHOG_URL")
    return MailhogMailbox(url) if url else OutboxMailbox()


@pytest.fixture
def bootstrap() -> Bootstrap:
    """Как проект сам заводит первых привилегированных людей: management-команда."""

    def run(command: str, email: str) -> None:
        call_command(command, email=email, stdout=io.StringIO())

    return run


@pytest.fixture
def actors(mailbox: Mailbox, bootstrap: Bootstrap) -> ActorFactory:
    """Фабрика акторов: actors.guest(), .participant(), .organizer(), .operator()."""
    return ActorFactory(mailbox, bootstrap)
