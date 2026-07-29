"""REST edge for the font library.

Three organizer endpoints and one public one, and the split between them is the whole design:

* ``GET/POST/DELETE /staff/diplomas/fonts`` — the library an organizer manages. Staff-gated,
  because uploading a file the renderer will embed into every diploma is organizer work.
* ``GET /public/diploma-fonts/<family>/<variant>.ttf`` — the bundled files themselves,
  **unauthenticated by necessity**. A browser fetches an ``@font-face`` source without the
  Authorization header, so a font behind a token would simply never load in the editor and
  the constructor would preview in a fallback face while the PDF used the real one. That is
  the exact mismatch this whole feature exists to remove. Nothing is given away: these are
  redistributable OFL/Apache files that ship in the repository.

Uploaded files are served from ``/media/`` like every other diploma artifact, so they need no
endpoint of their own.
"""

from __future__ import annotations

from typing import Any

from django.http import FileResponse, Http404, HttpRequest
from django.utils import timezone
from drf_spectacular.utils import extend_schema, inline_serializer
from rest_framework import serializers
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.diplomas.application.font_library import (
    FontCatalogFamilyView,
    UploadedFontView,
)
from apps.diplomas.composition import build_font_library_service
from apps.diplomas.domain.exceptions import DiplomaError
from apps.diplomas.infrastructure.fonts import MAX_FONT_BYTES
from apps.diplomas.infrastructure.pdf.fonts import bundled_font_path, invalidate_uploaded_fonts
from apps.diplomas.presentation.api.v1 import problems
from apps.identity.infrastructure.auth import CredentialAwareJWTAuthentication
from apps.organization.presentation.permissions import IsOrganizationStaff

_TAG = "Diplomas"
_PUBLIC_TAG = "Public Diploma Fonts"

__all__ = ["DiplomaFontDetailView", "DiplomaFontsView", "PublicBundledFontView"]

#: How long a browser may keep a bundled font file. They are immutable — a different file
#: would be a different family — so this is as long as is polite.
_FONT_CACHE_SECONDS = 60 * 60 * 24 * 30


def _variant_json(variant: Any) -> dict[str, Any]:
    return {
        "variant": variant.variant.value,
        "bold": variant.bold,
        "italic": variant.italic,
        "fileUrl": variant.file_url,
    }


def _family_json(family: FontCatalogFamilyView) -> dict[str, Any]:
    return {
        "family": family.family,
        "source": family.source.value,
        "variants": [_variant_json(variant) for variant in family.variants],
        "substitutedBy": family.substituted_by,
        "id": family.id,
    }


def _uploaded_json(font: UploadedFontView) -> dict[str, Any]:
    return {
        "id": font.id,
        "family": font.family,
        "variant": font.variant.value,
        "originalFilename": font.original_filename,
        "fileUrl": font.file_url,
        "sizeBytes": font.size_bytes,
        "uploadedAt": font.uploaded_at,
    }


_FontCatalogSerializer = inline_serializer(
    name="DiplomaFontCatalog",
    fields={
        "families": inline_serializer(
            name="DiplomaFontFamily",
            fields={
                "family": serializers.CharField(),
                "source": serializers.ChoiceField(choices=["BUNDLED", "UPLOADED"]),
                "variants": inline_serializer(
                    name="DiplomaFontVariant",
                    fields={
                        "variant": serializers.CharField(),
                        "bold": serializers.BooleanField(),
                        "italic": serializers.BooleanField(),
                        "fileUrl": serializers.CharField(),
                    },
                    many=True,
                ),
                "substitutedBy": serializers.CharField(allow_null=True),
                "id": serializers.CharField(allow_null=True),
            },
            many=True,
        ),
        "uploaded": inline_serializer(
            name="DiplomaUploadedFont",
            fields={
                "id": serializers.CharField(),
                "family": serializers.CharField(),
                "variant": serializers.CharField(),
                "originalFilename": serializers.CharField(),
                "fileUrl": serializers.CharField(),
                "sizeBytes": serializers.IntegerField(),
                "uploadedAt": serializers.DateTimeField(),
            },
            many=True,
        ),
    },
)


class _StaffView(APIView):
    """Authenticated organization staff only."""

    authentication_classes = (CredentialAwareJWTAuthentication,)
    permission_classes = (IsAuthenticated, IsOrganizationStaff)


class DiplomaFontsView(_StaffView):
    """``GET`` the catalog and the uploads; ``POST`` a font file."""

    parser_classes = (MultiPartParser, FormParser)

    @extend_schema(tags=[_TAG], operation_id="diplomas_fonts_list", responses={200: _FontCatalogSerializer})
    def get(self, request: Request) -> Response:
        service = build_font_library_service()
        catalog = service.catalog()
        return problems.envelope(
            request,
            {
                "families": [_family_json(family) for family in catalog.families],
                "uploaded": [_uploaded_json(font) for font in service.list_uploaded()],
            },
        )

    @extend_schema(
        tags=[_TAG],
        operation_id="diplomas_fonts_upload",
        request={
            "multipart/form-data": inline_serializer(
                name="DiplomaFontUpload",
                fields={"file": serializers.FileField()},
            )
        },
        responses={201: _FontCatalogSerializer},
    )
    def post(self, request: Request) -> Response:
        upload = request.FILES.get("file")
        if upload is None:
            return problems.validation_problem({"file": ["Прикрепите файл шрифта."]}, instance=request.path, request=request)
        if upload.size > MAX_FONT_BYTES:
            return problems.validation_problem(
                {"file": [f"Файл больше {MAX_FONT_BYTES // (1024 * 1024)} МБ."]},
                instance=request.path,
                request=request,
            )
        try:
            build_font_library_service().register(
                data=upload.read(),
                original_filename=str(getattr(upload, "name", "") or "font.ttf"),
                now=timezone.now(),
            )
        except DiplomaError as exc:
            return problems.diploma_problem(exc, instance=request.path, request=request)
        # This process now has a stale view of the library; other processes age out on their
        # own TTL, which is why the registry does not rely on being told.
        invalidate_uploaded_fonts()
        service = build_font_library_service()
        catalog = service.catalog()
        return problems.envelope(
            request,
            {
                "families": [_family_json(family) for family in catalog.families],
                "uploaded": [_uploaded_json(font) for font in service.list_uploaded()],
            },
            status=201,
        )


class DiplomaFontDetailView(_StaffView):
    """``DELETE`` one uploaded face."""

    @extend_schema(tags=[_TAG], operation_id="diplomas_fonts_delete", responses={204: None})
    def delete(self, request: Request, font_id: str) -> Response:
        try:
            build_font_library_service().remove(font_id)
        except DiplomaError as exc:
            return problems.diploma_problem(exc, instance=request.path, request=request)
        invalidate_uploaded_fonts()
        return Response(status=204)


class PublicBundledFontView(APIView):
    """``GET /api/v1/public/diploma-fonts/<family>/<variant>.ttf`` — a bundled font file.

    Unauthenticated on purpose; see the module docstring. The path is resolved through the
    registry's own index rather than joined onto a directory, so ``../../etc/passwd`` is a
    lookup miss rather than a traversal.
    """

    authentication_classes = ()
    permission_classes = (AllowAny,)

    @extend_schema(tags=[_PUBLIC_TAG], operation_id="publicDiplomaFont", auth=[], responses={200: bytes, 404: None})
    def get(self, request: HttpRequest, family: str, variant: str) -> FileResponse:
        path = bundled_font_path(family, variant)
        if path is None or not path.exists():
            raise Http404("No such bundled font face.")
        response = FileResponse(path.open("rb"), content_type="font/ttf")
        response["Cache-Control"] = f"public, max-age={_FONT_CACHE_SECONDS}, immutable"
        # The editor fetches these with `@font-face`, and a cross-origin font request is
        # subject to CORS even when the file itself is public.
        response["Access-Control-Allow-Origin"] = "*"
        return response
