"""The operator's side: everything that happens inside the support supergroup.

One topic per person. Writing in a topic answers that person; the commands below cover the few
things the conversation itself cannot express. Nothing here is addressed to the person unless
it is a message an operator typed — the bot's own remarks stay in the group.
"""

from __future__ import annotations

import logging

from aiogram import Bot, F, Router
from aiogram.enums import ChatType
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError
from aiogram.filters import Command
from aiogram.types import Message, ReactionTypeEmoji

from support_bot import texts
from support_bot.config import Settings
from support_bot.keyboards import phone_keyboard
from support_bot.storage import STAGE_AWAITING_PHONE, Person, Storage
from support_bot.topics import card_text, deliver_to_person

logger = logging.getLogger(__name__)

router = Router(name="forum")
router.message.filter(F.chat.type.in_({ChatType.GROUP, ChatType.SUPERGROUP}))

# Service messages Telegram posts into a forum. They carry no text an operator wrote, and
# relaying them would send "тема закрыта" to the person as if it were an answer.
NOT_A_SERVICE_MESSAGE = (
    ~F.forum_topic_created
    & ~F.forum_topic_edited
    & ~F.forum_topic_closed
    & ~F.forum_topic_reopened
    & ~F.pinned_message
    & ~F.new_chat_members
    & ~F.left_chat_member
)


# Topics already told they belong to nobody. In memory on purpose: the only cost of forgetting
# on restart is saying it once more, and it saves a table for something with no consequences.
_TOLD_ABOUT: set[int] = set()


async def _person_of(message: Message, db: Storage, *, always_say_so: bool = True) -> Person | None:
    """The person this topic belongs to, saying so in the topic when there is none.

    A command deserves an answer every time. A plain message does not: a topic somebody opened in
    this group for their own notes would otherwise be answered with the same complaint forever —
    and answering it once is enough to learn that nothing written there reaches anyone.
    """
    thread = message.message_thread_id
    if thread is None:
        return None

    person = await db.by_topic(thread)
    if person is None and (always_say_so or thread not in _TOLD_ABOUT):
        _TOLD_ABOUT.add(thread)
        await message.reply(texts.UNKNOWN_TOPIC)
    return person


@router.message(Command("help"), F.message_thread_id)
async def on_help(message: Message) -> None:
    await message.reply(texts.GROUP_COMMANDS)


@router.message(Command("info"), F.message_thread_id)
async def on_info(message: Message, db: Storage) -> None:
    person = await _person_of(message, db)
    if person is not None:
        await message.reply(card_text(person))


@router.message(Command("contact"), F.message_thread_id)
async def on_contact(message: Message, bot: Bot, db: Storage) -> None:
    """Ask the person for a phone number — for when the answer clearly needs a call."""
    person = await _person_of(message, db)
    if person is None:
        return
    try:
        await bot.send_message(chat_id=person.tg_id, text=texts.ASK_PHONE_AGAIN, reply_markup=phone_keyboard())
    except TelegramForbiddenError:
        await message.reply(texts.BLOCKED_BY_USER)
        return
    await db.set_stage(person.tg_id, STAGE_AWAITING_PHONE)
    await message.reply(texts.CONTACT_REQUESTED)


@router.message(Command("close"), F.message_thread_id)
async def on_close(message: Message, bot: Bot, db: Storage, settings: Settings) -> None:
    person = await _person_of(message, db)
    if person is None or person.topic_id is None:
        return

    # Told, not just filed away: a closed ticket the person never heard about is how they end up
    # writing to the organiser again — the exact loop this bot exists to break.
    try:
        await bot.send_message(chat_id=person.tg_id, text=texts.CLOSED)
    except TelegramForbiddenError:
        await message.reply(texts.BLOCKED_BY_USER)

    await db.set_closed(person.tg_id, closed=True)
    try:
        await bot.close_forum_topic(chat_id=settings.group_id, message_thread_id=person.topic_id)
    except TelegramBadRequest as error:
        logger.warning("could not close topic %s: %s", person.topic_id, error)
    await message.reply(texts.CLOSED_NOTICE)


@router.message(Command("ban"), F.message_thread_id)
async def on_ban(message: Message, db: Storage) -> None:
    person = await _person_of(message, db)
    if person is not None:
        await db.set_banned(person.tg_id, banned=True)
        await message.reply(texts.BANNED_NOTICE)


@router.message(Command("unban"), F.message_thread_id)
async def on_unban(message: Message, db: Storage) -> None:
    person = await _person_of(message, db)
    if person is not None:
        await db.set_banned(person.tg_id, banned=False)
        await message.reply(texts.UNBANNED_NOTICE)


@router.message(F.message_thread_id, ~F.from_user.is_bot, NOT_A_SERVICE_MESSAGE)
async def on_reply(message: Message, bot: Bot, db: Storage, settings: Settings) -> None:
    """Anything an operator writes in a topic goes to that topic's person, as-is."""
    person = await _person_of(message, db, always_say_so=False)
    if person is None:
        return

    try:
        await deliver_to_person(bot, person, message, settings.group_id, reply_to=await _quoted_original(message, db))
    except TelegramForbiddenError:
        # Blocked, or they deleted the chat. Said plainly in the topic, where the phone number is
        # pinned two messages up — an undelivered answer that looks delivered is the worst outcome.
        await message.reply(texts.DELIVERY_BLOCKED)
        return
    except TelegramBadRequest as error:
        await message.reply(texts.DELIVERY_FAILED.format(error=error.message))
        return

    try:
        await bot.set_message_reaction(chat_id=message.chat.id, message_id=message.message_id, reaction=[ReactionTypeEmoji(emoji="\U0001f44c")])
    except TelegramBadRequest as error:
        logger.debug("could not mark %s as delivered: %s", message.message_id, error)


async def _quoted_original(message: Message, db: Storage) -> int | None:
    """If the operator replied to a copied message, the person's own message id behind it."""
    quoted = message.reply_to_message
    if quoted is None or quoted.forum_topic_created is not None:
        # Telegram points the first message of a topic at the topic-creation service message;
        # that is not a reply anyone made.
        return None
    return await db.original_of(quoted.message_id)
