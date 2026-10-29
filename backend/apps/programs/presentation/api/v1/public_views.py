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

import uuid

from django.core.cache import cache
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.programs.application.commands import (
    AnnotateItemCommand,
    HostReorderCommand,
    MarkBackstageCommand,
    SetItemProgressCommand,
)
from apps.programs.application.dto import PublicProgramView
from apps.programs.composition import build_program_service
from apps.programs.domain.exceptions import ProgramError, RunningOrderNotControllableError
from apps.programs.presentation.api.v1.problems import problem_response, request_id
from apps.programs.presentation.api.v1.public_serializers import (
    PublicProgramEnvelopeSerializer,
)
from apps.programs.presentation.api.v1.serializers import (
    ReorderItemsRequestSerializer,
    SetBackstageRequestSerializer,
    SetHostNoteRequestSerializer,
    SetProgressRequestSerializer,
)

_TAG = "Public Program"

#: How long a rendered table may be served from Redis before it is built again.
#:
#: This is the ceiling on how far behind the screen can be on data this context does not
#: own - a participant renamed in Applications, a competition retitled - because those do
#: not move the programme's version. Anything the programme itself records (a row marked
#: on stage, a reorder, a republished column set) bumps the version and is visible on the
#: next poll regardless.
_CACHE_TTL_SECONDS = 60

__all__ = [
    "PublicProgramDetailView",
    "PublicProgramOrderView",
    "PublicProgramRowBackstageView",
    "PublicProgramRowNoteView",
    "PublicProgramRowProgressView",
]


def _cache_key(slug: str, stamp: str) -> str:
    return f"programs:public:{slug}:{stamp}"


def _if_none_match(request: Request) -> frozenset[str]:
    """The client's validators, weak prefix stripped so ``W/"x"`` matches ``"x"``."""
    header = request.headers.get("If-None-Match", "")
    return frozenset(part.removeprefix("W/").strip() for part in (raw.strip() for raw in header.split(",")) if part)


def _cache_headers(etag: str, correlation_id: str) -> dict[str, str]:
    return {
        "ETag": etag,
        # ``no-cache`` means "revalidate", not "do not store": the client keeps the body
        # and asks whether it is still current, which is the whole point of the ETag.
        # ``private`` because the host's edition carries row ids that a shared cache has
        # no business holding.
        "Cache-Control": "private, no-cache",
        "X-Request-ID": correlation_id,
    }


def _public_json(view: PublicProgramView) -> dict[str, object]:
    return {
        "name": view.name,
        "slug": view.slug,
        "competitionTitle": view.competition_title,
        "nomination": view.nomination,
        "startsAt": view.starts_at,
        "totalSeconds": view.total_seconds,
        "controlsRunningOrder": view.controls_running_order,
        "columns": [{"key": column.key, "label": column.label, "custom": column.custom, "sensitive": column.sensitive} for column in view.columns],
        "rows": [
            # ``id``, ``backstage`` and ``note`` are present only on the host's edition -
            # see PublicProgramRowView. On every other one they are null here because the
            # application layer never put anything in them.
            {
                "kind": row.kind,
                "cells": list(row.cells),
                "progress": row.progress,
                "id": row.id,
                "backstage": row.backstage,
                "note": row.note,
            }
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
        responses={
            status.HTTP_200_OK: PublicProgramEnvelopeSerializer,
            status.HTTP_304_NOT_MODIFIED: None,
        },
        description=(
            "Returns the published table. Send back the `ETag` as `If-None-Match` and a "
            "poll that finds nothing changed costs a `304` instead of the whole table."
        ),
    )
    def get(self, request: Request, slug: str) -> Response:
        correlation_id = request_id(request)
        service = build_program_service()

        # The cheap question first: one indexed row, no aggregate, no catalog read behind it.
        stamp = service.public_program_stamp(slug)
        if stamp is None:
            return self._gone(request, correlation_id)

        key = _cache_key(slug, stamp)
        entry = cache.get(key)
        if entry is None:
            view = service.public_program(slug)
            if view is None:
                # Revoked between the two reads: the link is simply gone.
                return self._gone(request, correlation_id)
            # The validator is minted with the entry and stored beside it, so it rotates
            # exactly when the table is built again. That is what bounds the lag on data
            # this context does not own: no rebuild, no new validator, no stale answer
            # that outlives the TTL.
            entry = {"etag": f'W/"{stamp}.{uuid.uuid4().hex[:8]}"', "body": _public_json(view)}
            cache.set(key, entry, timeout=_CACHE_TTL_SECONDS)

        etag = str(entry["etag"])
        if etag.removeprefix("W/") in _if_none_match(request):
            # Nothing to send, and this is the answer to the overwhelming majority of
            # polls: a programme changes a few times an hour, and every open screen asks
            # every few seconds.
            return Response(status=status.HTTP_304_NOT_MODIFIED, headers=_cache_headers(etag, correlation_id))

        return Response(
            {"data": entry["body"], "meta": {"requestId": correlation_id}},
            status=status.HTTP_200_OK,
            headers=_cache_headers(etag, correlation_id),
        )

    def _gone(self, request: Request, correlation_id: str) -> Response:
        return problem_response(
            status=status.HTTP_404_NOT_FOUND,
            type_suffix="not-found",
            title="Resource not found",
            detail="По этой ссылке опубликованной программы нет.",
            instance=request.get_full_path(),
            correlation_id=correlation_id,
        )


class _HostView(APIView):
    """A write from the host's own link.

    Unauthenticated like the read, and gated on the *edition* rather than on a user: the
    organizer decides which link may drive the day, and hands that one to the host. A
    read-only link refuses here indistinguishably from a slug that does not exist, so the
    links handed to an audience cannot be probed for control.

    The gate runs before the body is parsed - see :meth:`_authorize`.
    """

    authentication_classes = ()
    permission_classes = (AllowAny,)

    def _authorize(self, request: Request, slug: str, correlation_id: str) -> Response | None:
        """Settle whether this link may drive the day, before the body is looked at.

        Order matters here and is the whole point: a link without control must be
        refused identically whatever it sends, so that a 400 about the payload can
        never be mistaken — by an attacker or by an auditor — for the absence of a
        gate. Returns the refusal to send, or ``None`` to carry on.
        """
        try:
            build_program_service().ensure_host_control(slug)
        except ProgramError:
            # Covers both halves of the answer — the slug nobody minted and the link
            # minted without control — because telling them apart is exactly what this
            # edge must not let a caller do.
            return self._refused(request, correlation_id)
        return None

    def _refused(self, request: Request, correlation_id: str) -> Response:
        return problem_response(
            status=status.HTTP_404_NOT_FOUND,
            type_suffix="not-found",
            title="Resource not found",
            detail="По этой ссылке программа не найдена.",
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
        refusal = self._authorize(request, slug, correlation_id)
        if refusal is not None:
            return refusal
        serializer = SetProgressRequestSerializer(data=request.data)
        if not serializer.is_valid():
            return problem_response(
                status=status.HTTP_400_BAD_REQUEST,
                type_suffix="validation-error",
                title="Validation failed",
                detail="Неизвестный статус хода программы.",
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


class PublicProgramRowBackstageView(_HostView):
    """``PUT /public/programs/{slug}/rows/{itemId}/backstage`` - who has turned up.

    The host's own bookkeeping, and the only write here whose result nobody else can see:
    the answer carries the mark back on her edition and on no other, because the
    application layer renders it into no other.
    """

    @extend_schema(
        tags=[_TAG],
        operation_id="publicProgramSetBackstage",
        request=SetBackstageRequestSerializer,
        responses={status.HTTP_200_OK: PublicProgramEnvelopeSerializer},
        description="Mark one act as present behind the stage, or no longer present. Visible on the host's link only.",
    )
    def put(self, request: Request, slug: str, item_id: str) -> Response:
        correlation_id = request_id(request)
        refusal = self._authorize(request, slug, correlation_id)
        if refusal is not None:
            return refusal
        serializer = SetBackstageRequestSerializer(data=request.data)
        if not serializer.is_valid():
            return problem_response(
                status=status.HTTP_400_BAD_REQUEST,
                type_suffix="validation-error",
                title="Validation failed",
                detail="Передайте, стоит ли отметка «за сценой».",
                instance=request.get_full_path(),
                correlation_id=correlation_id,
            )
        try:
            program = build_program_service().set_item_backstage(
                MarkBackstageCommand(slug=slug, item_id=item_id, backstage=bool(serializer.validated_data["backstage"]))
            )
        except ProgramError:
            return self._refused(request, correlation_id)
        return Response(
            {"data": _public_json(program), "meta": {"requestId": correlation_id}},
            status=status.HTTP_200_OK,
            headers={"X-Request-ID": correlation_id},
        )


class PublicProgramRowNoteView(_HostView):
    """``PUT /public/programs/{slug}/rows/{itemId}/note`` - the host writes to herself.

    An empty note clears it, which is why this is a ``PUT`` of the whole note rather than
    an append: the thing being set is the one line that stands against this act now.
    """

    @extend_schema(
        tags=[_TAG],
        operation_id="publicProgramSetHostNote",
        request=SetHostNoteRequestSerializer,
        responses={status.HTTP_200_OK: PublicProgramEnvelopeSerializer},
        description="Write the host's own note on one row. Visible on the host's link only; blank clears it.",
    )
    def put(self, request: Request, slug: str, item_id: str) -> Response:
        correlation_id = request_id(request)
        refusal = self._authorize(request, slug, correlation_id)
        if refusal is not None:
            return refusal
        serializer = SetHostNoteRequestSerializer(data=request.data)
        if not serializer.is_valid():
            return problem_response(
                status=status.HTTP_400_BAD_REQUEST,
                type_suffix="validation-error",
                title="Validation failed",
                detail="Пометка слишком длинная — оставьте не больше 500 символов.",
                instance=request.get_full_path(),
                correlation_id=correlation_id,
            )
        try:
            program = build_program_service().annotate_item(
                AnnotateItemCommand(slug=slug, item_id=item_id, note=str(serializer.validated_data["note"]))
            )
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
        refusal = self._authorize(request, slug, correlation_id)
        if refusal is not None:
            return refusal
        serializer = ReorderItemsRequestSerializer(data=request.data)
        if not serializer.is_valid():
            return problem_response(
                status=status.HTTP_400_BAD_REQUEST,
                type_suffix="validation-error",
                title="Validation failed",
                detail="Передайте полный новый порядок выступлений.",
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
