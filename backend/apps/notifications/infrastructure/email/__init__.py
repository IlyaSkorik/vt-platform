"""Outbound email delivery, held to the mail provider's per-mailbox quotas."""

from __future__ import annotations

from .delivery import rebuild_message, send_bulk, send_priority, serialize_message
from .limits import (
    MessageTooLargeError,
    QuotaExceededError,
    TooManyRecipientsError,
    message_size,
    recipient_count,
    reserve_send_slot,
    seconds_until_window_resets,
    validate_message,
)

__all__ = [
    "MessageTooLargeError",
    "QuotaExceededError",
    "TooManyRecipientsError",
    "message_size",
    "rebuild_message",
    "recipient_count",
    "reserve_send_slot",
    "seconds_until_window_resets",
    "send_bulk",
    "send_priority",
    "serialize_message",
    "validate_message",
]
