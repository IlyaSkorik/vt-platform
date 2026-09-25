"""What the bot remembers: who wrote in, which forum topic holds their conversation, and what
they left as contacts.

It lives in its own `support` schema inside the platform's Postgres — the same database the rest
of the system uses, so there is one thing to back up and one thing to restore. The schema keeps
it a namespace rather than a naming convention: nothing here can collide with a Django table, and
`\\dt support.*` is the complete answer to what the bot stores.

The tables are created on start-up rather than by a migration. There are two of them, they are
`CREATE TABLE IF NOT EXISTS`, and no Django model describes them — putting them in the platform's
migration history would couple the bot's deploy to the backend's for no benefit.

Every write commits immediately (the pool runs autocommit). The bot can be killed at any point in
a deploy, and the cost of a lost `topic_id` is a duplicated topic and a confused operator.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Self

from psycopg import AsyncConnection, sql
from psycopg.rows import class_row
from psycopg_pool import AsyncConnectionPool

# Where a person is in the «представьтесь» flow. Kept in the database rather than in aiogram's
# FSM storage because the in-memory FSM forgets everything on restart, and a deploy in the
# middle of someone typing their phone number would silently swallow it.
STAGE_NEW = "new"
STAGE_AWAITING_NAME = "awaiting_name"
STAGE_AWAITING_PHONE = "awaiting_phone"
STAGE_READY = "ready"

# Telegram ids outstrip a 32-bit integer, hence BIGINT throughout.
SCHEMA_STATEMENTS = (
    "CREATE SCHEMA IF NOT EXISTS {schema}",
    """
    CREATE TABLE IF NOT EXISTS {schema}.people (
        tg_id       BIGINT PRIMARY KEY,
        topic_id    BIGINT UNIQUE,
        card_msg_id BIGINT,
        username    TEXT        NOT NULL DEFAULT '',
        tg_name     TEXT        NOT NULL DEFAULT '',
        name        TEXT        NOT NULL DEFAULT '',
        phone       TEXT        NOT NULL DEFAULT '',
        stage       TEXT        NOT NULL DEFAULT 'new',
        banned      BOOLEAN     NOT NULL DEFAULT FALSE,
        closed      BOOLEAN     NOT NULL DEFAULT FALSE,
        created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
        updated_at  TIMESTAMPTZ NOT NULL DEFAULT now()
    )
    """,
    # Maps a message in the support group back to the message it was copied from, so that replying
    # to a particular photo in the topic arrives as a reply to that same photo on the person's
    # side. Ids are unique within a chat, so the group-side id alone identifies the row.
    """
    CREATE TABLE IF NOT EXISTS {schema}.relayed (
        topic_msg_id BIGINT PRIMARY KEY,
        tg_id        BIGINT NOT NULL,
        user_msg_id  BIGINT NOT NULL
    )
    """,
)

# Named rather than `SELECT *`: the rows are read straight into `Person`, which has no place for
# the timestamps.
COLUMNS = "tg_id, topic_id, card_msg_id, username, tg_name, name, phone, stage, banned, closed"


@dataclass(frozen=True, slots=True)
class Person:
    tg_id: int
    topic_id: int | None
    card_msg_id: int | None
    username: str
    tg_name: str
    name: str
    phone: str
    stage: str
    banned: bool
    closed: bool

    @property
    def display_name(self) -> str:
        """What to call them in the topic title: what they told us, else their Telegram name."""
        return self.name or self.tg_name or f"id {self.tg_id}"


class Storage:
    def __init__(self, pool: AsyncConnectionPool[AsyncConnection]) -> None:
        self._pool = pool

    @classmethod
    async def connect(cls, url: str, schema: str) -> Self:
        async def configure(connection: AsyncConnection) -> None:
            await connection.set_autocommit(True)
            # Set once per connection so every statement below can be written unqualified. The
            # schema name is an identifier, not a value, so it is quoted rather than parameterised.
            await connection.execute(sql.SQL("SET search_path TO {}").format(sql.Identifier(schema)))

        pool: AsyncConnectionPool[AsyncConnection] = AsyncConnectionPool(
            url,
            min_size=1,
            max_size=4,
            open=False,
            configure=configure,
            # Every deploy restarts Postgres under a bot that is still running. Checking a
            # connection before handing it out turns that into a moment's delay instead of an
            # exception on whoever happened to write during the restart.
            check=AsyncConnectionPool.check_connection,
        )
        await pool.open(wait=True, timeout=30)

        async with pool.connection() as connection:
            for statement in SCHEMA_STATEMENTS:
                await connection.execute(sql.SQL(statement).format(schema=sql.Identifier(schema)))

        return cls(pool)

    async def close(self) -> None:
        await self._pool.close()

    # --- people ---------------------------------------------------------

    async def seen(self, tg_id: int, username: str, tg_name: str) -> Person:
        """Record that this person just wrote, creating their row on first contact.

        Their Telegram name and @username are refreshed on every message: people rename
        themselves, and a topic titled with a name from six months ago helps nobody.
        """
        async with self._pool.connection() as connection, connection.cursor(row_factory=class_row(Person)) as cursor:
            await cursor.execute(
                f"""
                INSERT INTO people (tg_id, username, tg_name)
                     VALUES (%s, %s, %s)
                ON CONFLICT (tg_id) DO UPDATE SET username   = EXCLUDED.username,
                                                  tg_name    = EXCLUDED.tg_name,
                                                  updated_at = now()
                  RETURNING {COLUMNS}
                """,
                (tg_id, username, tg_name),
            )
            person = await cursor.fetchone()
        assert person is not None  # an upsert with RETURNING always yields a row
        return person

    async def get(self, tg_id: int) -> Person | None:
        return await self._one("tg_id = %s", tg_id)

    async def by_topic(self, topic_id: int) -> Person | None:
        return await self._one("topic_id = %s", topic_id)

    async def _one(self, where: str, value: int) -> Person | None:
        async with self._pool.connection() as connection, connection.cursor(row_factory=class_row(Person)) as cursor:
            await cursor.execute(f"SELECT {COLUMNS} FROM people WHERE {where}", (value,))
            return await cursor.fetchone()

    async def _update(self, tg_id: int, **fields: object) -> None:
        assignments = sql.SQL(", ").join(sql.SQL("{} = %s").format(sql.Identifier(name)) for name in fields)
        query = sql.SQL("UPDATE people SET {assignments}, updated_at = now() WHERE tg_id = %s").format(assignments=assignments)
        async with self._pool.connection() as connection:
            await connection.execute(query, (*fields.values(), tg_id))

    async def attach_topic(self, tg_id: int, topic_id: int) -> None:
        await self._update(tg_id, topic_id=topic_id, closed=False)

    async def detach_topic(self, tg_id: int) -> None:
        """Forget a topic that no longer exists, so the next message recreates one."""
        await self._update(tg_id, topic_id=None, card_msg_id=None, closed=False)

    async def set_card(self, tg_id: int, card_msg_id: int) -> None:
        await self._update(tg_id, card_msg_id=card_msg_id)

    async def set_name(self, tg_id: int, name: str) -> None:
        await self._update(tg_id, name=name)

    async def set_phone(self, tg_id: int, phone: str) -> None:
        await self._update(tg_id, phone=phone)

    async def set_stage(self, tg_id: int, stage: str) -> None:
        await self._update(tg_id, stage=stage)

    async def set_banned(self, tg_id: int, *, banned: bool) -> None:
        await self._update(tg_id, banned=banned)

    async def set_closed(self, tg_id: int, *, closed: bool) -> None:
        await self._update(tg_id, closed=closed)

    # --- message mapping ------------------------------------------------

    async def remember_relay(self, topic_msg_id: int, tg_id: int, user_msg_id: int) -> None:
        async with self._pool.connection() as connection:
            await connection.execute(
                """
                INSERT INTO relayed (topic_msg_id, tg_id, user_msg_id)
                     VALUES (%s, %s, %s)
                ON CONFLICT (topic_msg_id) DO UPDATE SET tg_id       = EXCLUDED.tg_id,
                                                         user_msg_id = EXCLUDED.user_msg_id
                """,
                (topic_msg_id, tg_id, user_msg_id),
            )

    async def original_of(self, topic_msg_id: int) -> int | None:
        """The person's own message id behind a copy sitting in the support group."""
        async with self._pool.connection() as connection, connection.cursor() as cursor:
            await cursor.execute("SELECT user_msg_id FROM relayed WHERE topic_msg_id = %s", (topic_msg_id,))
            row = await cursor.fetchone()
        return int(row[0]) if row else None
