"""The bridge between one person's private chat and the forum topic that holds their conversation.

A forum topic *is* the ticket here. There is no ticket table, no status field, no web interface:
the topic's title carries who and how to reach them, the pinned card carries the contacts, and
open/closed is the topic's own state. That is the whole point of choosing this shape — the
operator already lives in Telegram, and every minute spent somewhere else is the delay the
person on the other end feels.
"""

from __future__ import annotations

import logging
from html import escape

from aiogram import Bot
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError
from aiogram.types import Message, ReplyParameters

from support_bot import texts
from support_bot.phones import format_phone
from support_bot.storage import Person, Storage

logger = logging.getLogger(__name__)

# Telegram's own limit on a forum topic's name.
TITLE_LIMIT = 128


def topic_title(person: Person) -> str:
    """`Анна Петрова · +7 913 000-00-00`, or `· нет контакта` while none was left.

    The phone lives in the title rather than only in the pinned card because the title is what
    the topic list shows: scrolling that list should already answer "can I just call them?".
    """
    tail = format_phone(person.phone) if person.phone else texts.TOPIC_NO_PHONE
    return f"{person.display_name} · {tail}"[:TITLE_LIMIT]


def card_text(person: Person) -> str:
    return texts.CARD.format(
        name=escape(person.display_name),
        phone=escape(format_phone(person.phone)) if person.phone else texts.CARD_NO_PHONE,
        username=f"@{escape(person.username)}" if person.username else texts.CARD_NO_USERNAME,
        tg_id=person.tg_id,
    )


async def ensure_topic(bot: Bot, db: Storage, person: Person, group_id: int) -> Person:
    """Return the person with a live topic, creating one on first contact.

    Created lazily — on the first real message rather than on `/start` — so that curiosity taps
    on a bot link do not fill the group with empty topics.
    """
    if person.topic_id is not None:
        return person

    topic = await bot.create_forum_topic(chat_id=group_id, name=topic_title(person))
    await db.attach_topic(person.tg_id, topic.message_thread_id)

    card = await bot.send_message(chat_id=group_id, message_thread_id=topic.message_thread_id, text=card_text(person))
    await db.set_card(person.tg_id, card.message_id)
    # Pinned so the contacts stay one tap away once the conversation is long. Silently: the
    # operator is already being notified about the message that created this topic.
    try:
        await bot.pin_chat_message(chat_id=group_id, message_id=card.message_id, disable_notification=True)
    except TelegramBadRequest as error:
        logger.warning("could not pin the contact card in topic %s: %s", topic.message_thread_id, error)

    refreshed = await db.get(person.tg_id)
    assert refreshed is not None
    return refreshed


async def refresh_card(bot: Bot, db: Storage, tg_id: int, group_id: int) -> None:
    """Re-title the topic and rewrite the pinned card after contacts changed.

    Both calls are best-effort. A name that failed to reach the title is cosmetic; failing the
    message the person is waiting on because of it would not be.
    """
    person = await db.get(tg_id)
    if person is None or person.topic_id is None:
        return

    try:
        await bot.edit_forum_topic(chat_id=group_id, message_thread_id=person.topic_id, name=topic_title(person))
    except TelegramBadRequest as error:
        logger.warning("could not rename topic %s: %s", person.topic_id, error)

    if person.card_msg_id is not None:
        try:
            await bot.edit_message_text(chat_id=group_id, message_id=person.card_msg_id, text=card_text(person))
        except TelegramBadRequest as error:
            # "message is not modified" every time contacts are re-saved unchanged — expected.
            logger.debug("could not update the contact card for %s: %s", tg_id, error)


async def deliver_to_support(bot: Bot, db: Storage, person: Person, message: Message, group_id: int) -> bool:
    """Copy a person's message into their topic. Returns whether the topic had to be created."""
    is_first = person.topic_id is None
    person = await ensure_topic(bot, db, person, group_id)
    assert person.topic_id is not None

    if person.closed:
        # Someone writing again is exactly what reopening is for; nobody should have to notice
        # that the ticket had been closed.
        try:
            await bot.reopen_forum_topic(chat_id=group_id, message_thread_id=person.topic_id)
        except TelegramBadRequest as error:
            logger.debug("could not reopen topic %s: %s", person.topic_id, error)
        await db.set_closed(person.tg_id, closed=False)

    try:
        copied = await _copy_into_topic(bot, person, message, group_id)
    except TelegramBadRequest as error:
        if "thread not found" not in str(error).lower():
            raise
        # The topic was deleted by hand in the group. Start a fresh one rather than dropping
        # the message: the person is waiting, and they cannot see that anything went wrong.
        logger.warning("topic %s is gone, recreating it for %s", person.topic_id, person.tg_id)
        await db.detach_topic(person.tg_id)
        reloaded = await db.get(person.tg_id)
        assert reloaded is not None
        person = await ensure_topic(bot, db, reloaded, group_id)
        copied = await _copy_into_topic(bot, person, message, group_id)
        is_first = True

    await db.remember_relay(copied, person.tg_id, message.message_id)
    return is_first


async def _copy_into_topic(bot: Bot, person: Person, message: Message, group_id: int) -> int:
    """Copy, falling back to a forward for content `copyMessage` refuses (polls, for instance)."""
    assert person.topic_id is not None
    try:
        copied = await bot.copy_message(
            chat_id=group_id,
            message_thread_id=person.topic_id,
            from_chat_id=message.chat.id,
            message_id=message.message_id,
        )
        return copied.message_id
    except TelegramBadRequest as error:
        if "thread not found" in str(error).lower():
            raise
        logger.info("copy failed (%s), forwarding instead", error)
        forwarded = await bot.forward_message(
            chat_id=group_id,
            message_thread_id=person.topic_id,
            from_chat_id=message.chat.id,
            message_id=message.message_id,
        )
        return forwarded.message_id


async def deliver_to_person(bot: Bot, person: Person, message: Message, group_id: int, reply_to: int | None) -> None:
    """Copy an operator's message from the topic to the person. Raises if it cannot be delivered."""
    # `allow_sending_without_reply` is what keeps a deleted original from swallowing the answer:
    # the quote is nice, the reply arriving is the job.
    reply = ReplyParameters(message_id=reply_to, allow_sending_without_reply=True) if reply_to is not None else None
    await bot.copy_message(
        chat_id=person.tg_id,
        from_chat_id=group_id,
        message_id=message.message_id,
        reply_parameters=reply,
    )


async def note_in_topic(bot: Bot, group_id: int, topic_id: int, text: str) -> None:
    """A line addressed to the operator, inside the topic. Never relayed onward."""
    try:
        await bot.send_message(chat_id=group_id, message_thread_id=topic_id, text=text)
    except (TelegramBadRequest, TelegramForbiddenError) as error:
        logger.warning("could not write into topic %s: %s", topic_id, error)
