from support_bot.storage import STAGE_READY, Storage


async def test_first_contact_creates_a_row(db: Storage) -> None:
    person = await db.seen(1, "anna", "Анна")

    assert person.tg_id == 1
    assert person.topic_id is None
    assert person.stage == "new"
    assert not person.banned


async def test_telegram_name_is_refreshed_but_the_answers_are_not(db: Storage) -> None:
    await db.seen(1, "anna", "Анна")
    await db.set_name(1, "Анна Петрова")
    await db.set_phone(1, "+79130000000")

    person = await db.seen(1, "anna_new", "Анна 🌸")

    assert person.tg_name == "Анна 🌸"
    assert person.username == "anna_new"
    assert person.name == "Анна Петрова"
    assert person.phone == "+79130000000"


async def test_a_topic_finds_its_person(db: Storage) -> None:
    await db.seen(1, "anna", "Анна")
    await db.attach_topic(1, 42)

    found = await db.by_topic(42)

    assert found is not None
    assert found.tg_id == 1
    assert await db.by_topic(43) is None


async def test_a_deleted_topic_is_forgotten_so_the_next_message_makes_a_new_one(db: Storage) -> None:
    await db.seen(1, "anna", "Анна")
    await db.attach_topic(1, 42)
    await db.set_card(1, 7)

    await db.detach_topic(1)

    person = await db.get(1)
    assert person is not None
    assert person.topic_id is None
    assert person.card_msg_id is None


async def test_a_reply_finds_the_message_it_answers(db: Storage) -> None:
    await db.seen(1, "anna", "Анна")
    await db.remember_relay(topic_msg_id=555, tg_id=1, user_msg_id=9)

    assert await db.original_of(555) == 9
    assert await db.original_of(556) is None


async def test_display_name_falls_back_all_the_way_to_the_id(db: Storage) -> None:
    nameless = await db.seen(483920, "", "")
    assert nameless.display_name == "id 483920"

    await db.set_name(483920, "Анна Петрова")
    named = await db.get(483920)
    assert named is not None
    assert named.display_name == "Анна Петрова"

    await db.set_stage(483920, STAGE_READY)
    assert (await db.get(483920)).stage == STAGE_READY  # type: ignore[union-attr]


async def test_telegram_ids_larger_than_a_32_bit_integer_survive(db: Storage) -> None:
    """Telegram ids passed 2^31 years ago; a column narrower than BIGINT would reject a real user."""
    huge = 7_500_000_000

    person = await db.seen(huge, "anna", "Анна")
    await db.attach_topic(huge, 9_000_000_001)

    found = await db.by_topic(9_000_000_001)
    assert person.tg_id == huge
    assert found is not None
    assert found.tg_id == huge


async def test_the_flags_come_back_as_booleans(db: Storage) -> None:
    await db.seen(1, "anna", "Анна")

    await db.set_banned(1, banned=True)
    await db.set_closed(1, closed=True)
    banned = await db.get(1)

    assert banned is not None
    assert banned.banned is True
    assert banned.closed is True

    await db.set_banned(1, banned=False)
    unbanned = await db.get(1)
    assert unbanned is not None
    assert unbanned.banned is False
