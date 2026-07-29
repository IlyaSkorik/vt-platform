"""Result & view DTOs for the Results application layer.

Immutable, primitive-only output shapes: ids and enums as strings, instants as
:class:`~datetime.datetime`. They are the boundary in the outward direction, so no
outer layer needs the domain to read a protocol.

The organizer view and the public view are deliberately **separate shapes** rather than
one shape with fields blanked out. A published protocol is read by anyone with the link
- it is linked from a landing page - and keeping its projection its own type is what
stops an organizer-only field (an applicant's email, a row's submission id) from
leaking into it by accident later.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

__all__ = [
    "AwardOptionView",
    "ColumnView",
    "ProtocolDetailView",
    "ProtocolRowView",
    "ProtocolSummaryView",
    "ProtocolTableView",
    "PublicProtocolRowView",
    "PublicProtocolView",
    "PublicationResultView",
    "PublishedProtocolLinkView",
]


@dataclass(frozen=True, slots=True)
class ColumnView:
    """One column of the protocol table: its stable key and its header."""

    key: str
    label: str


@dataclass(frozen=True, slots=True)
class AwardOptionView:
    """One award the jury can pick, as the dropdown offers it.

    Served from the API rather than hard-coded in the client, so the vocabulary has one
    home: adding "Специальный приз жюри" later must not need a frontend release to be
    selectable.
    """

    value: str
    label: str
    #: Rank among the kinds (0 = Гран-при). Orders the list; not a place.
    seniority: int


@dataclass(frozen=True, slots=True)
class ProtocolRowView:
    """One row as the jury's table shows it.

    ``award`` is the enum name and ``award_label`` its wording, so a client can render
    the table without a second lookup and still round-trip the value it sends back.
    ``missing_performance`` marks the one case an organizer has to be able to see: a row
    whose act has since been withdrawn from the competition entirely.
    """

    id: str
    number: int
    submission_id: str
    title: str
    award: str | None
    award_label: str | None
    lead_participant: str | None = None
    participants: tuple[str, ...] = ()
    teachers: tuple[str, ...] = ()
    nomination: str | None = None
    discipline: str | None = None
    age_category: str | None = None
    participant_group: str | None = None
    participation_format: str | None = None
    organization: str | None = None
    missing_performance: bool = False


@dataclass(frozen=True, slots=True)
class ProtocolSummaryView:
    """A protocol as it appears in the list of a competition's protocols."""

    id: str
    competition_id: str
    nomination_id: str
    nomination: str | None
    name: str
    status: str
    row_count: int
    decided_count: int
    revision: int
    slug: str | None
    path: str | None
    published_at: datetime | None
    has_unpublished_changes: bool
    created_at: datetime
    updated_at: datetime


@dataclass(frozen=True, slots=True)
class ProtocolDetailView:
    """One protocol in full: its rows, its results, and its publication state."""

    id: str
    competition_id: str
    nomination_id: str
    nomination: str | None
    competition_title: str | None
    name: str
    status: str
    rows: tuple[ProtocolRowView, ...]
    #: Every column the table can carry, in canonical order - what the jury's screen
    #: renders its header from and what the publish dialog offers to choose between.
    available_columns: tuple[ColumnView, ...]
    #: The columns the published page shows (the default set until one is chosen).
    public_columns: tuple[ColumnView, ...]
    #: The award vocabulary, so the dropdown is served rather than duplicated.
    award_options: tuple[AwardOptionView, ...]
    revision: int
    slug: str | None
    path: str | None
    published_at: datetime | None
    has_unpublished_changes: bool
    seeded_from_program_id: str | None
    created_at: datetime
    updated_at: datetime
    version: int


@dataclass(frozen=True, slots=True)
class PublicationResultView:
    """What one publication did, beyond changing the protocol's status.

    Publishing is three effects in one action - the page, the diplomas, the mail - and
    an organizer who pressed the button needs to see all three land. ``diplomas_awarded``
    and ``letters_sent`` are counts rather than lists because that is what the
    confirmation says; the diploma register itself is the place to audit individual rows.
    """

    protocol: ProtocolDetailView
    diplomas_awarded: int
    diplomas_created: int
    #: Awarded rows whose diploma could not be resolved at all - the gap an organizer
    #: has to know about, since those participants have a result and no document.
    diplomas_missing: int
    letters_sent: int
    letters_skipped: int


@dataclass(frozen=True, slots=True)
class ProtocolTableView:
    """A protocol as a plain table, for a renderer that knows nothing about protocols.

    The same shape the public page is built from: a heading, the chosen columns, and one
    row of already-rendered cells each.
    """

    title: str
    subtitle: str | None
    columns: tuple[ColumnView, ...]
    rows: tuple[tuple[str, ...], ...]


@dataclass(frozen=True, slots=True)
class PublicProtocolRowView:
    """One row of a public protocol table.

    ``cells`` is aligned with the view's :attr:`PublicProtocolView.columns` - a column
    the organizer did not publish produces no cell at all, so a hidden column cannot be
    read off the wire. There is no id and no submission id here on purpose: a public
    protocol is a document, not an API onto the entries behind it.
    """

    cells: tuple[str, ...]
    #: The award's enum name, carried for styling only (Гран-при is drawn differently).
    #: The wording itself is already in ``cells`` when the award column is published.
    award: str | None = None


@dataclass(frozen=True, slots=True)
class PublicProtocolView:
    """What a public protocol link resolves to: a table, and what it was cut to."""

    name: str
    slug: str
    competition_title: str | None
    nomination: str | None
    revision: int
    published_at: datetime | None
    columns: tuple[ColumnView, ...]
    rows: tuple[PublicProtocolRowView, ...]


@dataclass(frozen=True, slots=True)
class PublishedProtocolLinkView:
    """One entry in a competition's "Результаты" section.

    All the landing page needs: what the protocol is called, when it was published, and
    where to read it. Deliberately no counts and no awards - a landing page lists
    documents, and the document itself is one click away.
    """

    nomination: str | None
    name: str
    slug: str
    path: str
    revision: int
    published_at: datetime | None
