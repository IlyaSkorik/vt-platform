"""Settings for the support bot.

The bot reads the *same* `.env` file the backend does — one file per deployment, one place to
edit — so every key is prefixed and unknown keys are ignored rather than rejected. Without
`extra="ignore"` the fifty Django keys in that file would make the bot refuse to boot.
"""

from urllib.parse import quote

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class PostgresSettings(BaseSettings):
    """The platform's database, read from the keys the backend already defines.

    The bot stores its conversations next to everything else rather than in a file of its own:
    one database to back up, one thing to restore, and `pg_dump` before every deploy already
    covers it (OPS-008 §9).
    """

    model_config = SettingsConfigDict(env_prefix="POSTGRES_", env_file=".env", env_file_encoding="utf-8", extra="ignore")

    db: str = "vt_platform"
    user: str = "vt_platform"
    password: SecretStr = SecretStr("")
    host: str = "localhost"
    port: int = 5432

    @property
    def url(self) -> str:
        # Percent-encoded: a generated password contains `@` or `/` often enough, and either one
        # silently truncates the URL into something that connects to the wrong place.
        password = quote(self.password.get_secret_value(), safe="")
        return f"postgresql://{quote(self.user, safe='')}:{password}@{self.host}:{self.port}/{self.db}"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="SUPPORT_BOT_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # From @BotFather.
    token: SecretStr

    # The private supergroup with «Темы» enabled where the conversations land. Left at 0 the bot
    # starts in setup mode instead of refusing to boot: it answers `/id` in any group it is added
    # to, which is the only practical way to learn a supergroup's id. See README §2.
    group_id: int = 0

    # Its own schema in the platform's database. A namespace rather than a naming convention, so
    # `\dt support.*` is the whole answer to "what does the bot store" and nothing it creates can
    # ever collide with a Django table.
    db_schema: str = "support"

    # Set to point the bot at a different database or a dedicated role; otherwise it uses the
    # platform's POSTGRES_* credentials, which is what makes the default deployment zero-setup.
    database_url: str = ""

    log_level: str = "INFO"

    @property
    def is_configured(self) -> bool:
        return self.group_id != 0


def resolve_database_url(settings: Settings) -> str:
    return settings.database_url or PostgresSettings().url
