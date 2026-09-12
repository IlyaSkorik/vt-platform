"""Application ports (contracts) required by Voting use cases.

Pure :class:`typing.Protocol` seams (ARCH-001 §7.3, Dependency Inversion). A use
case depends only on these; concrete adapters live under ``infrastructure/`` and
are injected at composition time. **Framework-free**: standard library only.

Two of these are worth a word.

:class:`VoterIdentity` is how a request becomes a pair of opaque keys. The use case
must not know that the answer comes from a cookie and an address prefix, because
the moment it does, changing how voters are recognized — adding an SMS tier, say —
becomes a change to the voting rules rather than to one adapter.

:class:`NomineeCatalog` is this context's window onto a festival that *does* live
on the platform: the programme rows a ballot can be seeded from. It returns flat
values in this context's language, so everything outward of it is written as if
the nominees simply arrived as data — which, for a standalone ballot, they did.
"""

from __future__ import annotations

import uuid
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime
from typing import Protocol, runtime_checkable

from apps.voting.domain.entities import Ballot
from apps.voting.domain.vote import NetworkKey, VoterKey

__all__ = [
    "BallotRepository",
    "CatalogNominee",
    "Clock",
    "NomineeCatalog",
    "SlugFactory",
    "UuidGenerator",
    "VoteRepository",
    "VoterIdentity",
    "VoterTokens",
]


@runtime_checkable
class Clock(Protocol):
    """Port: the current instant, always timezone-aware UTC."""

    def utcnow(self) -> datetime: ...


@runtime_checkable
class UuidGenerator(Protocol):
    """Port: fresh time-ordered identifiers."""

    def new(self) -> uuid.UUID: ...


@runtime_checkable
class SlugFactory(Protocol):
    """Port: mint a candidate public slug (the caller checks it is free)."""

    def new_slug(self) -> str: ...


@runtime_checkable
class BallotRepository(Protocol):
    """Port: persistence & retrieval of :class:`Ballot` aggregates."""

    def get(self, ballot_id: uuid.UUID) -> Ballot | None: ...

    def find_by_slug(self, slug: str) -> Ballot | None: ...

    def slug_exists(self, slug: str) -> bool: ...

    def list_for_organization(self, organization_id: uuid.UUID, *, competition_id: uuid.UUID | None = None) -> Sequence[Ballot]: ...

    def save(self, ballot: Ballot) -> None: ...

    def soft_delete(self, ballot: Ballot, *, now: datetime) -> None: ...


@runtime_checkable
class VoteRepository(Protocol):
    """Port: the append-only record of cast votes."""

    def cast(
        self,
        *,
        vote_id: uuid.UUID,
        ballot_id: uuid.UUID,
        nominee_id: uuid.UUID,
        voter: VoterKey,
        network: NetworkKey,
        bucket: int,
        now: datetime,
    ) -> None: ...

    def spent_by_voter(self, *, ballot_id: uuid.UUID, voter: VoterKey, bucket: int) -> int: ...

    def chosen_by_voter(self, *, ballot_id: uuid.UUID, voter: VoterKey, bucket: int) -> set[uuid.UUID]: ...

    def sent_by_network(self, *, ballot_id: uuid.UUID, network: NetworkKey, bucket: int) -> int: ...

    def tally(self, ballot_id: uuid.UUID) -> dict[uuid.UUID, int]: ...

    def voters(self, ballot_id: uuid.UUID) -> int: ...


@dataclass(frozen=True, slots=True)
class VoterTokens:
    """Who this request is, as far as a soft identification can tell.

    ``issued`` says the voter token was minted for this request rather than
    presented by it — the caller has to hand it back in a cookie, and it is how a
    first-time visitor becomes a recognizable one.
    """

    voter: VoterKey
    network: NetworkKey
    issued: bool = False
    #: The raw token to put in the cookie, present only when ``issued``.
    raw_token: str | None = None


@runtime_checkable
class VoterIdentity(Protocol):
    """Port: turn an incoming request into the pair of keys a vote is filed under.

    Deliberately opaque to the use case. Recognizing voters more strictly later —
    a confirmed e-mail, a Telegram account, an SMS code — replaces this adapter and
    changes nothing above it.
    """

    def recognize(self, request: object, *, ballot_id: uuid.UUID) -> VoterTokens: ...


@dataclass(frozen=True, slots=True)
class CatalogNominee:
    """One act a ballot could be seeded from, in this context's own language."""

    title: str
    subtitle: str = ""
    number: int | None = None
    submission_id: uuid.UUID | None = None
    program_item_id: uuid.UUID | None = None


@runtime_checkable
class NomineeCatalog(Protocol):
    """Port: the acts of a festival that does live on this platform.

    Only ever consulted for a ballot that named a competition. A standalone ballot
    never reaches this, which is why its absence is not an error anywhere.
    """

    def for_program(self, program_id: uuid.UUID, *, organization_id: uuid.UUID) -> Sequence[CatalogNominee]: ...

    def programs_of(self, competition_id: uuid.UUID, *, organization_id: uuid.UUID) -> Sequence[tuple[uuid.UUID, str]]: ...
