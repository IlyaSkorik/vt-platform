"""Account self-service controllers — what a person may change about their own account.

The sub-resources of ``/users/me``, one per thing that can change: the password,
the email address, the phone number. Nouns, not verbs (API-000 §3.3), and ``PUT``
rather than ``POST`` because each replaces a single value the account has exactly
one of.

Same shape as every other Identity controller:

    HTTP request → serializer (validate) → command → handler → DTO → HTTP response

The account is always the caller's own, taken from the validated token and never
from the request body: there is no path here by which one account can reach
another, which is why these live apart from the operator-driven user
administration the context also has use cases for.
"""

from __future__ import annotations

from drf_spectacular.utils import OpenApiResponse, extend_schema
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.identity.application.commands import (
    ChangeEmailCommand,
    ChangePasswordCommand,
    ChangePhoneCommand,
    RequestEmailVerificationCommand,
)
from apps.identity.application.dto import UserDto
from apps.identity.application.exceptions import ApplicationError
from apps.identity.infrastructure.auth import CredentialAwareJWTAuthentication
from apps.identity.presentation.api.v1.account.serializers import (
    AccountEmailRequestSerializer,
    AccountPasswordRequestSerializer,
    AccountPhoneRequestSerializer,
    AccountResponseSerializer,
)
from apps.identity.presentation.api.v1.auth import composition
from apps.identity.presentation.api.v1.auth.serializers import ProblemDetailSerializer
from apps.identity.presentation.api.v1.problems import (
    application_problem,
    request_id,
    validation_problem,
)
from apps.identity.presentation.api.v1.resources import user_resource

_TAG = "Identity"

_PROBLEM_RESPONSES = {
    400: OpenApiResponse(ProblemDetailSerializer, description="Malformed request."),
    401: OpenApiResponse(ProblemDetailSerializer, description="No valid session, or the current password is wrong."),
}


class _AccountView(APIView):
    """Shared plumbing: the caller's own account, and the one response shape."""

    authentication_classes = (CredentialAwareJWTAuthentication,)
    permission_classes = (IsAuthenticated,)

    def _envelope(self, request: Request, user: UserDto) -> Response:
        correlation_id = request_id(request)
        return Response(
            {"data": user_resource(user), "meta": {"requestId": correlation_id}},
            status=200,
            headers={"X-Request-ID": correlation_id},
        )


class AccountPasswordView(_AccountView):
    """``PUT /api/v1/users/me/password`` — change your own password."""

    @extend_schema(
        tags=[_TAG],
        operation_id="changeOwnPassword",
        summary="Change the signed-in account's password",
        description=(
            "Replace the account's password. The current password is required: a session "
            "left open must not be enough to lock its owner out. The session survives the "
            "change — an emailed reset (`/auth/password-reset/confirmations`) is the flow "
            "that revokes every issued credential."
        ),
        request=AccountPasswordRequestSerializer,
        responses={
            200: AccountResponseSerializer,
            **_PROBLEM_RESPONSES,
            422: OpenApiResponse(ProblemDetailSerializer, description="The new password is too weak."),
        },
    )
    def put(self, request: Request) -> Response:
        serializer = AccountPasswordRequestSerializer(data=request.data)
        if not serializer.is_valid():
            return validation_problem(serializer.errors, instance=request.path, request=request)
        data = serializer.validated_data
        command = ChangePasswordCommand(
            user_id=str(request.user.id),
            current_password=str(data["currentPassword"]),
            new_password=str(data["newPassword"]),
        )
        try:
            result = composition.build_change_password_handler().handle(command)
        except ApplicationError as exc:
            return application_problem(exc, instance=request.path, request=request)
        return self._envelope(request, result.user)


class AccountEmailView(_AccountView):
    """``PUT /api/v1/users/me/email`` — move the account to another address."""

    @extend_schema(
        tags=[_TAG],
        operation_id="changeOwnEmail",
        summary="Change the signed-in account's email address",
        description=(
            "Replace the account's email address. The current password is required, because "
            "the address is the account's recovery channel. The new address starts unverified "
            "and a fresh verification link is sent to it; the old one stops being the account's."
        ),
        request=AccountEmailRequestSerializer,
        responses={
            200: AccountResponseSerializer,
            **_PROBLEM_RESPONSES,
            409: OpenApiResponse(ProblemDetailSerializer, description="That address already belongs to an account."),
            422: OpenApiResponse(ProblemDetailSerializer, description="The address is not a valid email."),
        },
    )
    def put(self, request: Request) -> Response:
        serializer = AccountEmailRequestSerializer(data=request.data)
        if not serializer.is_valid():
            return validation_problem(serializer.errors, instance=request.path, request=request)
        data = serializer.validated_data
        command = ChangeEmailCommand(
            user_id=str(request.user.id),
            new_email=str(data["email"]),
            current_password=str(data["currentPassword"]),
        )
        try:
            result = composition.build_change_email_handler().handle(command)
            # Sent from here rather than from a subscriber on `EmailChanged`: an
            # address the platform cannot reach is an account nobody can recover,
            # so the change is not reported as done unless the challenge went out.
            composition.build_request_email_verification_handler().handle(RequestEmailVerificationCommand(email=result.user.email))
        except ApplicationError as exc:
            return application_problem(exc, instance=request.path, request=request)
        return self._envelope(request, result.user)


class AccountPhoneView(_AccountView):
    """``PUT /api/v1/users/me/phone`` — set or replace the account's phone number."""

    @extend_schema(
        tags=[_TAG],
        operation_id="changeOwnPhone",
        summary="Set or replace the signed-in account's phone number",
        description=(
            "Set the account's phone number. No password is asked for: unlike the address, "
            "the phone is a way for an organizer to reach the applicant, not a way back into "
            "the account. The number starts unverified."
        ),
        request=AccountPhoneRequestSerializer,
        responses={
            200: AccountResponseSerializer,
            **_PROBLEM_RESPONSES,
            409: OpenApiResponse(ProblemDetailSerializer, description="That number already belongs to an account."),
            422: OpenApiResponse(ProblemDetailSerializer, description="The number is not a valid phone number."),
        },
    )
    def put(self, request: Request) -> Response:
        serializer = AccountPhoneRequestSerializer(data=request.data)
        if not serializer.is_valid():
            return validation_problem(serializer.errors, instance=request.path, request=request)
        command = ChangePhoneCommand(
            user_id=str(request.user.id),
            new_phone=str(serializer.validated_data["phone"]),
        )
        try:
            result = composition.build_change_phone_handler().handle(command)
        except ApplicationError as exc:
            return application_problem(exc, instance=request.path, request=request)
        return self._envelope(request, result.user)
