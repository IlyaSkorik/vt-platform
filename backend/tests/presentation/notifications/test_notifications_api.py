"""Integration tests for the cabinet notification feed.

Driven through DRF's ``APIClient`` with a real JWT, so the parts that matter are
exercised end to end: that the feed is scoped to the caller, that reading somebody
else's entry is impossible even with its id, and that the unread count the bell
renders tracks what was actually opened.
"""

from __future__ import annotations

import uuid

import pytest
from rest_framework.test import APIClient

from apps.identity.presentation.api.v1.auth import composition as identity_composition
from apps.notifications.infrastructure import feed
from apps.notifications.infrastructure.models import NotificationKind, NotificationModel

pytestmark = pytest.mark.django_db

_PASSWORD = "V3ry$ecurePass!"
_FEED = "/api/v1/me/notifications"


def _account(email: str) -> tuple[APIClient, str]:
    """An authenticated client and the id of the account behind it."""
    client = APIClient()
    registration = client.post(
        "/api/v1/auth/registration",
        {"email": email, "password": _PASSWORD, "firstName": "Ольга", "lastName": "Петрова"},
        format="json",
    )
    user_id = str(registration.data["data"]["id"])
    access = identity_composition.build_token_service().issue(subject=user_id).access_token
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {access}")
    return client, user_id


def _seed(user_id: str, title: str, *, link: str = "/cabinet/applications") -> None:
    feed.publish(recipient_id=user_id, kind=NotificationKind.CORRECTION_REQUESTED, title=title, body="Подробности", link=link)


def test_requires_authentication() -> None:
    assert APIClient().get(_FEED).status_code == 401


def test_feed_returns_own_entries_newest_first() -> None:
    client, user_id = _account("feed-owner@example.com")
    _seed(user_id, "Первое")
    _seed(user_id, "Второе")

    response = client.get(_FEED)

    assert response.status_code == 200, response.data
    data = response.data["data"]
    assert [item["title"] for item in data["items"]] == ["Второе", "Первое"]
    assert data["unreadCount"] == 2
    assert data["items"][0]["link"] == "/cabinet/applications"
    assert data["items"][0]["readAt"] is None


def test_feed_never_shows_another_accounts_entries() -> None:
    mine, my_id = _account("mine@example.com")
    _, other_id = _account("other@example.com")
    _seed(my_id, "Моё")
    _seed(other_id, "Чужое")

    data = mine.get(_FEED).data["data"]

    assert [item["title"] for item in data["items"]] == ["Моё"]
    assert data["unreadCount"] == 1


def test_marking_one_entry_read_drops_the_unread_count() -> None:
    client, user_id = _account("reader@example.com")
    _seed(user_id, "Первое")
    _seed(user_id, "Второе")
    target = client.get(_FEED).data["data"]["items"][0]["id"]

    response = client.post(f"{_FEED}/{target}/read")

    assert response.status_code == 200, response.data
    assert response.data["data"] == {"unreadCount": 1, "markedCount": 1}
    # Read, not gone: the feed is a record of what the person was told.
    assert len(client.get(_FEED).data["data"]["items"]) == 2


def test_marking_the_same_entry_twice_changes_nothing_further() -> None:
    client, user_id = _account("twice@example.com")
    _seed(user_id, "Единственное")
    target = client.get(_FEED).data["data"]["items"][0]["id"]
    client.post(f"{_FEED}/{target}/read")

    again = client.post(f"{_FEED}/{target}/read")

    assert again.data["data"] == {"unreadCount": 0, "markedCount": 0}


def test_another_accounts_entry_cannot_be_marked_even_with_its_id() -> None:
    mine, my_id = _account("attacker@example.com")
    _, other_id = _account("victim@example.com")
    _seed(my_id, "Моё")
    _seed(other_id, "Чужое")
    stolen = str(NotificationModel.objects.get(recipient_id=uuid.UUID(other_id)).id)

    response = mine.post(f"{_FEED}/{stolen}/read")

    # Answered as "nothing changed" rather than 404, so the endpoint cannot be used
    # to find out which notification ids exist.
    assert response.status_code == 200
    assert response.data["data"]["markedCount"] == 0
    assert NotificationModel.objects.get(recipient_id=uuid.UUID(other_id)).read_at is None


def test_mark_all_read_clears_the_bell() -> None:
    client, user_id = _account("clear-all@example.com")
    for index in range(3):
        _seed(user_id, f"Событие {index}")

    response = client.post(f"{_FEED}/read")

    assert response.data["data"] == {"unreadCount": 0, "markedCount": 3}
    assert client.get(_FEED).data["data"]["unreadCount"] == 0


def test_publishing_never_raises_on_a_junk_recipient() -> None:
    # Callers hand over whatever id they hold; a value that is not an identifier is a
    # skipped write, never an exception thrown back into somebody's submit.
    feed.publish(recipient_id="not-a-uuid", kind=NotificationKind.RESULTS_PUBLISHED, title="Результаты")

    assert NotificationModel.objects.count() == 0
