"""Every line a person reads, in one file.

Support copy gets rewritten far more often than support logic does — usually right after
someone misreads it. Keeping it here means changing a sentence never means opening a handler.
"""

# --- the person's side ----------------------------------------------------

GREETING = (
    "Здравствуйте! Это техподдержка платформы «Взлёт талантов».\n\n"
    "Опишите здесь свой вопрос — текстом, фото, скриншотом, голосовым, как удобно. "
    "Я отвечу в этом же чате.\n\n"
    "Сначала представьтесь, пожалуйста: как к вам обращаться?"
)

GREETING_BACK = "Снова здравствуйте! Пишите вопрос — я на связи."

ASK_NAME = "Как к вам обращаться? Напишите имя или нажмите кнопку ниже."

# The phone is asked for once, at the start, and never demanded: a question that turns out to be
# answerable in two lines of text should not first require someone to hand over their number.
ASK_PHONE = (
    "Спасибо, {name}!\n\n"
    "Оставьте номер телефона — он нужен только на случай, если вопрос быстрее решить звонком. "
    "Нажмите кнопку ниже или просто напишите номер."
)

ASK_PHONE_AGAIN = "Похоже, вопрос быстрее разобрать голосом. Оставьте, пожалуйста, номер телефона — нажмите кнопку ниже или напишите его сообщением."

BTN_SHARE_PHONE = "📱 Отправить мой номер"
BTN_SKIP = "Пропустить"

PHONE_SAVED = "Записал: {phone}.\n\nТеперь опишите вопрос — отвечу здесь же."
PHONE_SKIPPED = "Хорошо, обойдёмся без телефона.\n\nОпишите вопрос — отвечу здесь же."
PHONE_UNCLEAR = "Это не похоже на номер. Напишите его в виде +7 900 000-00-00 или нажмите кнопку ниже."

NAME_SAVED_LATER = "Записал, спасибо."

# Sent once, right after the first message actually reaches the support group — so the person
# knows their message did not fall into a void, and knows where the answer will arrive.
FIRST_RELAYED = "Принял. Отвечу в этом чате — уведомление придёт сюда же."

HELP = (
    "Просто напишите сюда, что случилось. Чем подробнее, тем быстрее разберёмся:\n"
    "• что вы делали и что пошло не так;\n"
    "• скриншот или фото экрана;\n"
    "• название конкурса или номера, если вопрос про них.\n\n"
    "Команды: /start — начать заново, /help — эта подсказка."
)

CLOSED = "Вопрос закрыт. Если появится что-то ещё — просто напишите сюда, я снова на связи."

# --- the support group's side ---------------------------------------------

CARD = '👤 <b>{name}</b>\n📱 {phone}\n✉️ {username}\n🆔 <a href="tg://user?id={tg_id}">{tg_id}</a>'

CARD_NO_PHONE = "контакт не оставлен"
CARD_NO_USERNAME = "без @username"

TOPIC_NO_PHONE = "нет контакта"

DELIVERY_BLOCKED = "⚠️ Не доставлено: человек заблокировал бота. Позвоните или напишите на почту."
DELIVERY_FAILED = "⚠️ Не доставлено: {error}"

UNKNOWN_TOPIC = "Эта тема ни к кому не привязана — отправлять некуда."
BANNED_NOTICE = "🚫 Обращения от этого человека больше не пересылаются. Вернуть — /unban."
UNBANNED_NOTICE = "✅ Обращения снова пересылаются."
CONTACT_REQUESTED = "Попросил у человека номер телефона."
CLOSED_NOTICE = "Тема закрыта. Напишет снова — откроется сама."
BLOCKED_BY_USER = "🚫 Человек заблокировал бота — сообщения ему не дойдут."

GROUP_COMMANDS = (
    "Команды внутри темы:\n"
    "/contact — попросить у человека телефон\n"
    "/info — карточка с контактами\n"
    "/close — закрыть обращение\n"
    "/ban, /unban — перестать/снова принимать от него сообщения"
)

# --- setup mode -----------------------------------------------------------

SETUP_ID = "id этого чата: <code>{chat_id}</code>\n\nПропишите его в <code>SUPPORT_BOT_GROUP_ID</code> и перезапустите бота."

SETUP_HINT = (
    "Бот ещё не настроен: не задан <code>SUPPORT_BOT_GROUP_ID</code>.\n\n"
    "Добавьте бота в приватную супергруппу с включёнными «Темами», дайте права администратора "
    "и отправьте там <code>/id</code>."
)

# --- when the bot itself fails --------------------------------------------

TROUBLE_PERSON = "Что-то сломалось на моей стороне — сообщение не ушло. Отправьте его ещё раз через минуту."
TROUBLE_OPERATOR = "⚠️ Сбой на стороне бота — сообщение не отправлено. Повторите через минуту."
