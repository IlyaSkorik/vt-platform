# VT Platform — support bot

A Telegram bot that puts the people using «Взлёт талантов» in direct contact with whoever
maintains it.

The problem it removes: a participant's parent hits something broken, writes to the competition
organiser, the organiser relays it — usually a day later, usually paraphrased — and the answer
travels back the same way. Two hops, two delays, and a screenshot that never survives the trip.
Here they write to the bot and the maintainer answers them, in Telegram, where both already are.

---

## 1. How it works

Every person who writes gets **one forum topic** in a private support supergroup. Their messages
— text, photos, screenshots, voice notes, documents — are copied into that topic. Anything typed
in the topic goes back to them. That is the whole mechanism.

```
  private chat with the bot                 support supergroup («Темы» on)
  ┌────────────────────────┐                ┌──────────────────────────────────┐
  │ Анна:                  │  ──copy───▶    │ 🟢 Анна Петрова · +7 913 000-…   │
  │  не грузится фото      │                │    📌 контакты (pinned card)     │
  │  [screenshot]          │                │    не грузится фото              │
  │                        │                │    [screenshot]                  │
  │ Bot: пришлите скрин…   │  ◀──copy───    │    Ты: пришлите скрин ошибки     │
  └────────────────────────┘                └──────────────────────────────────┘
```

**The topic is the ticket.** There is no ticket table, no status column and no web interface: the
title carries who and how to phone them, the pinned card carries the contacts, and open/closed is
the topic's own state. Closing a topic closes the request; the person writing again reopens it.

**Nothing anybody sends is stored here.** Photos, screenshots, voice notes and documents are
moved with `copyMessage` — an instruction to Telegram to copy the message on its own servers. No
file is ever downloaded, written to disk or passed through this process, and no message text is
saved. The database holds one row per person (name, phone, which topic is theirs) and a map of
message ids; the conversation itself lives where it already was, in the group's history.

**Contacts are asked for, never demanded.** On `/start` the bot asks for a name and offers a
one-tap `request_contact` button for the phone. Somebody who ignores that and starts describing
their problem is not blocked — the message is relayed, the topic is titled `… · нет контакта`,
and the phone is asked for once more afterwards. `/contact` from inside the topic asks again,
which is what to use when a question turns out to need a call.

---

## 2. Setting it up

1. **Create the bot** — @BotFather → `/newbot`. Keep the token.
2. **Turn off privacy mode** is *not* needed: the bot reads group messages because it is an
   administrator there.
3. **Create a private supergroup** for support and open *Settings → Topics* («Темы»). A plain
   group will not do — the bot refuses to start without topics and says so.
4. **Add the bot as an administrator** with **«Управление темами»** (`can_manage_topics`) and the
   right to post messages.
5. **Find the group id.** Start the bot with `SUPPORT_BOT_TOKEN` set and `SUPPORT_BOT_GROUP_ID`
   left at `0`: it comes up in setup mode and answers `/id` in the group with the number to use.
   Put it in the environment and restart.

The bot verifies steps 3 and 4 on every start and exits with a plain-language error when either
is missing — both look exactly like a working setup in the Telegram UI until a message needs them.

### Environment

All keys are read from the same `.env` the backend uses; unrelated keys are ignored.

| Variable | Required | Default | What it is |
|---|---|---|---|
| `SUPPORT_BOT_TOKEN` | yes | — | The @BotFather token. |
| `SUPPORT_BOT_GROUP_ID` | yes | `0` | The support supergroup, e.g. `-1001234567890`. `0` starts setup mode. |
| `SUPPORT_BOT_DB_SCHEMA` | no | `support` | The schema its two tables live in. |
| `SUPPORT_BOT_DATABASE_URL` | no | — | Overrides the connection. Unset, the bot uses the platform's `POSTGRES_*` keys. |
| `SUPPORT_BOT_LOG_LEVEL` | no | `INFO` | Standard logging level. |

The database is the platform's. The bot reads the `POSTGRES_*` keys already in that `.env`, and
creates its `support` schema and two tables itself on first start — there is nothing to migrate
and nothing extra to provision. Point `SUPPORT_BOT_DATABASE_URL` at a dedicated role or database
to give it narrower privileges than the platform's own user.

---

## 3. Running it

```bash
# locally — any Postgres will do; the bot creates its own schema in it
uv sync
SUPPORT_BOT_TOKEN=… SUPPORT_BOT_GROUP_ID=… \
SUPPORT_BOT_DATABASE_URL=postgresql://postgres:postgres@localhost:5432/postgres \
  uv run python -m support_bot

# checks, the same ones CI runs. The storage tests need a database and say so; without one they
# skip locally and fail in CI, where SUPPORT_BOT_REQUIRE_DATABASE is set.
uv run ruff format --check . && uv run ruff check . && uv run mypy . && uv run pytest -q

# a throwaway database for the tests
docker run -d --rm --name bot-test-pg -e POSTGRES_PASSWORD=postgres -p 5432:5432 postgres:16-alpine
```

In production it is a service in `docker-compose.prod.yml` behind the `bot` profile, so a host
that has no support bot is unaffected by its existence. Turn it on for a host by putting

```
COMPOSE_PROFILES=bot
```

in that host's `.env`, next to the two `SUPPORT_BOT_*` keys. The regular deploy then brings it up
with everything else.

---

## 4. Commands

**In a private chat** — `/start` (begin, or start the introduction again), `/help`.

**Inside a topic**, for whoever is answering:

| Command | Does |
|---|---|
| `/contact` | Asks that person for a phone number, with the one-tap button. |
| `/info` | Reposts their contact card. |
| `/close` | Tells them the request is closed and closes the topic. Writing again reopens it. |
| `/ban` / `/unban` | Stops / resumes relaying from that person. |
| `/help` | The list above. |

Replying to a specific copied message sends the answer as a reply to *that* message on their
side, so a one-word answer to the third screenshot is not ambiguous.

---

## 5. Layout

```
support_bot/
  __main__.py     process entry point: polling, start-up checks, command menus
  config.py       SUPPORT_BOT_* settings
  storage.py      Postgres: who wrote in, which topic is theirs, contacts, message mapping
  topics.py       the bridge — create/rename topics, copy messages both ways
  phones.py       one way in (E.164), one way out (grouped for reading)
  keyboards.py    the two reply keyboards
  texts.py        every line a person reads
  handlers/
    private.py    the person's side
    forum.py      the support group's side
    setup.py      setup mode, before the group id is known
```

**Why a separate service and not a Django app.** Its own process, own image and own dependency
tree: no Django settings to load, no Celery, no migration to wait for on deploy, and a crash here
cannot take the API down with it. It polls rather than taking a webhook, so it needs no public
hostname, no certificate and no route through nginx — three things that break independently of
the bot. What it does share with the platform is the database.

**Why the platform's Postgres.** One database to back up and one to restore; the `pg_dump` taken
before every deploy already covers the bot, and there is no second piece of state on the host to
remember. The trade is real and worth naming: the bot is only as available as Postgres, so during
the seconds a deploy restarts the database it cannot record a new conversation. It does not fail
silently there — a handler that throws answers the person with «сообщение не ушло, отправьте ещё
раз», because a question that vanished quietly is the failure that matters.

Its two tables live in a `support` schema and are created by the bot on start-up, not by a Django
migration: no model describes them, and putting them in the platform's migration history would
couple the bot's deploy to the backend's for nothing. `\dt support.*` is the whole picture.

---

## 6. Deliberately not here

- **Any web interface.** Adding one would mean a second place to check for messages, which is how
  the two-hop relay this replaces started.
- **Canned replies, tags, SLAs, assignment.** One person answers. Every one of these is worth
  building the day that stops being true, and not before.
- **Linking a conversation to a platform account.** The phone number is in the topic title;
  matching it to a participant is a lookup the operator does when it matters.
- **A place in the build-and-push pipeline.** `.github/workflows/ci.yml` lints, types and tests
  the bot, but only the backend and frontend images are built and pushed to the registry. The bot
  is built on the host instead, by an explicit `build support-bot` step in `_deploy-stack.yml`
  — explicit because `up -d` builds only a *missing* image, so a host that already had one would
  otherwise keep running the old code and report a successful deploy. The step is skipped where
  the profile is off. Worth promoting to a real image when the bot is deployed often enough that
  the minute of host build time is noticeable, or when it should be releasable independently.
