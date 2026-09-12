"""Composition root for the Voting bounded context.

The one place a framework-free use case is wired to its concrete adapters
(ARCH-001 §7.3, Dependency Inversion): the presentation edge asks here for an
assembled service and stays ignorant of which repository, clock or identity
adapter sits behind each port. Adapters are stateless and cheap, so they are
assembled per call.

The voter-identity adapter is the one worth knowing about: swapping
:class:`CookieVoterIdentity` for something stricter — a confirmed e-mail, a
Telegram login, an SMS code — is a change to :func:`build_voter_identity` and to
nothing else.
"""

from __future__ import annotations

from apps.voting.application.services import BallotService
from apps.voting.infrastructure.acl import DjangoNomineeCatalog
from apps.voting.infrastructure.repositories import DjangoBallotRepository, DjangoVoteRepository
from apps.voting.infrastructure.system import RandomSlugFactory, SystemClock, Uuid7Generator
from apps.voting.infrastructure.voters import CookieVoterIdentity

__all__ = ["build_ballot_service", "build_voter_identity"]


def build_ballot_service() -> BallotService:
    """Assemble the voting use cases over PostgreSQL and the real clock."""
    return BallotService(
        ballots=DjangoBallotRepository(),
        votes=DjangoVoteRepository(),
        clock=SystemClock(),
        uuids=Uuid7Generator(),
        slugs=RandomSlugFactory(),
        catalog=DjangoNomineeCatalog(),
    )


def build_voter_identity() -> CookieVoterIdentity:
    """Assemble the adapter that turns a request into a pair of opaque voter keys.

    Used by the public edge rather than by the service: recognizing a voter is an
    HTTP fact (a cookie, an address prefix), and the use cases take the resolved
    tokens so they never see a request object.
    """
    return CookieVoterIdentity()
