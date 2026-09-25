"""Setup mode: what the bot does before it knows which group to work in.

A supergroup's id is not visible anywhere in the Telegram clients, and the usual workaround is
adding some third-party bot to read it. Refusing to boot without it would make this bot useless
for the one job that could supply it — so with `SUPPORT_BOT_GROUP_ID` unset it starts anyway and
does nothing but report ids.
"""

from aiogram import F, Router
from aiogram.enums import ChatType
from aiogram.filters import Command
from aiogram.types import Message

from support_bot import texts

router = Router(name="setup")


@router.message(Command("id"))
async def on_id(message: Message) -> None:
    await message.reply(texts.SETUP_ID.format(chat_id=message.chat.id))


# Only in private chats: an unconfigured bot sitting in a group should stay quiet, not reply to
# every message posted while somebody sorts the configuration out.
@router.message(F.chat.type == ChatType.PRIVATE)
async def on_anything_else(message: Message) -> None:
    await message.reply(texts.SETUP_HINT)
