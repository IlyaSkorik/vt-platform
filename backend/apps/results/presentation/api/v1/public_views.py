"""Public results REST edge (anyone-facing).

Two unauthenticated endpoints, and together they are the whole of what the outside world
sees of this context:

* ``GET /api/v1/public/protocols/{slug}`` - one published protocol, the page a participant
  opens from "Результаты" or from the letter they were sent.
* ``GET /api/v1/public/competitions/{competition_id}/results`` - which protocols a
  competition has published, for the landing page's "Результаты" section.

Public by design, and different from a programme link in one way worth noting: a programme
slug is a secret handed to a sound engineer, while a protocol slug is **meant** to be found
- it is linked from a public landing page. It stays unguessable anyway, because the link
exists from the moment of publication and the results must not be readable a moment before
the page they are linked from says so.

Both responses are cacheable by shared caches, unlike the programme's private ones: a
published protocol is the same document for every reader, and there is nothing in it that a
CDN has no business holding.
"""

from __future__ import annotations

from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.results.application.dto import PublicProtocolView
from apps.results.composition import build_protocol_service
from apps.results.domain.exceptions import ProtocolError
from apps.results.presentation.api.v1.problems import envelope, problem_response, request_id
from apps.results.presentation.api.v1.public_serializers import (
    PublicProtocolEnvelopeSerializer,
    PublishedProtocolListEnvelopeSerializer,
)

_TAG = "Public Results"

#: How long a published protocol may be served from a cache. Results change rarely and a
#: correction is a deliberate act, so a minute of staleness is a fair trade for a landing
#: page that survives being linked from a parents' chat.
_CACHE_SECONDS = 60

__all__ = ["PublicCompetitionResultsView", "PublicProtocolDetailView"]


def _protocol_json(view: PublicProtocolView) -> dict[str, object]:
    return {
        "name": view.name,
        "slug": view.slug,
        "competitionTitle": view.competition_title,
        "nomination": view.nomination,
        "revision": view.revision,
        "publishedAt": view.published_at,
        "columns": [{"key": column.key, "label": column.label} for column in view.columns],
        "rows": [{"cells": list(row.cells), "award": row.award} for row in view.rows],
    }


class PublicProtocolDetailView(APIView):
    """``GET /api/v1/public/protocols/{slug}`` - one published protocol."""

    authentication_classes = ()
    permission_classes = (AllowAny,)

    @extend_schema(
        tags=[_TAG],
        operation_id="publicProtocolRetrieve",
        auth=[],
        responses={200: PublicProtocolEnvelopeSerializer, 404: None},
    )
    def get(self, request: Request, slug: str) -> Response:
        try:
            view = build_protocol_service().public_protocol(slug)
        except ProtocolError:
            # A malformed slug is not a different answer from an unknown one: a link either
            # resolves or it does not, and saying which is which invites probing.
            view = None
        if view is None:
            return problem_response(
                status=status.HTTP_404_NOT_FOUND,
                type_suffix="not-found",
                title="Resource not found",
                detail="No published protocol answers to this link.",
                instance=request.get_full_path(),
                correlation_id=request_id(request),
            )
        response = envelope(request, _protocol_json(view))
        response["Cache-Control"] = f"public, max-age={_CACHE_SECONDS}"
        return response


class PublicCompetitionResultsView(APIView):
    """``GET /api/v1/public/competitions/{competition_id}/results`` - the results index.

    Answers an empty list for a competition that has published nothing, which is what lets
    a landing page decide to hide the section entirely rather than show an empty heading.
    """

    authentication_classes = ()
    permission_classes = (AllowAny,)

    @extend_schema(
        tags=[_TAG],
        operation_id="publicCompetitionResults",
        auth=[],
        responses={200: PublishedProtocolListEnvelopeSerializer, 404: None},
    )
    def get(self, request: Request, competition_id: str) -> Response:
        try:
            links = build_protocol_service().published_links(competition_id)
        except ProtocolError:
            links = ()
        response = envelope(
            request,
            [
                {
                    "nomination": link.nomination,
                    "name": link.name,
                    "slug": link.slug,
                    "path": link.path,
                    "revision": link.revision,
                    "publishedAt": link.published_at,
                }
                for link in links
            ],
            meta={"total": len(links)},
        )
        response["Cache-Control"] = f"public, max-age={_CACHE_SECONDS}"
        return response
