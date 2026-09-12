"""Public voting edge (anyone-facing).

Two endpoints and no authentication: whoever holds the link reads the ballot and
votes on it, with no account. The slug *is* the credential — minted per ballot
from a confusable-free alphabet, never derived from its title — so a link cannot
be found by guessing, and a retired one is indistinguishable from one that never
existed. A draft ballot answers the same way, so a link handed out early does not
confirm that something is being prepared.

**The cookie.** Recognizing a voter happens here rather than in the use case,
because a cookie and an address are HTTP facts: the edge resolves them into a pair
of opaque keys and hands those down, so the service never sees a request object.
The first read mints a token and asks the browser to keep it (httpOnly,
path-scoped, SameSite=Lax).

Voting is throttled in its own bucket, far below the anonymous default: a person
voting sends one request, and whatever sends sixty a minute is not somebody in a
hall.
"""

from __future__ import annotations

from django.conf import settings
from drf_spectacular.utils import OpenApiResponse, extend_schema
from rest_framework.permissions import AllowAny
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView

from apps.voting.application.commands import CastVoteCommand
from apps.voting.application.interfaces import VoterTokens
from apps.voting.composition import build_ballot_service, build_voter_identity
from apps.voting.domain.exceptions import BallotError, BallotNotFoundError
from apps.voting.infrastructure.models import BallotModel
from apps.voting.infrastructure.voters import COOKIE_NAME, COOKIE_PATH, cookie_max_age
from apps.voting.presentation.api.v1 import resources
from apps.voting.presentation.api.v1.problems import ballot_problem, envelope
from apps.voting.presentation.api.v1.serializers import (
    BallotProblemDetailSerializer,
    CastVoteRequestSerializer,
    PublicBallotSerializer,
    VoteReceiptSerializer,
)

_TAG = "Public Voting"

__all__ = ["PublicBallotDetailView", "PublicBallotVoteView"]


def _attach_cookie(response: Response, tokens: VoterTokens | None) -> Response:
    """Hand a first-time visitor the token that makes them recognizable.

    ``httponly`` because nothing on the page needs to read it; ``samesite=Lax``
    because the vote is a same-site POST from the page we just served; ``secure``
    off only where the whole deployment is (local development over plain HTTP).

    Attached to refusals as well as to successes: somebody who votes before the
    page has set a cookie must not remain a stranger, or their next attempt looks
    to us like a different person.
    """
    if tokens is None or not tokens.issued or tokens.raw_token is None:
        return response
    response.set_cookie(
        COOKIE_NAME,
        tokens.raw_token,
        max_age=cookie_max_age(),
        path=COOKIE_PATH,
        httponly=True,
        samesite="Lax",
        secure=not settings.DEBUG,
    )
    return response


class _PublicView(APIView):
    """Anyone, with no account. The slug is the only credential."""

    authentication_classes = ()
    permission_classes = (AllowAny,)

    def _problem(self, error: BallotError, request: Request) -> Response:
        return ballot_problem(error, instance=request.get_full_path(), request=request)

    def _recognize(self, request: Request, slug: str) -> VoterTokens | None:
        """Resolve who this reader is, if the slug leads anywhere at all.

        The ballot's id goes into the keys, so it has to be looked up first — one
        indexed read. ``None`` means the link is dead, and the caller answers 404
        without having minted anything: a cookie handed out for a ballot that does
        not exist would be a tracker and nothing else.
        """
        ballot_id = BallotModel.objects.filter(slug=slug, deleted_at__isnull=True).values_list("id", flat=True).first()
        if ballot_id is None:
            return None
        return build_voter_identity().recognize(request, ballot_id=ballot_id)


class PublicBallotDetailView(_PublicView):
    """``GET /api/v1/public/ballots/{slug}`` — the voting page."""

    @extend_schema(
        tags=[_TAG],
        operation_id="public_get_ballot",
        summary="Read a ballot by its public link",
        description=(
            "Unauthenticated. Sets an httpOnly cookie identifying the reader as a voter, so their choices "
            "can be shown back to them and counted once. A draft or retired ballot answers 404."
        ),
        request=None,
        responses={
            200: PublicBallotSerializer,
            404: OpenApiResponse(BallotProblemDetailSerializer, description="No such ballot."),
        },
    )
    def get(self, request: Request, slug: str) -> Response:
        tokens = self._recognize(request, slug)
        if tokens is None:
            return self._problem(BallotNotFoundError("Голосование не найдено."), request)
        try:
            view = build_ballot_service().public_view(slug, tokens=tokens)
        except BallotError as exc:
            return self._problem(exc, request)

        response = envelope(resources.public_ballot(view), request)
        # `private, no-cache` means "revalidate", not "do not store": this body
        # carries the reader's own choices and a shared cache has no business
        # holding it. The count moves while a hall votes, so there is nothing here
        # worth caching for longer than a round trip anyway.
        response["Cache-Control"] = "private, no-cache"
        return _attach_cookie(response, tokens)


class PublicBallotVoteView(_PublicView):
    """``POST /api/v1/public/ballots/{slug}/votes`` — cast a vote."""

    throttle_classes = (ScopedRateThrottle,)
    throttle_scope = "ballot_vote"

    @extend_schema(
        tags=[_TAG],
        operation_id="public_cast_vote",
        summary="Cast a vote",
        description=(
            "All or nothing: every check runs before any vote is written, so a submission never leaves "
            "somebody with two of their three votes spent and an error on screen. Answers with the whole "
            "page state, so the client renders the outcome without a second request."
        ),
        request=CastVoteRequestSerializer,
        responses={
            200: VoteReceiptSerializer,
            404: OpenApiResponse(BallotProblemDetailSerializer, description="No such ballot."),
            409: OpenApiResponse(BallotProblemDetailSerializer, description="Already voted, or out of votes."),
            422: OpenApiResponse(BallotProblemDetailSerializer, description="Voting is not open."),
            429: OpenApiResponse(BallotProblemDetailSerializer, description="Too many votes from this network."),
        },
    )
    def post(self, request: Request, slug: str) -> Response:
        serializer = CastVoteRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        tokens = self._recognize(request, slug)
        if tokens is None:
            return self._problem(BallotNotFoundError("Голосование не найдено."), request)

        command = CastVoteCommand(
            slug=slug,
            nominee_ids=tuple(str(value) for value in serializer.validated_data["nomineeIds"]),
        )
        try:
            receipt = build_ballot_service().cast_vote(command, tokens=tokens)
        except BallotError as exc:
            return _attach_cookie(self._problem(exc, request), tokens)

        response = envelope(resources.vote_receipt(receipt), request)
        response["Cache-Control"] = "no-store"
        return _attach_cookie(response, tokens)
