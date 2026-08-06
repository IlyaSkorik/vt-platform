"""Authentication controllers for the Identity REST API v1 (API-001 §4).

Four noun-resource endpoints — registration, sessions (login), token refresh, and
the current session (logout) — each a thin HTTP adapter that follows one flow:

    HTTP request → serializer (validate) → command → handler → DTO → HTTP response

A view never queries the ORM, verifies a password, issues a JWT itself, or holds a
business rule: it validates the request shape, maps it onto an application
command, invokes a handler assembled by the :mod:`composition` root, and renders
the resulting DTO into the API envelope (API-000 §7) or an RFC 9457 problem
(API-000 §8, via :mod:`apps.identity.presentation.api.v1.problems`). Token
issuance/rotation is delegated to the ``TokenService`` port; the refresh token is
carried in an httpOnly cookie for web clients and echoed in the body for native
clients (API-001 §1.2).
"""

from __future__ import annotations

import contextlib
from datetime import timedelta
from typing import Any, cast

from django.conf import settings
from drf_spectacular.utils import OpenApiResponse, extend_schema
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.settings import api_settings as jwt_settings

from apps.identity.application.commands import (
    AuthenticateUserCommand,
    ConfirmEmailVerificationCommand,
    ConsentAcceptance,
    LogoutCommand,
    RefreshTokenCommand,
    RegisterUserCommand,
    RequestEmailVerificationCommand,
    RequestPasswordResetCommand,
    ResetPasswordCommand,
)
from apps.identity.application.dto import TokenPairDto, UserDto
from apps.identity.application.exceptions import ApplicationError, InvalidTokenError
from apps.identity.infrastructure.auth import CredentialAwareJWTAuthentication
from apps.identity.presentation.api.v1.auth import composition
from apps.identity.presentation.api.v1.auth.serializers import (
    EmailVerificationConfirmSerializer,
    EmailVerificationRequestSerializer,
    EmailVerificationResponseSerializer,
    PasswordResetConfirmSerializer,
    PasswordResetRequestSerializer,
    ProblemDetailSerializer,
    RegistrationRequestSerializer,
    RegistrationResponseSerializer,
    SessionCreateRequestSerializer,
    SessionResponseSerializer,
    TokenRefreshRequestSerializer,
    TokenRefreshResponseSerializer,
)
from apps.identity.presentation.api.v1.problems import (
    application_problem,
    request_id,
    unauthorized_problem,
    validation_problem,
)
from apps.identity.presentation.api.v1.resources import user_resource as _user_resource

_AUTH_TAG = "Identity"


# ---------------------------------------------------------------------------
# Rendering helpers
# ---------------------------------------------------------------------------


def _user_summary(user: UserDto) -> dict[str, Any]:
    """Project a :class:`UserDto` into the compact session user summary."""
    return {
        "id": user.id,
        "type": "user",
        "displayName": user.full_name,
        "emailVerified": user.is_email_verified,
    }


def _session_resource(tokens: TokenPairDto, *, user: UserDto | None = None) -> dict[str, Any]:
    """Build a session/token resource body from an issued or rotated pair."""
    resource: dict[str, Any] = {
        "type": "session",
        "accessToken": tokens.access_token,
        "tokenType": tokens.token_type,
        "expiresIn": tokens.expires_in,
        "refreshToken": tokens.refresh_token,
    }
    if user is not None:
        resource["user"] = _user_summary(user)
    return resource


def _envelope(request: Request, data: dict[str, Any], *, status: int) -> Response:
    """Wrap a resource in the ``data``/``meta`` envelope (API-000 §7.1)."""
    correlation_id = request_id(request)
    return Response(
        {"data": data, "meta": {"requestId": correlation_id}},
        status=status,
        headers={"X-Request-ID": correlation_id},
    )


def _refresh_cookie_max_age() -> int:
    """Refresh cookie lifetime in whole seconds (SimpleJWT ``REFRESH_TOKEN_LIFETIME``)."""
    lifetime = jwt_settings.REFRESH_TOKEN_LIFETIME
    if not isinstance(lifetime, timedelta):
        return 0
    return int(lifetime.total_seconds())


def _cookie_config() -> dict[str, Any]:
    """The refresh-cookie settings block, typed for the cookie API."""
    return cast(dict[str, Any], settings.REFRESH_TOKEN_COOKIE)


def _set_refresh_cookie(response: Response, refresh_token: str) -> None:
    """Attach the rotating refresh token as a hardened httpOnly cookie."""
    cookie = _cookie_config()
    response.set_cookie(
        cookie["NAME"],
        refresh_token,
        max_age=_refresh_cookie_max_age(),
        path=cookie["PATH"],
        httponly=cookie["HTTPONLY"],
        secure=cookie["SECURE"],
        samesite=cookie["SAMESITE"],
    )


def _clear_refresh_cookie(response: Response) -> None:
    """Remove the refresh cookie (logout)."""
    cookie = _cookie_config()
    response.delete_cookie(cookie["NAME"], path=cookie["PATH"], samesite=cookie["SAMESITE"])


def _extract_refresh_token(request: Request, body: dict[str, Any]) -> str | None:
    """Read the refresh token from the request body (native) or cookie (web)."""
    from_body = body.get("refreshToken")
    if from_body:
        return str(from_body)
    from_cookie = request.COOKIES.get(_cookie_config()["NAME"])
    return str(from_cookie) if from_cookie else None


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


class RegistrationView(APIView):
    """POST /api/v1/auth/registration — create a new adult account (API-001 §4.1)."""

    authentication_classes = ()
    permission_classes = (AllowAny,)

    @extend_schema(
        tags=[_AUTH_TAG],
        operation_id="auth_registration_create",
        summary="Register a new account",
        description="Create a new adult user account. Public endpoint.",
        request=RegistrationRequestSerializer,
        responses={
            201: RegistrationResponseSerializer,
            400: OpenApiResponse(ProblemDetailSerializer, description="Malformed request."),
            409: OpenApiResponse(ProblemDetailSerializer, description="Email already in use."),
            422: OpenApiResponse(ProblemDetailSerializer, description="Weak password / invalid."),
        },
    )
    def post(self, request: Request) -> Response:
        instance = request.path
        serializer = RegistrationRequestSerializer(data=request.data)
        if not serializer.is_valid():
            return validation_problem(serializer.errors, instance=instance, request=request)
        data = serializer.validated_data
        command = RegisterUserCommand(
            email=str(data["email"]),
            password=str(data["password"]),
            first_name=str(data["firstName"]),
            last_name=str(data["lastName"]),
            middle_name=_optional_str(data.get("middleName")),
            phone=_optional_str(data.get("phone")),
            locale=_optional_str(data.get("locale")),
            timezone=_optional_str(data.get("timezone")),
            consents=tuple(
                ConsentAcceptance(consent_type=str(item["consentType"]), version=str(item["version"])) for item in data.get("consents") or ()
            ),
        )
        try:
            result = composition.build_register_user_handler().handle(command)
            # Dispatch the events the domain produced (UserRegistered → send the
            # verification email). Synchronous, in-process: registration is not
            # reported as successful unless the verification email was dispatched.
            composition.build_event_publisher().publish(result.events)
        except ApplicationError as exc:
            return application_problem(exc, instance=instance, request=request)
        response = _envelope(request, _user_resource(result.user), status=201)
        response["Location"] = f"/api/v1/users/{result.user.id}"
        return response


class EmailVerificationConfirmationView(APIView):
    """POST /api/v1/auth/email-verification/confirmations — confirm an email (API-001 §4.2)."""

    authentication_classes = ()
    permission_classes = (AllowAny,)

    @extend_schema(
        tags=[_AUTH_TAG],
        operation_id="confirmEmailVerification",
        summary="Confirm email ownership using the emailed token",
        description="Confirm the account's email address using the token from the sent link.",
        request=EmailVerificationConfirmSerializer,
        responses={
            200: EmailVerificationResponseSerializer,
            400: OpenApiResponse(ProblemDetailSerializer, description="Malformed request."),
            409: OpenApiResponse(ProblemDetailSerializer, description="Already verified."),
            410: OpenApiResponse(ProblemDetailSerializer, description="Token expired."),
            422: OpenApiResponse(ProblemDetailSerializer, description="Invalid token."),
        },
    )
    def post(self, request: Request) -> Response:
        instance = request.path
        serializer = EmailVerificationConfirmSerializer(data=request.data)
        if not serializer.is_valid():
            return validation_problem(serializer.errors, instance=instance, request=request)
        data = serializer.validated_data
        command = ConfirmEmailVerificationCommand(token=str(data["token"]))
        try:
            result = composition.build_confirm_email_verification_handler().handle(command)
        except ApplicationError as exc:
            return application_problem(exc, instance=instance, request=request)
        return _envelope(request, _user_resource(result.user), status=200)


class EmailVerificationRequestView(APIView):
    """POST /api/v1/auth/email-verification/requests — (re)send the challenge (API-001 §4.2).

    Public: an account gated out of login by an unverified email cannot present a
    session, so this endpoint takes the target address in the body. The handler is
    anti-enumeration (API-000 §26) — unknown/deleted/already-verified addresses are
    silent no-ops — so the response is a uniform ``202`` and never reveals whether
    the address is registered.
    """

    authentication_classes = ()
    permission_classes = (AllowAny,)

    @extend_schema(
        tags=[_AUTH_TAG],
        operation_id="requestEmailVerification",
        summary="(Re)send an email-verification challenge",
        description="Send a fresh verification link to the given address (no-op if unknown/verified).",
        request=EmailVerificationRequestSerializer,
        responses={
            202: OpenApiResponse(description="Request accepted (email dispatched if applicable)."),
            400: OpenApiResponse(ProblemDetailSerializer, description="Malformed request."),
        },
    )
    def post(self, request: Request) -> Response:
        instance = request.path
        serializer = EmailVerificationRequestSerializer(data=request.data)
        if not serializer.is_valid():
            return validation_problem(serializer.errors, instance=instance, request=request)
        command = RequestEmailVerificationCommand(email=str(serializer.validated_data["email"]))
        try:
            composition.build_request_email_verification_handler().handle(command)
        except ApplicationError as exc:
            return application_problem(exc, instance=instance, request=request)
        correlation_id = request_id(request)
        return Response(status=202, headers={"X-Request-ID": correlation_id})


class PasswordResetRequestView(APIView):
    """POST /api/v1/auth/password-reset/requests — begin recovery (API-001 §4.7).

    Public: a user who forgot their password cannot sign in, so the target address
    is taken in the body. The handler is anti-enumeration (API-000 §26) —
    unknown/deleted/unverified addresses are silent no-ops — so the response is a
    uniform ``202`` and never reveals whether the address is registered.
    """

    authentication_classes = ()
    permission_classes = (AllowAny,)

    @extend_schema(
        tags=[_AUTH_TAG],
        operation_id="requestPasswordReset",
        summary="Begin password recovery (email a reset link)",
        description="Send a password-reset link to the given address (no-op if unknown/unverified).",
        request=PasswordResetRequestSerializer,
        responses={
            202: OpenApiResponse(description="Request accepted (email dispatched if applicable)."),
            400: OpenApiResponse(ProblemDetailSerializer, description="Malformed request."),
        },
    )
    def post(self, request: Request) -> Response:
        instance = request.path
        serializer = PasswordResetRequestSerializer(data=request.data)
        if not serializer.is_valid():
            return validation_problem(serializer.errors, instance=instance, request=request)
        command = RequestPasswordResetCommand(email=str(serializer.validated_data["email"]))
        try:
            composition.build_request_password_reset_handler().handle(command)
        except ApplicationError as exc:
            return application_problem(exc, instance=instance, request=request)
        correlation_id = request_id(request)
        return Response(status=202, headers={"X-Request-ID": correlation_id})


class PasswordResetConfirmationView(APIView):
    """POST /api/v1/auth/password-reset/confirmations — set a new password (API-001 §4.7).

    Public: the emailed token is the proof of ownership. On success the new password
    is stored and every outstanding session is revoked (the account's credential
    cut-off is stamped), so the user must sign in again — this endpoint issues no
    session. A malformed/tampered token is ``422``; an expired link is ``410``; a
    weak password is ``422`` with a field-level checklist.
    """

    authentication_classes = ()
    permission_classes = (AllowAny,)

    @extend_schema(
        tags=[_AUTH_TAG],
        operation_id="confirmPasswordReset",
        summary="Set a new password using the reset token",
        description="Set a new password from the emailed token; revokes all sessions.",
        request=PasswordResetConfirmSerializer,
        responses={
            204: OpenApiResponse(description="Password reset; all sessions revoked."),
            400: OpenApiResponse(ProblemDetailSerializer, description="Malformed request."),
            410: OpenApiResponse(ProblemDetailSerializer, description="Reset token expired."),
            422: OpenApiResponse(ProblemDetailSerializer, description="Invalid token / weak password."),
        },
    )
    def post(self, request: Request) -> Response:
        instance = request.path
        serializer = PasswordResetConfirmSerializer(data=request.data)
        if not serializer.is_valid():
            return validation_problem(serializer.errors, instance=instance, request=request)
        data = serializer.validated_data
        command = ResetPasswordCommand(token=str(data["token"]), new_password=str(data["newPassword"]))
        try:
            composition.build_reset_password_handler().handle(command)
        except ApplicationError as exc:
            return application_problem(exc, instance=instance, request=request)
        correlation_id = request_id(request)
        return Response(status=204, headers={"X-Request-ID": correlation_id})


class SessionCollectionView(APIView):
    """POST /api/v1/auth/sessions — authenticate and establish a session (API-001 §4.4)."""

    authentication_classes = ()
    permission_classes = (AllowAny,)

    @extend_schema(
        tags=[_AUTH_TAG],
        operation_id="auth_session_create",
        summary="Log in (create a session)",
        description="Verify credentials and issue an access token (+ rotating refresh token).",
        request=SessionCreateRequestSerializer,
        responses={
            201: SessionResponseSerializer,
            400: OpenApiResponse(ProblemDetailSerializer, description="Malformed request."),
            401: OpenApiResponse(ProblemDetailSerializer, description="Invalid credentials."),
            403: OpenApiResponse(ProblemDetailSerializer, description="Account suspended or email not verified."),
        },
    )
    def post(self, request: Request) -> Response:
        instance = request.path
        serializer = SessionCreateRequestSerializer(data=request.data)
        if not serializer.is_valid():
            return validation_problem(serializer.errors, instance=instance, request=request)
        data = serializer.validated_data
        command = AuthenticateUserCommand(email=str(data["email"]), password=str(data["password"]))
        try:
            result = composition.build_authenticate_user_handler().handle(command)
        except ApplicationError as exc:
            return application_problem(exc, instance=instance, request=request)
        tokens = composition.build_token_service().issue(subject=result.user.id)
        response = _envelope(request, _session_resource(tokens, user=result.user), status=201)
        _set_refresh_cookie(response, tokens.refresh_token)
        return response


class TokenRefreshView(APIView):
    """POST /api/v1/auth/token/refresh — rotate the refresh token (API-001 §4.5)."""

    authentication_classes = ()
    permission_classes = (AllowAny,)

    @extend_schema(
        tags=[_AUTH_TAG],
        operation_id="auth_token_refresh",
        summary="Refresh the access token",
        description="Exchange a valid rotating refresh token for a new access/refresh pair.",
        request=TokenRefreshRequestSerializer,
        responses={
            200: TokenRefreshResponseSerializer,
            401: OpenApiResponse(ProblemDetailSerializer, description="Invalid/expired refresh."),
        },
    )
    def post(self, request: Request) -> Response:
        instance = request.path
        serializer = TokenRefreshRequestSerializer(data=request.data)
        if not serializer.is_valid():
            return validation_problem(serializer.errors, instance=instance, request=request)
        refresh_token = _extract_refresh_token(request, dict(serializer.validated_data))
        if refresh_token is None:
            return unauthorized_problem(instance=instance, request=request, detail="A refresh token is required.")
        command = RefreshTokenCommand(refresh_token=refresh_token)
        try:
            tokens = composition.build_refresh_token_handler().handle(command)
        except ApplicationError as exc:
            return application_problem(exc, instance=instance, request=request)
        response = _envelope(request, _session_resource(tokens), status=200)
        _set_refresh_cookie(response, tokens.refresh_token)
        return response


class CurrentSessionView(APIView):
    """DELETE /api/v1/auth/sessions/current — revoke the current session (API-001 §4.6)."""

    authentication_classes = (CredentialAwareJWTAuthentication,)
    permission_classes = (IsAuthenticated,)

    @extend_schema(
        tags=[_AUTH_TAG],
        operation_id="auth_session_current_delete",
        summary="Log out (revoke the current session)",
        description="Blacklist the session's refresh token. The access token is left to expire.",
        request=None,
        responses={
            204: OpenApiResponse(description="Session revoked."),
            401: OpenApiResponse(ProblemDetailSerializer, description="No valid session."),
        },
    )
    def delete(self, request: Request) -> Response:
        refresh_token = _extract_refresh_token(request, {})
        if refresh_token is not None:
            # Logout is idempotent: an already-unusable token means the session is
            # effectively gone. Nothing more to revoke; still clear the cookie.
            with contextlib.suppress(InvalidTokenError):
                composition.build_logout_handler().handle(LogoutCommand(refresh_token=refresh_token))
        response = Response(status=204)
        _clear_refresh_cookie(response)
        return response


def _optional_str(value: object) -> str | None:
    """Coerce an optional serializer value to ``str | None`` (blank → ``None``)."""
    if value is None:
        return None
    text = str(value)
    return text if text else None
