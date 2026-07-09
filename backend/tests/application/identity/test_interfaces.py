"""Unit tests for the Identity application ports.

These tests pin the *contracts*, not any implementation — none exists in the
application layer by design. They verify two things:

* **Protocol compatibility** — a conforming fake structurally satisfies each
  port (checked at runtime via the ``@runtime_checkable`` protocols), and a fake
  missing a method does not.
* **Type correctness** — module-level ``_accepts_*`` functions bind each fake to
  its port type. These are exercised statically by ``mypy --strict``; at runtime
  they simply confirm the fakes are usable through the port's methods.

Everything here is framework-free, database-free, and clock-free (ARCH-001
§28.2): time is supplied explicitly and domain objects are built directly.
"""

from __future__ import annotations

import uuid
from collections.abc import Sequence
from datetime import UTC, datetime

from apps.identity.application.interfaces import (
    Clock,
    EmailGateway,
    EventPublisher,
    NotificationGateway,
    PasswordHasher,
    SmsGateway,
    UserRepository,
    UuidGenerator,
    VerificationToken,
    VerificationTokenService,
)
from apps.identity.domain.entities import User
from apps.identity.domain.events import DomainEvent
from apps.identity.domain.value_objects import (
    Email,
    FullName,
    Locale,
    PasswordHash,
    PhoneNumber,
    UserId,
)

NOW = datetime(2026, 7, 7, 12, 0, tzinfo=UTC)
_HASH = PasswordHash.from_hash("$argon2id$v=19$m=65536,t=3,p=4$c2FsdA$aGFzaA")


def _make_user() -> User:
    """Build a valid ``User`` aggregate for repository fakes."""
    user, _ = User.register(
        user_id=UserId.generate(),
        email=Email("member@example.com"),
        full_name=FullName.of("Ivan", "Petrov"),
        password_hash=_HASH,
        now=NOW,
    )
    return user


# ---------------------------------------------------------------------------
# Conforming fakes — one per port
# ---------------------------------------------------------------------------


class FakeUserRepository:
    """In-memory ``UserRepository`` that stores aggregates by id."""

    def __init__(self) -> None:
        self._by_id: dict[UserId, User] = {}

    def get(self, user_id: UserId) -> User | None:
        return self._by_id.get(user_id)

    def get_by_email(self, email: Email) -> User | None:
        return next((u for u in self._by_id.values() if u.email == email), None)

    def get_by_phone(self, phone: PhoneNumber) -> User | None:
        return next((u for u in self._by_id.values() if u.phone == phone), None)

    def exists(self, user_id: UserId) -> bool:
        return user_id in self._by_id

    def exists_by_email(self, email: Email) -> bool:
        return any(u.email == email for u in self._by_id.values())

    def exists_by_phone(self, phone: PhoneNumber) -> bool:
        return any(u.phone == phone for u in self._by_id.values())

    def save(self, user: User) -> None:
        self._by_id[user.id] = user

    def delete(self, user: User) -> None:
        self._by_id.pop(user.id, None)


class FakePasswordHasher:
    """Deterministic ``PasswordHasher`` fake (no real cryptography)."""

    def hash(self, password: str) -> PasswordHash:
        return PasswordHash.from_hash(f"$argon2id$v=19$m=1$t=1$p=1${password}")

    def verify(self, password: str, hash: PasswordHash) -> bool:
        return hash.encoded_hash.endswith(f"${password}")

    def needs_rehash(self, hash: PasswordHash) -> bool:
        return hash.needs_migration()


class FakeEmailGateway:
    """Recording ``EmailGateway`` fake."""

    def __init__(self) -> None:
        self.sent: list[tuple[str, Email]] = []

    def send_verification_email(self, *, email: Email, full_name: FullName, verification_url: str, locale: Locale) -> None:
        self.sent.append(("verification", email))

    def send_password_reset(
        self,
        *,
        email: Email,
        full_name: FullName,
        reset_url: str,
        expires_at: datetime,
        locale: Locale,
    ) -> None:
        self.sent.append(("reset", email))


class FakeSmsGateway:
    """Recording ``SmsGateway`` fake."""

    def __init__(self) -> None:
        self.sent: list[tuple[PhoneNumber, str]] = []

    def send_verification_code(self, *, phone: PhoneNumber, code: str) -> None:
        self.sent.append((phone, code))


class FakeNotificationGateway:
    """Recording ``NotificationGateway`` fake."""

    def __init__(self) -> None:
        self.sent: list[tuple[UserId, str]] = []

    def notify(self, *, recipient: UserId, subject: str, body: str, locale: Locale) -> None:
        self.sent.append((recipient, subject))


class FakeClock:
    """Frozen ``Clock`` fake returning a fixed instant."""

    def __init__(self, moment: datetime) -> None:
        self._moment = moment

    def now(self) -> datetime:
        return self._moment

    def utcnow(self) -> datetime:
        return self._moment.astimezone(UTC)


class FakeUuidGenerator:
    """``UuidGenerator`` fake producing fresh UUID v7 values."""

    def new(self) -> uuid.UUID:
        return UserId.generate().value


class FakeEventPublisher:
    """Recording ``EventPublisher`` fake."""

    def __init__(self) -> None:
        self.published: list[DomainEvent] = []

    def publish(self, events: Sequence[DomainEvent]) -> None:
        self.published.extend(events)


class FakeVerificationTokenService:
    """Reversible ``VerificationTokenService`` fake."""

    def __init__(self) -> None:
        self._issued: dict[str, VerificationToken] = {}

    def issue_link(self, *, user_id: UserId, issued_at: datetime) -> str:
        token = f"{user_id.json()}|{issued_at.isoformat()}"
        self._issued[token] = VerificationToken(user_id=user_id, issued_at=issued_at)
        return f"https://vt.example/verify-email?token={token}"

    def verify(self, token: str) -> VerificationToken:
        return self._issued[token]


# ---------------------------------------------------------------------------
# Static type-correctness checks (verified by mypy --strict)
# ---------------------------------------------------------------------------


def _accepts_user_repository(repo: UserRepository) -> UserRepository:
    return repo


def _accepts_password_hasher(hasher: PasswordHasher) -> PasswordHasher:
    return hasher


def _accepts_email_gateway(gateway: EmailGateway) -> EmailGateway:
    return gateway


def _accepts_sms_gateway(gateway: SmsGateway) -> SmsGateway:
    return gateway


def _accepts_notification_gateway(gateway: NotificationGateway) -> NotificationGateway:
    return gateway


def _accepts_clock(clock: Clock) -> Clock:
    return clock


def _accepts_uuid_generator(generator: UuidGenerator) -> UuidGenerator:
    return generator


def _accepts_event_publisher(publisher: EventPublisher) -> EventPublisher:
    return publisher


def _accepts_verification_token_service(
    service: VerificationTokenService,
) -> VerificationTokenService:
    return service


# Binding each fake to its port type is itself the static conformance assertion.
_REPO: UserRepository = _accepts_user_repository(FakeUserRepository())
_HASHER: PasswordHasher = _accepts_password_hasher(FakePasswordHasher())
_EMAIL: EmailGateway = _accepts_email_gateway(FakeEmailGateway())
_SMS: SmsGateway = _accepts_sms_gateway(FakeSmsGateway())
_NOTIFY: NotificationGateway = _accepts_notification_gateway(FakeNotificationGateway())
_CLOCK: Clock = _accepts_clock(FakeClock(NOW))
_UUIDS: UuidGenerator = _accepts_uuid_generator(FakeUuidGenerator())
_PUBLISHER: EventPublisher = _accepts_event_publisher(FakeEventPublisher())
_VERIFY_TOKENS: VerificationTokenService = _accepts_verification_token_service(FakeVerificationTokenService())


# ---------------------------------------------------------------------------
# Runtime protocol-compatibility checks
# ---------------------------------------------------------------------------


class TestProtocolCompatibility:
    def test_fakes_satisfy_their_ports(self) -> None:
        assert isinstance(FakeUserRepository(), UserRepository)
        assert isinstance(FakePasswordHasher(), PasswordHasher)
        assert isinstance(FakeEmailGateway(), EmailGateway)
        assert isinstance(FakeSmsGateway(), SmsGateway)
        assert isinstance(FakeNotificationGateway(), NotificationGateway)
        assert isinstance(FakeClock(NOW), Clock)
        assert isinstance(FakeUuidGenerator(), UuidGenerator)
        assert isinstance(FakeEventPublisher(), EventPublisher)
        assert isinstance(FakeVerificationTokenService(), VerificationTokenService)

    def test_incomplete_repository_does_not_satisfy_port(self) -> None:
        class PartialRepository:
            def get(self, user_id: UserId) -> User | None:
                return None

        # Missing get_by_email/save/delete/... — structurally not a UserRepository.
        assert not isinstance(PartialRepository(), UserRepository)

    def test_object_missing_gateway_methods_is_not_a_gateway(self) -> None:
        assert not isinstance(object(), EmailGateway)
        assert not isinstance(object(), Clock)


# ---------------------------------------------------------------------------
# Behavioural smoke checks — the fakes are usable through the port surface
# ---------------------------------------------------------------------------


class TestPortsAreUsable:
    def test_repository_round_trips_an_aggregate(self) -> None:
        repo: UserRepository = FakeUserRepository()
        user = _make_user()

        assert repo.get(user.id) is None
        assert not repo.exists(user.id)

        repo.save(user)

        assert repo.exists(user.id)
        assert repo.exists_by_email(user.email)
        assert repo.get(user.id) is user
        assert repo.get_by_email(user.email) is user

        repo.delete(user)
        assert repo.get(user.id) is None

    def test_password_hasher_hash_verify_cycle(self) -> None:
        hasher: PasswordHasher = FakePasswordHasher()
        digest = hasher.hash("Sup3rSecret!")

        assert isinstance(digest, PasswordHash)
        assert hasher.verify("Sup3rSecret!", digest)
        assert not hasher.verify("wrong", digest)
        assert hasher.needs_rehash(digest) is False

    def test_gateways_record_deliveries(self) -> None:
        email: EmailGateway = FakeEmailGateway()
        sms: SmsGateway = FakeSmsGateway()
        notify: NotificationGateway = FakeNotificationGateway()
        recipient = UserId.generate()

        email.send_verification_email(
            email=Email("a@example.com"),
            full_name=FullName.of("Ann", "Lee"),
            verification_url="https://vt.example/verify?t=x",
            locale=Locale.default(),
        )
        sms.send_verification_code(phone=PhoneNumber("+79991234567"), code="123456")
        notify.notify(
            recipient=recipient,
            subject="Signed in",
            body="A new sign-in was detected.",
            locale=Locale.default(),
        )

        assert isinstance(email, FakeEmailGateway) and email.sent == [("verification", Email("a@example.com"))]
        assert isinstance(sms, FakeSmsGateway) and sms.sent[0][1] == "123456"
        assert isinstance(notify, FakeNotificationGateway) and notify.sent[0][0] == recipient

    def test_clock_returns_aware_datetimes(self) -> None:
        clock: Clock = FakeClock(NOW)
        assert clock.now().tzinfo is not None
        assert clock.utcnow().utcoffset() == UTC.utcoffset(None)

    def test_uuid_generator_produces_uuid_v7(self) -> None:
        generator: UuidGenerator = FakeUuidGenerator()
        value = generator.new()
        assert isinstance(value, uuid.UUID)
        assert value.version == 7

    def test_event_publisher_collects_events(self) -> None:
        publisher: EventPublisher = FakeEventPublisher()
        _, events = User.register(
            user_id=UserId.generate(),
            email=Email("new@example.com"),
            full_name=FullName.of("New", "User"),
            password_hash=_HASH,
            now=NOW,
        )

        publisher.publish(events)
        publisher.publish([])  # empty sequence is a valid no-op

        assert isinstance(publisher, FakeEventPublisher)
        assert publisher.published == events
