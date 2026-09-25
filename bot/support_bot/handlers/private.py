"""The person's side: everything that happens in a private chat with the bot.

Two jobs, in this order of importance: get the message to a human, and — without ever standing
in the way of the first — learn who wrote it and how to phone them.

The introduction is therefore a request, never a gate. Someone whose diploma is missing an hour
before a deadline will not fill in a form first, and a support bot that insists on one simply
becomes another wall between them and the organiser — which is the exact thing this replaces.
"""

from __future__ import annotations

import logging
import re

from aiogram import Bot, F, Router
from aiogram.enums import ChatType
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import Command, CommandStart
from aiogram.types import Message, ReactionTypeEmoji, ReplyKeyboardRemove

from support_bot import texts
from support_bot.config import Settings
from support_bot.keyboards import NAME_LIMIT, name_keyboard, phone_keyboard
from support_bot.phones import format_phone, normalise_phone
from support_bot.storage import STAGE_AWAITING_NAME, STAGE_AWAITING_PHONE, STAGE_NEW, STAGE_READY, Person, Storage
from support_bot.topics import deliver_to_support, refresh_card

logger = logging.getLogger(__name__)

router = Router(name="private")
router.message.filter(F.chat.type == ChatType.PRIVATE)

# Enough digits in a reply to "leave your number" to read as an attempt at one.
PHONE_ATTEMPT_DIGITS = 7

# Everything a phone number is ever written with, and nothing a sentence needs.
PHONE_CHARACTERS = set("0123456789 +-()")


async def _seen(db: Storage, message: Message) -> Person | None:
    user = message.from_user
    if user is None:
        return None
    person = await db.seen(user.id, user.username or "", user.full_name)
    return None if person.banned else person


async def _acknowledge(bot: Bot, message: Message, *, first: bool) -> None:
    """Confirm receipt without adding a message to every exchange.

    A reaction, not a reply: someone sending eight screenshots should not get eight «принято» in
    return. The one line of text is sent only the first time, because that is the only time the
    person does not yet know the answer will arrive here.
    """
    try:
        await bot.set_message_reaction(chat_id=message.chat.id, message_id=message.message_id, reaction=[ReactionTypeEmoji(emoji="👌")])
    except TelegramBadRequest as error:
        logger.debug("could not react to %s: %s", message.message_id, error)
    if first:
        await message.answer(texts.FIRST_RELAYED, reply_markup=ReplyKeyboardRemove())


@router.message(CommandStart())
async def on_start(message: Message, db: Storage) -> None:
    person = await _seen(db, message)
    if person is None:
        return

    if person.stage == STAGE_NEW:
        await db.set_stage(person.tg_id, STAGE_AWAITING_NAME)
        await message.answer(texts.GREETING, reply_markup=name_keyboard(person.tg_name))
    elif person.stage == STAGE_AWAITING_NAME:
        await message.answer(texts.ASK_NAME, reply_markup=name_keyboard(person.tg_name))
    elif person.stage == STAGE_AWAITING_PHONE:
        await message.answer(texts.ASK_PHONE.format(name=person.display_name), reply_markup=phone_keyboard())
    else:
        await message.answer(texts.GREETING_BACK, reply_markup=ReplyKeyboardRemove())


@router.message(Command("help"))
async def on_help(message: Message) -> None:
    await message.answer(texts.HELP)


@router.message(F.contact)
async def on_contact(message: Message, bot: Bot, db: Storage, settings: Settings) -> None:
    person = await _seen(db, message)
    if person is None or message.contact is None:
        return

    contact = message.contact
    if contact.user_id is not None and message.from_user is not None and contact.user_id != message.from_user.id:
        # Somebody else's card — a parent passing on their teacher's number, say. That is content,
        # not a contact detail for this conversation.
        await _relay(message, bot, db, person.tg_id, settings)
        return

    phone = normalise_phone(contact.phone_number) or contact.phone_number
    await db.set_phone(person.tg_id, phone)
    if not person.name:
        # The phone book spelling is usually the real name, unlike the Telegram display name.
        from_contact = " ".join(part for part in (contact.first_name, contact.last_name) if part)
        if from_contact:
            await db.set_name(person.tg_id, from_contact)
    await db.set_stage(person.tg_id, STAGE_READY)
    await refresh_card(bot, db, person.tg_id, settings.group_id)
    await message.answer(texts.PHONE_SAVED.format(phone=format_phone(phone)), reply_markup=ReplyKeyboardRemove())


@router.message()
async def on_message(message: Message, bot: Bot, db: Storage, settings: Settings) -> None:
    person = await _seen(db, message)
    if person is None:
        return

    if person.stage == STAGE_AWAITING_NAME:
        await _take_the_name(message, bot, db, person, settings)
        return
    if person.stage == STAGE_AWAITING_PHONE and await _took_the_phone(message, bot, db, person, settings):
        return

    await _relay(message, bot, db, person.tg_id, settings)


async def _take_the_name(message: Message, bot: Bot, db: Storage, person: Person, settings: Settings) -> None:
    """Record the answer to «как к вам обращаться» — and pass it on anyway unless it is certainly a name.

    The trap this avoids: «не грузится фото» is sixteen characters and reads exactly like a name by
    every measure code has. Treated as one it would be filed into the title of a topic that does not
    exist yet, and the person's first message — their actual problem — would simply be gone.

    So only an exact match with the one-tap suggestion is trusted to be *just* a name. Everything
    else is saved as the name and relayed as well, at the price of the occasional topic whose first
    message is somebody's surname. That is the cheap mistake of the two.
    """
    text = (message.text or "").strip()

    if text and len(text) <= NAME_LIMIT:
        await db.set_name(person.tg_id, text)

    if text and text == person.tg_name.strip():
        await db.set_stage(person.tg_id, STAGE_AWAITING_PHONE)
        await message.answer(texts.ASK_PHONE.format(name=text), reply_markup=phone_keyboard())
        return

    await _relay(message, bot, db, person.tg_id, settings)


async def _took_the_phone(message: Message, bot: Bot, db: Storage, person: Person, settings: Settings) -> bool:
    """Returns whether the message was an answer to «оставьте номер» rather than a question."""
    text = (message.text or "").strip()
    if not text:
        return False

    if text == texts.BTN_SKIP:
        await db.set_stage(person.tg_id, STAGE_READY)
        await message.answer(texts.PHONE_SKIPPED, reply_markup=ReplyKeyboardRemove())
        return True

    phone = normalise_phone(text)
    if phone is not None:
        await db.set_phone(person.tg_id, phone)
        await db.set_stage(person.tg_id, STAGE_READY)
        await refresh_card(bot, db, person.tg_id, settings.group_id)
        await message.answer(texts.PHONE_SAVED.format(phone=format_phone(phone)), reply_markup=ReplyKeyboardRemove())
        return True

    if looks_like_a_failed_phone(text):
        await message.answer(texts.PHONE_UNCLEAR, reply_markup=phone_keyboard())
        return True

    # Not an attempt at a number — they have moved on to the actual question. So do we.
    return False


def looks_like_a_failed_phone(text: str) -> bool:
    """A mistyped number, as opposed to a sentence that happens to contain digits.

    The distinction matters: «не могу оплатить 1500 за конкурс 2026» carries eight digits, and
    counting digits alone would answer it with «это не похоже на номер» instead of relaying it.
    Nothing but the characters a phone number is written with, then.
    """
    if not set(text) <= PHONE_CHARACTERS:
        return False
    return len(re.sub(r"\D", "", text)) >= PHONE_ATTEMPT_DIGITS


async def _relay(message: Message, bot: Bot, db: Storage, tg_id: int, settings: Settings) -> None:
    """Send one of their messages on to the support group.

    The person is re-read here rather than passed in: the introduction steps above write a name or
    a phone immediately before relaying, and a topic created from a stale copy would be titled with
    the contacts the person had a moment ago — which is to say, with none.
    """
    person = await db.get(tg_id)
    if person is None:
        return

    is_first = await deliver_to_support(bot, db, person, message, settings.group_id)
    await _acknowledge(bot, message, first=is_first)

    if is_first and not person.phone:
        # They wrote before answering; ask once, now that the question is safely delivered, and
        # never again on our own initiative — `/contact` from the topic is for the rest.
        await db.set_stage(person.tg_id, STAGE_AWAITING_PHONE)
        await message.answer(texts.ASK_PHONE.format(name=person.display_name), reply_markup=phone_keyboard())
    elif person.stage != STAGE_READY:
        await db.set_stage(person.tg_id, STAGE_READY)
