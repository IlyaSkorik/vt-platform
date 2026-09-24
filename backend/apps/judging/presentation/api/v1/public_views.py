"""The hall's board — the one unauthenticated read in the Judging context.

A projector standing beside a stage has no account and cannot be given one. What
protects the marks is the same thing that protects a published protocol: an unguessable
slug, minted once when the organizer switches the board on, that stops resolving the
moment they switch it off.

What the page shows was decided in the application layer, not here. A board configured
for totals only never has per-judge marks in the view this renders — see
:meth:`~apps.judging.application.services.ScoringService.board`.
"""

from __future__ import annotations

from drf_spectacular.utils import OpenApiResponse, extend_schema
from rest_framework.permissions import AllowAny
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.judging.composition import build_scoring_service
from apps.judging.domain.exceptions import JudgingError
from apps.judging.presentation.api.v1 import problems
from apps.judging.presentation.api.v1.rendering import board_json
from apps.judging.presentation.api.v1.serializers import BoardEnvelopeSerializer, JudgingProblemDetailSerializer

__all__ = ["PublicBoardView"]

_TAG = "Public Judging Board"


class PublicBoardView(APIView):
    """``GET /api/v1/public/judging/board/<slug>`` — the screen beside the stage."""

    authentication_classes = ()
    permission_classes = (AllowAny,)

    @extend_schema(
        tags=[_TAG],
        operation_id="publicJudgingBoard",
        responses={
            200: BoardEnvelopeSerializer,
            404: OpenApiResponse(JudgingProblemDetailSerializer, description="No such board, or it is switched off."),
        },
    )
    def get(self, request: Request, slug: str) -> Response:
        try:
            view = build_scoring_service().board(slug)
        except JudgingError as exc:
            return problems.judging_problem(exc, instance=request.get_full_path(), request=request)
        if view is None:
            return problems.problem_response(
                status=404,
                type_suffix="not-found",
                title="Resource not found",
                detail="Табло не найдено. Проверьте ссылку.",
                instance=request.get_full_path(),
                correlation_id=problems.request_id(request),
            )
        return problems.envelope(request, board_json(view))
