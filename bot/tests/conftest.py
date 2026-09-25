"""A real Postgres for the storage tests.

The bot's persistence is Postgres-specific — an upsert with `RETURNING`, a schema, `now()` — so
testing it against anything else would be testing a different thing. The tests therefore need a
database; they skip rather than fail when one is not around, and CI always provides one.
"""

import os
from collections.abc import AsyncIterator

import psycopg
import pytest

from support_bot.storage import Storage

DEFAULT_URL = "postgresql://postgres:postgres@localhost:5432/postgres"

# Its own schema, so a run against a machine that also hosts a real bot cannot touch its data.
TEST_SCHEMA = "support_test"


@pytest.fixture(scope="session")
def database_url() -> str:
    """Decide once, in three seconds, whether there is a database to test against.

    A plain connection rather than the pool: the pool's job is to wait patiently for a database to
    come back, which is right in production and wrong here — it turned "no Postgres, skip" into
    thirty seconds of waiting per test.
    """
    url = os.environ.get("SUPPORT_BOT_TEST_DATABASE_URL", DEFAULT_URL)
    try:
        psycopg.connect(url, connect_timeout=3).close()
    except psycopg.OperationalError as error:
        # CI sets `SUPPORT_BOT_REQUIRE_DATABASE` and therefore fails instead of skipping. A
        # storage suite that quietly skips itself is a green build that tested nothing, and it
        # would stay green through exactly the change that breaks persistence.
        if os.environ.get("SUPPORT_BOT_REQUIRE_DATABASE"):
            raise
        pytest.skip(f"no Postgres at {url}: {error}")
    return url


@pytest.fixture
async def db(database_url: str) -> AsyncIterator[Storage]:
    storage = await Storage.connect(database_url, TEST_SCHEMA)

    # Reaching past the public API on purpose: emptying the tables is a test concern, and adding
    # a `truncate()` to `Storage` would put it one typo away from production code.
    async with storage._pool.connection() as connection:
        await connection.execute("TRUNCATE people, relayed")

    yield storage
    await storage.close()
