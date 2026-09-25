"""The two reply keyboards the bot ever shows.

Reply keyboards rather than inline buttons: `request_contact` is the only way to get a verified
phone number in one tap, and it exists nowhere else.
"""

from aiogram.types import KeyboardButton, ReplyKeyboardMarkup, ReplyKeyboardRemove

from support_bot import texts

# A name is short. Anything longer than this, sent where a name was asked for, is someone who
# skipped the question and started describing their problem — so it is treated as the problem.
NAME_LIMIT = 80


def phone_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=texts.BTN_SHARE_PHONE, request_contact=True)],
            [KeyboardButton(text=texts.BTN_SKIP)],
        ],
        resize_keyboard=True,
        one_time_keyboard=True,
    )


def name_keyboard(tg_name: str) -> ReplyKeyboardMarkup | ReplyKeyboardRemove:
    """One tap to confirm the Telegram name — the answer most people would type anyway."""
    if not tg_name:
        return ReplyKeyboardRemove()
    return ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text=tg_name[:NAME_LIMIT])]], resize_keyboard=True, one_time_keyboard=True)
