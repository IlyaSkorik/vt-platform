"""Process entry point.

Long polling, not a webhook. A webhook would need a public hostname, a TLS certificate and a
route through the platform's nginx — three things that can break independently of the bot, for a
service whose entire value is being reachable when the platform is not. Polling needs an
outbound connection and nothing else.
"""

from __future__ import annotations

import asyncio
import contextlib
import logging
import signal

from aiogram import Bot, Dispatcher, F
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ChatType, ParseMode
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError, TelegramUnauthorizedError
from aiogram.types import BotCommand, BotCommandScopeAllPrivateChats, BotCommandScopeChat, ErrorEvent

from support_bot import texts
from support_bot.config import Settings, resolve_database_url
from support_bot.handlers import forum, private, setup
from support_bot.storage import Storage

logger = logging.getLogger("support_bot")

PRIVATE_COMMANDS = [
    BotCommand(command="start", description="Начать заново"),
    BotCommand(command="help", description="Как задать вопрос"),
]

GROUP_COMMANDS = [
    BotCommand(command="contact", description="Попросить телефон"),
    BotCommand(command="info", description="Карточка обратившегося"),
    BotCommand(command="close", description="Закрыть обращение"),
    BotCommand(command="ban", description="Не принимать сообщения"),
    BotCommand(command="unban", description="Снова принимать сообщения"),
]


async def check_group(bot: Bot, settings: Settings) -> None:
    """Fail loudly at start-up instead of silently on the first person's first message.

    Both mistakes below are invisible in the Telegram UI until something needs them: a supergroup
    without «Темы» and a bot without «Управление темами» look exactly like a working setup.
    """
    try:
        chat = await bot.get_chat(settings.group_id)
    except (TelegramBadRequest, TelegramForbiddenError) as error:
        raise SystemExit(f"SUPPORT_BOT_GROUP_ID={settings.group_id} is unreachable: {error}") from error

    if not chat.is_forum:
        raise SystemExit(f"«{chat.title}» has no topics enabled — turn on «Темы» in the group's settings (README §2).")

    me = await bot.get_chat_member(settings.group_id, (await bot.me()).id)
    if getattr(me, "can_manage_topics", False) is not True:
        raise SystemExit(f"the bot is not an administrator of «{chat.title}» with «Управление темами» (README §2).")

    logger.info("support group: «%s» (%s)", chat.title, settings.group_id)


async def publish_commands(bot: Bot, settings: Settings) -> None:
    """The command menu differs by audience: people see two entries, the support group sees five."""
    await bot.set_my_commands(PRIVATE_COMMANDS, scope=BotCommandScopeAllPrivateChats())
    with contextlib.suppress(TelegramBadRequest):
        await bot.set_my_commands(GROUP_COMMANDS, scope=BotCommandScopeChat(chat_id=settings.group_id))


async def on_error(event: ErrorEvent) -> None:
    """Say that a message did not go through, rather than dropping it in silence.

    Nothing retries a failed handler: aiogram logs the exception and moves on, so the person sits
    waiting for an answer to a message nobody ever saw. Now that the conversations live in the
    platform's Postgres, the likeliest cause is the database being restarted by a deploy — a
    twenty-second window in which the honest thing is to ask them to send it again.
    """
    logger.error("update %s failed", event.update.update_id, exc_info=event.exception)

    message = event.update.message
    if message is None:
        return
    text = texts.TROUBLE_PERSON if message.chat.type == ChatType.PRIVATE else texts.TROUBLE_OPERATOR
    with contextlib.suppress(TelegramBadRequest, TelegramForbiddenError):
        await message.reply(text)


async def main() -> None:
    # mypy cannot see that pydantic-settings fills every field from the environment.
    settings = Settings()  # type: ignore[call-arg]
    logging.basicConfig(level=settings.log_level.upper(), format="%(asctime)s %(levelname)-8s %(name)s: %(message)s")

    db = await Storage.connect(resolve_database_url(settings), settings.db_schema)
    bot = Bot(token=settings.token.get_secret_value(), default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    dispatcher = Dispatcher()
    dispatcher["db"] = db
    dispatcher["settings"] = settings
    dispatcher.errors.register(on_error)

    # Everything past this point runs inside the cleanup, start-up included. A token Telegram
    # rejects used to leave the HTTP session open and print a traceback about it underneath the
    # actual cause — which is the wrong thing to read first when a deploy is failing.
    try:
        if settings.is_configured:
            # Bound here rather than inside the module so the group id stays a setting: every
            # handler in `forum` then only ever sees the one group, whatever else the bot is
            # added to.
            forum.router.message.filter(F.chat.id == settings.group_id)
            dispatcher.include_router(private.router)
            dispatcher.include_router(forum.router)
            await check_group(bot, settings)
            await publish_commands(bot, settings)
        else:
            logger.warning("SUPPORT_BOT_GROUP_ID is unset — starting in setup mode, see README §2")
            dispatcher.include_router(setup.router)

        # Pending updates are kept on purpose. They are questions people asked while the bot was
        # being deployed; dropping them means someone waits for an answer to a message nobody saw.
        await bot.delete_webhook(drop_pending_updates=False)

        loop = asyncio.get_running_loop()
        for sig in (signal.SIGINT, signal.SIGTERM):
            loop.add_signal_handler(sig, lambda: asyncio.ensure_future(dispatcher.stop_polling()))

        await dispatcher.start_polling(bot)
    except TelegramUnauthorizedError as error:
        raise SystemExit("SUPPORT_BOT_TOKEN was rejected by Telegram. Check it against @BotFather — README §2.") from error
    finally:
        await db.close()
        await bot.session.close()


if __name__ == "__main__":
    with contextlib.suppress(KeyboardInterrupt):
        asyncio.run(main())
