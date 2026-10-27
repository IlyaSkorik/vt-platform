"""Акторы для сценарных (journey) тестов.

Правило эпика: ORM здесь не трогаем вообще. Любое состояние заводится через HTTP,
а подтверждение почты проходится по-настоящему: письмо читается из почтового ящика,
токен достаётся из его текста и отправляется в ручку подтверждения."""

from __future__ import annotations

import email as email_lib
import html
import json
import re
import time
import uuid
from collections.abc import Callable
from email import policy
from typing import Any
from urllib import parse as urlparse
from urllib import request as urlrequest


# Контракт API
REGISTRATION_PATH = "/api/v1/auth/registration"
CONFIRM_EMAIL_PATH = "/api/v1/auth/email-verification/confirmations"
CONFIRM_EMAIL_FIELD = "token"
LOGIN_PATH = "/api/v1/auth/sessions"

AUTH_SCHEME = "Bearer"
LOGIN_TOKEN_KEYS = ("accessToken", "access", "access_token", "token", "key")

# Токен подтверждения
CONFIRM_QUERY_RE = re.compile(r"[?&](?:token|key|code)=([A-Za-z0-9_\-\.:~%]+)")
CONFIRM_PATH_RE = re.compile(r"/(?:confirm|verify)[\w\-]*/([A-Za-z0-9_\-\.:~%]+)")

DEFAULT_PASSWORD = "Journey-Pass-12345!"

# Management-команды, которыми проект сам заводит первых привилегированных людей.
GRANT_PLATFORM_ADMIN = "grant_platform_admin"
BOOTSTRAP_OWNER = "bootstrap_owner"


type Bootstrap = Callable[[str, str], None]


class MailNotReceivedError(AssertionError):
    pass



# Почтовые ящики
class Mailbox:
    """Достаёт текст последнего письма, адресованного `to`."""

    def wait_for(self, to: str, timeout: float = 10.0) -> str:
        deadline = time.monotonic() + timeout
        while True:
            body = self._find(to)
            if body is not None:
                return html.unescape(body)
            if time.monotonic() > deadline:
                raise MailNotReceivedError(
                    f"Письмо для {to} не пришло за {timeout:.0f} с. "
                    "Если используется MailHog: запущен ли mail-worker "
                    "и пуста ли очередь (redis-cli -n 1 llen mail)?"
                )
            time.sleep(0.25)

    def _find(self, to: str) -> str | None:
        raise NotImplementedError


class OutboxMailbox(Mailbox):

    def _find(self, to: str) -> str | None:
        from django.core import mail

        for message in reversed(mail.outbox):
            if to in message.to:
                return str(message.body)
        return None


class MailhogMailbox(Mailbox):
    """Письма из живого MailHog по HTTP API v2"""

    def __init__(self, base_url: str) -> None:
        self.base_url = base_url.rstrip("/")

    def _find(self, to: str) -> str | None:
        query = urlparse.urlencode({"kind": "to", "query": to})
        url = f"{self.base_url}/api/v2/search?{query}"
        with urlrequest.urlopen(url, timeout=5) as response:
            items = json.load(response).get("items") or []
        if not items:
            return None
        # MailHog отдаёт сначала новые; парсим сырое письмо, чтобы корректно
        # раскодировать quoted-printable / base64.
        message = email_lib.message_from_string(items[0]["Raw"]["Data"], policy=policy.default)
        part = message.get_body(preferencelist=("plain", "html"))
        return str(part.get_content()) if part is not None else ""


def extract_confirmation_token(body: str) -> str:
    for pattern in (CONFIRM_QUERY_RE, CONFIRM_PATH_RE):
        found = pattern.search(body)
        if found:
            return urlparse.unquote(found.group(1))
    raise AssertionError(f"В письме не найден токен подтверждения:\n{body[:500]}")


def _find_token(payload: Any) -> str | None:
    """Ищет токен доступа в ответе логина, в том числе во вложенных объектах."""
    if isinstance(payload, dict):
        for key in LOGIN_TOKEN_KEYS:
            value = payload.get(key)
            if isinstance(value, str) and value:
                return value
        for value in payload.values():
            found = _find_token(value)
            if found:
                return found
    return None


def _brief(response: Any) -> str:
    content = getattr(response, "content", b"")
    text = content.decode("utf-8", "replace") if isinstance(content, bytes) else str(content)
    return f"{response.status_code} {text[:2000]}"



# Акторы
class Actor:
    """Человек с собственным HTTP-клиентом и собственным заголовком Authorization."""

    role = "guest"

    def __init__(
        self,
        client: Any,
        mailbox: Mailbox,
        *,
        email: str | None = None,
        password: str = DEFAULT_PASSWORD,
    ) -> None:
        self.client = client
        self.mailbox = mailbox
        self.email = email or f"{self.role}-{uuid.uuid4().hex[:10]}@example.test"
        self.password = password
        self.token: str | None = None

    # Authorization 
    @property
    def authorization(self) -> str | None:
        return f"{AUTH_SCHEME} {self.token}" if self.token else None

    @property
    def headers(self) -> dict[str, str]:
        return {"Authorization": f"{AUTH_SCHEME} {self.token}"} if self.token else {}

    # HTTP 
    def request(self, method: str, path: str, data: Any = None, **extra: Any) -> Any:
        if self.token:
            extra["HTTP_AUTHORIZATION"] = self.authorization
        call = getattr(self.client, method.lower())
        if method.upper() == "GET":
            return call(path, data, **extra)
        return call(path, data, format="json", **extra)

    def get(self, path: str, data: Any = None, **extra: Any) -> Any:
        return self.request("GET", path, data, **extra)

    def post(self, path: str, data: Any = None, **extra: Any) -> Any:
        return self.request("POST", path, data, **extra)

    def put(self, path: str, data: Any = None, **extra: Any) -> Any:
        return self.request("PUT", path, data, **extra)

    def patch(self, path: str, data: Any = None, **extra: Any) -> Any:
        return self.request("PATCH", path, data, **extra)

    def delete(self, path: str, data: Any = None, **extra: Any) -> Any:
        return self.request("DELETE", path, data, **extra)

    # Путь живого человека 
    def registration_payload(self) -> dict[str, Any]:
        return {
            "email": self.email,
            "password": self.password,
            "firstName": "Тест",
            "lastName": "Тестов",
        }

    def register(self) -> Any:
        response = self.client.post(REGISTRATION_PATH, self.registration_payload(), format="json")
        assert response.status_code in (200, 201, 202, 204), f"Регистрация {self.email}: {_brief(response)}"
        return response

    def confirm_email(self) -> Any:
        body = self.mailbox.wait_for(self.email)
        token = extract_confirmation_token(body)
        response = self.client.post(CONFIRM_EMAIL_PATH, {CONFIRM_EMAIL_FIELD: token}, format="json")
        assert response.status_code in (200, 201, 204), f"Подтверждение почты {self.email}: {_brief(response)}"
        return response

    def login(self) -> Any:
        response = self.client.post(LOGIN_PATH, {"email": self.email, "password": self.password}, format="json")
        assert response.status_code in (200, 201), f"Логин {self.email}: {_brief(response)}"
        payload = response.json()
        token = _find_token(payload)
        if token is None:
            raise AssertionError(f"В ответе логина нет токена (искали {LOGIN_TOKEN_KEYS}): {_brief(response)}")
        self.token = token
        return response

    def sign_up(self) -> Actor:
        """Регистрация -> подтверждение почты -> логин."""
        self.register()
        self.confirm_email()
        self.login()
        return self


class Guest(Actor):
    """Аноним: аккаунта нет, пока сценарий сам не вызовет register()/sign_up()."""

    role = "guest"


class Participant(Actor):
    role = "participant"


class Organizer(Actor):
    """Первый владелец (OWNER) организации."""

    role = "organizer"


class Judge(Actor):
    role = "judge"


class PlatformOperator(Actor):
    """Администратор платформы."""

    role = "operator"


class ActorFactory:
    """Создаёт акторов: у каждого свой клиент и своя почта."""

    def __init__(
        self,
        mailbox: Mailbox,
        bootstrap: Bootstrap,
        client_factory: Callable[[], Any] | None = None,
    ) -> None:
        self.mailbox = mailbox
        self._bootstrap = bootstrap
        self._client_factory = client_factory or self._default_client

    @staticmethod
    def _default_client() -> Any:
        from rest_framework.test import APIClient

        return APIClient()

    def guest(self) -> Guest:
        return Guest(self._client_factory(), self.mailbox)

    def participant(self) -> Participant:
        actor = Participant(self._client_factory(), self.mailbox)
        actor.sign_up()
        return actor

    def operator(self) -> PlatformOperator:
        actor = PlatformOperator(self._client_factory(), self.mailbox)
        return self._promoted(actor, GRANT_PLATFORM_ADMIN)

    def organizer(self) -> Organizer:
        actor = Organizer(self._client_factory(), self.mailbox)
        return self._promoted(actor, BOOTSTRAP_OWNER)

    def judge(self) -> Judge:
        raise NotImplementedError("Судья: ещё не выяснено, как он получает роль по HTTP (см. ручки judging).")

    def _promoted[A: Actor](self, actor: A, command: str) -> A:
        actor.register()
        actor.confirm_email()
        self._bootstrap(command, actor.email)  
        actor.login() 
        return actor
