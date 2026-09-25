from support_bot.storage import Person
from support_bot.topics import TITLE_LIMIT, card_text, topic_title


def _person(
    *,
    name: str = "Анна Петрова",
    phone: str = "+79130000000",
    username: str = "anna",
    tg_name: str = "Анна 🌸",
) -> Person:
    return Person(
        tg_id=483920,
        topic_id=None,
        card_msg_id=None,
        username=username,
        tg_name=tg_name,
        name=name,
        phone=phone,
        stage="ready",
        banned=False,
        closed=False,
    )


def test_the_title_carries_the_phone_so_the_topic_list_answers_can_i_call() -> None:
    assert topic_title(_person()) == "Анна Петрова · +7 913 000-00-00"


def test_a_missing_contact_is_visible_in_the_title() -> None:
    assert topic_title(_person(phone="", name="", tg_name="")) == "id 483920 · нет контакта"


def test_the_title_stays_within_telegrams_limit() -> None:
    assert len(topic_title(_person(name="Анна" * 100))) == TITLE_LIMIT


def test_the_card_escapes_what_people_put_in_their_names() -> None:
    card = card_text(_person(name="<b>Аня</b> & Co"))

    assert "&lt;b&gt;Аня&lt;/b&gt; &amp; Co" in card
    assert "<b>Аня</b> & Co" not in card


def test_the_card_says_plainly_when_there_is_no_way_to_call() -> None:
    card = card_text(_person(phone="", username=""))

    assert "контакт не оставлен" in card
    assert "без @username" in card
