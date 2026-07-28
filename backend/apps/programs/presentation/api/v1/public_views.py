"""Public program REST edge (anyone-facing).

``GET /api/v1/public/programs/{slug}`` - the single unauthenticated endpoint of this
context, and the backend of the screen an organizer hands to a sound engineer, a host,
the jury or a display beside the stage.

Public by design: whoever holds the link reads the program, with no account. The slug
*is* the credential - minted per edition from a confusable-free alphabet, never
derived from the program's name - so a link cannot be found by guessing, and a revoked
one is indistinguishable from one that never existed.
"""

from __future__ import annotations

from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.programs.application.commands import HostReorderCommand, SetItemProgressCommand
from apps.programs.application.dto import PublicProgramView
from apps.programs.composition import build_program_service
from apps.programs.domain.exceptions import ProgramError, RunningOrderNotControllableError
from apps.programs.presentation.api.v1.problems import problem_response, request_id
from apps.programs.presentation.api.v1.public_serializers import (
    PublicProgramEnvelopeSerializer,
)
from apps.programs.presentation.api.v1.serializers import (
    ReorderItemsRequestSerializer,
    SetProgressRequestSerializer,
)

_TAG = "Public Program"

__all__ = ["PublicProgramDetailView", "PublicProgramOrderView", "PublicProgramRowProgressView"]


def _public_json(view: PublicProgramView) -> dict[str, object]:
    return {
        "name": view.name,
        "slug": view.slug,
        "competitionTitle": view.competition_title,
        "nomination": view.nomination,
        "startsAt": view.starts_at,
        "totalSeconds": view.total_seconds,
        "controlsRunningOrder": view.controls_running_order,
        "columns": [{"key": column.key, "label": column.label, "custom": column.custom} for column in view.columns],
        "rows": [
            # ``id`` is present only on the host's edition - see PublicProgramRowView.
            {"kind": row.kind, "cells": list(row.cells), "progress": row.progress, "id": row.id}
            for row in view.rows
        ],
    }


class PublicProgramDetailView(APIView):
    """Read one published program by its slug.

    An unknown, malformed or revoked slug is a single, indistinguishable ``404``, so
    nothing about which of the three it was leaks.
    """

    # Public by design: no authentication and no staff gate. A visitor may happen to
    # carry a bearer token; it is irrelevant here - the link is the whole of the input.
    authentication_classes = ()
    permission_classes = (AllowAny,)

    @extend_schema(
        tags=[_TAG],
        operation_id="publicProgramRetrieve",
        responses={status.HTTP_200_OK: PublicProgramEnvelopeSerializer},
    )
    def get(self, request: Request, slug: str) -> Response:
        correlation_id = request_id(request)
        program = build_program_service().public_program(slug)
        if program is None:
            return problem_response(
                status=status.HTTP_404_NOT_FOUND,
                type_suffix="not-found",
                title="Resource not found",
                detail="No published program answers to this link.",
                instance=request.get_full_path(),
                correlation_id=correlation_id,
            )
        return Response(
            {"data": _public_json(program), "meta": {"requestId": correlation_id}},
            status=status.HTTP_200_OK,
            headers={"X-Request-ID": correlation_id},
        )


class _HostView(APIView):
    """A write from the host's own link.

    Unauthenticated like the read, and gated on the *edition* rather than on a user: the
    organizer decides which link may drive the day, and hands that one to the host. A
    read-only link refuses here indistinguishably from a slug that does not exist, so the
    links handed to an audience cannot be probed for control.
    """

    authentication_classes = ()
    permission_classes = (AllowAny,)

    def _refused(self, request: Request, correlation_id: str) -> Response:
        return problem_response(
            status=status.HTTP_404_NOT_FOUND,
            type_suffix="not-found",
            title="Resource not found",
            detail="No programme answers to this link.",
            instance=request.get_full_path(),
            correlation_id=correlation_id,
        )


class PublicProgramRowProgressView(_HostView):
    """``PUT /public/programs/{slug}/rows/{itemId}/progress`` - the host marks the day.

    Answers with the whole programme so the host's screen redraws from exactly the payload
    every other screen is polling - one table, one source, no divergence.
    """

    @extend_schema(
        tags=[_TAG],
        operation_id="publicProgramSetProgress",
        request=SetProgressRequestSerializer,
        responses={status.HTTP_200_OK: PublicProgramEnvelopeSerializer},
    )
    def put(self, request: Request, slug: str, item_id: str) -> Response:
        correlation_id = request_id(request)
        serializer = SetProgressRequestSerializer(data=request.data)
        if not serializer.is_valid():
            return problem_response(
                status=status.HTTP_400_BAD_REQUEST,
                type_suffix="validation-error",
                title="Validation failed",
                detail="Send a known progress state.",
                instance=request.get_full_path(),
                correlation_id=correlation_id,
            )
        try:
            program = build_program_service().set_item_progress(
                SetItemProgressCommand(slug=slug, item_id=item_id, progress=str(serializer.validated_data["progress"]))
            )
        except RunningOrderNotControllableError:
            return self._refused(request, correlation_id)
        except ProgramError:
            return self._refused(request, correlation_id)
        return Response(
            {"data": _public_json(program), "meta": {"requestId": correlation_id}},
            status=status.HTTP_200_OK,
            headers={"X-Request-ID": correlation_id},
        )


class PublicProgramOrderView(_HostView):
    """``PUT /public/programs/{slug}/order`` - the host rearranges what is still to come.

    Numbers are frozen by now (publishing froze them), so the rows move and every
    participant keeps the number they were told.
    """

    @extend_schema(
        tags=[_TAG],
        operation_id="publicProgramReorder",
        request=ReorderItemsRequestSerializer,
        responses={status.HTTP_200_OK: PublicProgramEnvelopeSerializer},
    )
    def put(self, request: Request, slug: str) -> Response:
        correlation_id = request_id(request)
        serializer = ReorderItemsRequestSerializer(data=request.data)
        if not serializer.is_valid():
            return problem_response(
                status=status.HTTP_400_BAD_REQUEST,
                type_suffix="validation-error",
                title="Validation failed",
                detail="Send the complete new order.",
                instance=request.get_full_path(),
                correlation_id=correlation_id,
            )
        item_ids = tuple(str(item_id) for item_id in serializer.validated_data["itemIds"])
        try:
            program = build_program_service().host_reorder(HostReorderCommand(slug=slug, item_ids=item_ids))
        except RunningOrderNotControllableError:
            return self._refused(request, correlation_id)
        except ProgramError as exc:
            # A mismatched order is the host's own mistake and worth saying so.
            return problem_response(
                status=status.HTTP_422_UNPROCESSABLE_ENTITY,
                type_suffix="unprocessable-entity",
                title="A reorder must list every item exactly once",
                detail=str(exc),
                instance=request.get_full_path(),
                correlation_id=correlation_id,
            )
        return Response(
            {"data": _public_json(program), "meta": {"requestId": correlation_id}},
            status=status.HTTP_200_OK,
            headers={"X-Request-ID": correlation_id},
        )
