"""The mail provider's quotas, from the outside.

Every one of these limits fails silently in production if it is not respected here: the
provider refuses or throttles the message and the platform hears nothing useful, so a
participant simply never gets their letter. That makes these tests the only place the
contract is actually checked.

Contract references are the hosting agreement's §5 (see OPS-009).
"""

from __future__ import annotations

from typing import Any

import pytest
from celery.exceptions import Retry
from django.core import mail
from django.core.cache import cache
from django.core.mail import EmailMultiAlternatives
from django.test import override_settings

from apps.notifications.infrastructure.email import (
    MessageTooLargeError,
    QuotaExceededError,
    TooManyRecipientsError,
    message_size,
    recipient_count,
    reserve_send_slot,
    seconds_until_window_resets,
    send_bulk,
    send_priority,
    serialize_message,
    validate_message,
)
from apps.notifications.tasks import deliver_email


def _message(**kwargs: object) -> EmailMultiAlternatives:
    message = EmailMultiAlternatives(
        subject=kwargs.get("subject", "Заявка подана"),  # type: ignore[arg-type]
        body=kwargs.get("body", "Здравствуйте!"),  # type: ignore[arg-type]
        from_email=kwargs.get("from_email", "no-reply@vzlyot-talantov.ru"),  # type: ignore[arg-type]
        to=kwargs.get("to", ["applicant@example.com"]),  # type: ignore[arg-type]
        cc=kwargs.get("cc", []),  # type: ignore[arg-type]
        bcc=kwargs.get("bcc", []),  # type: ignore[arg-type]
    )
    message.attach_alternative("<p>Здравствуйте!</p>", "text/html")
    return message


@pytest.fixture(autouse=True)
def _clean_quota() -> None:
    """The quota lives in the shared cache; no test may inherit another's count."""
    cache.clear()


class TestRecipientLimit:
    """§5.3.4 - 50 recipients per message."""

    def test_recipients_are_counted_across_to_cc_and_bcc(self) -> None:
        message = _message(to=["a@example.com", "b@example.com"], cc=["c@example.com"], bcc=["d@example.com"])
        assert recipient_count(message) == 4

    @override_settings(MAIL_MAX_RECIPIENTS=3)
    def test_a_message_within_the_limit_is_accepted(self) -> None:
        validate_message(_message(to=["a@example.com", "b@example.com"], bcc=["c@example.com"]))

    @override_settings(MAIL_MAX_RECIPIENTS=3)
    def test_one_recipient_too_many_is_refused_before_anything_is_queued(self) -> None:
        with pytest.raises(TooManyRecipientsError):
            send_priority(_message(to=["a@example.com", "b@example.com"], bcc=["c@example.com", "d@example.com"]))
        assert mail.outbox == [], "a message the provider would refuse must not be sent"


class TestSizeLimit:
    """§5.3.1 - 100 MB per message."""

    def test_size_is_measured_on_the_assembled_message(self) -> None:
        """Not on the body: headers, the HTML alternative and encoding all count."""
        message = _message(body="x" * 1000)
        assert message_size(message) > 1000

    @override_settings(MAIL_MAX_BYTES=2000)
    def test_an_oversized_message_is_refused_locally(self) -> None:
        with pytest.raises(MessageTooLargeError):
            send_priority(_message(body="x" * 5000))
        assert mail.outbox == []

    @override_settings(MAIL_MAX_BYTES=100 * 1024 * 1024)
    def test_an_ordinary_letter_is_nowhere_near_the_limit(self) -> None:
        validate_message(_message())


class TestPerMinuteQuota:
    """§5.3.6 - 30 outgoing messages per minute per mailbox."""

    @override_settings(MAIL_RATE_LIMIT_PER_MINUTE=3)
    def test_the_allowance_is_spent_and_then_refused(self) -> None:
        for _ in range(3):
            reserve_send_slot("no-reply@vzlyot-talantov.ru", now=1_000.0)
        with pytest.raises(QuotaExceededError):
            reserve_send_slot("no-reply@vzlyot-talantov.ru", now=1_000.0)

    @override_settings(MAIL_RATE_LIMIT_PER_MINUTE=3)
    def test_the_allowance_is_per_mailbox(self) -> None:
        """Otherwise one busy sender would starve every other."""
        for _ in range(3):
            reserve_send_slot("no-reply@vzlyot-talantov.ru", now=1_000.0)
        reserve_send_slot("diplomas@vzlyot-talantov.ru", now=1_000.0)

    @override_settings(MAIL_RATE_LIMIT_PER_MINUTE=3)
    def test_the_next_minute_starts_fresh(self) -> None:
        for _ in range(3):
            reserve_send_slot("no-reply@vzlyot-talantov.ru", now=1_000.0)
        reserve_send_slot("no-reply@vzlyot-talantov.ru", now=1_060.0)

    @override_settings(MAIL_RATE_LIMIT_PER_MINUTE=0)
    def test_zero_disables_the_limiter(self) -> None:
        """What the test suite runs on, and what a provider without a quota would use."""
        for _ in range(100):
            reserve_send_slot("no-reply@vzlyot-talantov.ru", now=1_000.0)

    def test_the_retry_waits_for_the_window_rather_than_a_fixed_delay(self) -> None:
        # 1_045 is 25 seconds into its minute (1_020 = 17 × 60), so 35 are left of it.
        assert seconds_until_window_resets(now=1_045.0) == 35
        # Exactly on a boundary: a whole fresh window.
        assert seconds_until_window_resets(now=1_020.0) == 60
        # Never zero, even a fraction of a second before the window turns over - a retry
        # scheduled for "now" would spin.
        assert seconds_until_window_resets(now=1_079.9) == 1


class TestDelivery:
    def test_a_queued_message_arrives_intact(self) -> None:
        """Celery runs inline in tests, so this exercises the whole path."""
        send_priority(_message(subject="Заявка подана", to=["applicant@example.com"]))

        assert len(mail.outbox) == 1
        sent = mail.outbox[0]
        assert sent.subject == "Заявка подана"
        assert sent.to == ["applicant@example.com"]
        assert sent.alternatives[0][1] == "text/html"

    def test_a_burst_larger_than_the_allowance_still_delivers_what_it_may(self) -> None:
        """The letters inside the allowance must not be lost because the batch was too big."""
        with override_settings(MAIL_RATE_LIMIT_PER_MINUTE=3):
            delivered = 0
            for index in range(5):
                try:
                    deliver_email(serialize_message(_message(to=[f"a{index}@example.com"])))
                    delivered += 1
                except (Retry, QuotaExceededError):
                    # The limiter working: in a worker this is a `Retry` that comes back when
                    # the window resets; called directly, Celery re-raises the cause instead.
                    pass
        assert delivered == 3
        assert len(mail.outbox) == 3

    def test_attachments_are_refused_rather_than_silently_dropped(self) -> None:
        message = _message()
        message.attach("diploma.pdf", b"%PDF-1.7", "application/pdf")
        with pytest.raises(ValueError, match="Attachments"):
            send_priority(message)
        assert mail.outbox == []


class TestTwoMailboxes:
    """Two mailboxes, because the provider's allowance is counted per mailbox.

    The split is about what happens under load rather than about importance: a registration
    rush or an organizer working through eighty applications must not be able to delay
    somebody who cannot log in until their letter arrives.
    """

    @pytest.fixture(autouse=True)
    def _second_mailbox(self, settings: Any) -> None:
        settings.MAIL_BULK_FROM = "news@vzlettalantov.by"

    def test_priority_mail_leaves_by_the_first_mailbox(self) -> None:
        send_priority(_message(from_email="no-reply@vzlettalantov.by"))
        assert mail.outbox[0].from_email == "no-reply@vzlettalantov.by"

    def test_bulk_mail_is_rewritten_to_the_second(self) -> None:
        send_bulk(_message(from_email="no-reply@vzlettalantov.by"))
        assert mail.outbox[0].from_email == "news@vzlettalantov.by"

    @override_settings(MAIL_RATE_LIMIT_PER_MINUTE=2)
    def test_a_saturated_bulk_mailbox_leaves_the_priority_one_untouched(self) -> None:
        """The whole point: this is what a registration rush must not be able to do."""
        for _ in range(2):
            reserve_send_slot("news@vzlettalantov.by", now=1_000.0)
        with pytest.raises(QuotaExceededError):
            reserve_send_slot("news@vzlettalantov.by", now=1_000.0)

        # The mailbox somebody's password reset goes out by is still entirely free.
        reserve_send_slot("no-reply@vzlettalantov.by", now=1_000.0)
        reserve_send_slot("no-reply@vzlettalantov.by", now=1_000.0)

    def test_bulk_still_works_when_only_one_mailbox_is_configured(self, settings: Any) -> None:
        """A deployment that has not bought the second address must behave as before."""
        settings.MAIL_BULK_FROM = ""
        send_bulk(_message(from_email="no-reply@vzlettalantov.by"))
        assert mail.outbox[0].from_email == "no-reply@vzlettalantov.by"


class TestRouting:
    """Mail is delivered by its own worker, and that is a deployment contract.

    Measured against the provider, a message costs ~2.8 s almost entirely in opening an SSL
    connection, so a single slot tops out around 21 a minute - under the allowance it is
    supposed to be able to reach. Four slots on a dedicated queue clear it, and stop a
    password reset from waiting behind a diploma print run.

    Asserted through Celery's own router rather than by reading the setting back, so it
    fails if the routing stops being applied rather than only if somebody edits the value.
    """

    def test_mail_goes_to_the_queue_a_dedicated_worker_consumes(self) -> None:
        from config.celery import app

        route = app.amqp.router.route({}, "notifications.deliver_email")
        assert route["queue"].name == "mail", (
            "mail must stay on its own queue; a worker has to consume it (see the "
            "mail-worker service in docker-compose.yml) or nothing is delivered"
        )

    def test_other_work_stays_on_the_default_queue(self) -> None:
        """Otherwise the mail worker would end up rendering diplomas."""
        from config.celery import app

        route = app.amqp.router.route({}, "diplomas.generate_print_package")
        assert route["queue"].name != "mail"


class TestQueuePriority:
    """Two mailboxes double the send rate; they do not reorder the queue.

    With one queue a password reset still waits behind five hundred receipts, so the channel
    also carries a Celery priority. Asserted on the call rather than on the broker, because
    tests run tasks inline and there is no queue to inspect.
    """

    def test_the_worker_reserves_one_message_per_slot(self) -> None:
        """Without this the priority above is nearly decorative.

        Celery applies priority when it fetches from the queue, so a worker that has already
        reserved a batch of bulk messages runs them first whatever arrives behind them. At
        the default multiplier of 4 a four-slot mail worker holds sixteen - some 45 seconds
        of sending at the measured 2.8 s a message.
        """
        from config.celery import app

        assert app.conf.worker_prefetch_multiplier == 1

    def test_priority_and_bulk_are_queued_at_different_priorities(self, monkeypatch: pytest.MonkeyPatch) -> None:
        seen: list[int] = []

        def _capture(*_args: object, **kwargs: object) -> None:
            seen.append(int(kwargs["priority"]))  # type: ignore[call-overload]

        monkeypatch.setattr("apps.notifications.tasks.deliver_email.apply_async", _capture)
        send_priority(_message())
        send_bulk(_message())

        assert seen[0] > seen[1], "priority mail must outrank bulk in the queue"
