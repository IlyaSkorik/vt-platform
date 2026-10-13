"""``GET /users/me`` — the current-user composition endpoint.

Composes two independent bounded contexts into one response the client needs but
neither context should own (ARCH-001 §14):

* **Identity** supplies the authenticated account (via its ``CurrentUserHandler``,
  rendered through Identity's own shared ``user_resource`` projection so the wire
  shape never drifts from the other Identity endpoints).
* **Organization** supplies the account's staff status (via the published
  ``StaffMembershipReadService`` cross-context read model), or ``None`` for the
  vast majority of users who are not staff.
* **Platform** supplies whether the account operates the platform itself — the
  flag the client routes the operator's console on.
* **Organization** also supplies which modules the account's organization holds,
  so the panel can render the parts of the platform it was sold and no others.

The view depends only on each context's *application/presentation* seams — never
on the other's domain — so composing here introduces no coupling between them.
Authentication is the same stateless-JWT scheme the rest of the API uses; the
account id comes from the validated token.
"""

from __future__ import annotations

import uuid
from typing import Any

from drf_spectacular.utils import OpenApiResponse, extend_schema
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.composition.presentation.api.v1.serializers import CurrentUserResponseSerializer
from apps.identity.application.exceptions import ApplicationError, UserNotFoundError
from apps.identity.infrastructure.auth import CredentialAwareJWTAuthentication
from apps.identity.presentation.api.v1.auth import composition as identity_composition
from apps.identity.presentation.api.v1.problems import (
    application_problem,
    request_id,
    unauthorized_problem,
)
from apps.identity.presentation.api.v1.resources import user_resource
from apps.organization.application.dto import StaffMembershipView
from apps.organization.composition import (
    build_enabled_modules_read_service,
    build_staff_membership_read_service,
)
from apps.organization.domain.value_objects import MembershipStatus, StaffRole
from apps.organization.presentation.scope import acting_organization_id
from apps.platform.composition import build_platform_access_read_service

_TAG = "Identity"


def _staff_membership_resource(view: StaffMembershipView | None) -> dict[str, Any] | None:
    """Project the staff read model into the ``staffMembership`` payload (or ``None``)."""
    if view is None:
        return None
    # The organization is part of the answer now: with several connected to the
    # platform, "staff" is a fact about a person *and* which organization.
    return {"role": view.role, "status": view.status, "organizationId": view.organization_id}


def _enabled_modules(membership: StaffMembershipView | None) -> list[str]:
    """Which modules the caller's organization holds, sorted for a stable payload.

    Empty for anyone who is not staff: modules describe what an *organization* was
    sold, and a participant's cabinet is not gated by them. The client must treat
    this as presentation only — the enforcing gate is
    :class:`~apps.organization.presentation.permissions.IsModuleEnabled` on the
    endpoints themselves.
    """
    if membership is None:
        return []
    try:
        organization_id = uuid.UUID(membership.organization_id)
    except (ValueError, TypeError):  # pragma: no cover - defensive
        return []
    return sorted(build_enabled_modules_read_service().for_organization(organization_id))


def _acting_membership(request: Request) -> StaffMembershipView | None:
    """The membership a platform operator holds *while inside* an organization.

    Synthesised, not stored: nothing grants the operator a seat in somebody else's
    organization, and a real row would outlive the visit and show up in their staff
    roster. It is an OWNER because that is what the request can actually do — the
    panel gates on this, and a membership that understated it would hide screens the
    operator is about to be asked about.

    It lives only as long as the header does, so it is also how the panel knows to
    render itself at all: without it ``/users/me`` says "not staff" and the client
    sends the operator back to their console.
    """
    organization_id = acting_organization_id(request)
    if organization_id is None:
        return None
    return StaffMembershipView(
        role=StaffRole.OWNER.value,
        status=MembershipStatus.ACTIVE.value,
        organization_id=str(organization_id),
    )


class CurrentUserView(APIView):
    """GET /api/v1/users/me — the composed current-user resource."""

    authentication_classes = (CredentialAwareJWTAuthentication,)
    permission_classes = (IsAuthenticated,)

    @extend_schema(
        tags=[_TAG],
        operation_id="getCurrentUser",
        summary="Get the current user composed with staff membership",
        description=(
            "Return the authenticated account (Identity) composed with its staff "
            "membership (Organization) and whether it operates the platform itself. "
            "`staffMembership` is null for non-staff users; `platformAdmin` is false "
            "for everyone but the platform's own operators."
        ),
        request=None,
        responses={
            200: CurrentUserResponseSerializer,
            401: OpenApiResponse(description="No valid session."),
        },
    )
    def get(self, request: Request) -> Response:
        user_id = str(request.user.id)
        try:
            user = identity_composition.build_current_user_handler().handle(user_id)
        except UserNotFoundError:
            return unauthorized_problem(instance=request.path, request=request, detail="Профиль пользователя не найден. Войдите в систему заново.")
        except ApplicationError as exc:
            return application_problem(exc, instance=request.path, request=request)

        # The staff read model keys off the raw user UUID. A malformed subject can
        # never reach here (the JWT auth already validated it), so parsing is safe.
        # An operator who has stepped into an organization is answered *as* that
        # organization's staff: the panel renders from this payload, so saying what
        # is true of the account rather than of the request would show them their
        # own empty cabinet while every call they make lands in someone else's.
        membership = _acting_membership(request) or build_staff_membership_read_service().active_for_user(uuid.UUID(user_id))
        platform_admin = build_platform_access_read_service().is_platform_administrator(uuid.UUID(user_id))
        enabled_modules = _enabled_modules(membership)

        correlation_id = request_id(request)
        body = {
            "user": user_resource(user),
            "staffMembership": _staff_membership_resource(membership),
            "platformAdmin": platform_admin,
            "enabledModules": enabled_modules,
        }
        return Response(
            {"data": body, "meta": {"requestId": correlation_id}},
            status=200,
            headers={"X-Request-ID": correlation_id},
        )
