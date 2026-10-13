"""How a programme's instants become the text a person reads.

One module, because the same minute has to come out of three places identically: the
cells of a published link, the cells of an exported table, and the "Начало: 10:00" line
on the PDF. They are rendered at different layers, and a second copy of this rule is how
a link and a printout end up disagreeing about when the festival starts.

**Why a named zone rather than ``strftime`` on the stored instant.** Instants are stored
in UTC (``USE_TZ``), and ``DJANGO_TIME_ZONE`` is UTC in every environment, so formatting
the stored value directly prints UTC - three hours behind the people reading it. The
organizer types "10:00" in their own zone, the browser sends the instant, the constructor
renders it back in the browser's zone and reads 10:00 - and the link and the PDF, rendered
on the server, read 07:00. Naming the zone here is what makes all three agree.
"""

from __future__ import annotations

from datetime import datetime
from typing import Final
from zoneinfo import ZoneInfo

__all__ = ["DISPLAY_TZ", "clock", "day"]

#: The zone every programme is shown in - the same one the platform's letters use.
#: The festivals this platform runs are held in it, and a programme is read by people
#: standing in the hall, not by whoever happens to have opened it from abroad.
DISPLAY_TZ: Final = ZoneInfo("Europe/Minsk")


def clock(moment: datetime | None) -> str:
    """A time of day as ``10:04``, or blank when the programme has no start time yet.

    A naive datetime is taken as already being local: nothing in this context produces
    one, and guessing UTC for it would reintroduce exactly the shift this module exists
    to remove.
    """
    if moment is None:
        return ""
    local = moment.astimezone(DISPLAY_TZ) if moment.tzinfo is not None else moment
    return local.strftime("%H:%M")


#: Russian month names in the genitive, which is the case a date is read in
#: («1 августа»). ``strftime("%B")`` gives the nominative and depends on the server's
#: locale being installed, neither of which is true here.
_MONTHS: Final = (
    "января",
    "февраля",
    "марта",
    "апреля",
    "мая",
    "июня",
    "июля",
    "августа",
    "сентября",
    "октября",
    "ноября",
    "декабря",
)


def day(moment: datetime | None) -> str:
    """A whole moment as ``1 августа в 10:00``, or blank when there is none.

    What a letter says, as opposed to what a table cell says: a cell sits in a column
    headed «Время» on a page that already names the day, and a letter arrives on its own
    with no such context.
    """
    if moment is None:
        return ""
    local = moment.astimezone(DISPLAY_TZ) if moment.tzinfo is not None else moment
    return f"{local.day} {_MONTHS[local.month - 1]} в {local.strftime('%H:%M')}"
