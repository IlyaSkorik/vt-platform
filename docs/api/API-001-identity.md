# API-001 — Identity API v1.0

**Project:** «Взлёт талантов» — цифровая экосистема для организации детских творческих конкурсов
**Document type:** REST API Contract — Identity domain (design only)
**Status:** Draft for review (v1.0)
**Owner:** Backend / API Architecture Group
**Governing standard:** [API-000 REST API Standards](API-000-rest-api-standards.md) *(normative)*
**Source of truth:** [ARCH-001 §11–§12](../architecture/ARCH-001-vt-platform-architecture.md#11-authentication) · [DATA-001 §4.1](../business/DATA-001-business-data-model.md#41-identity) · [DATA-002 §4.1](../business/DATA-002-business-rules-catalog.md#41-identity-idn) · [DATA-003 §4.1](../business/DATA-003-domain-event-catalog.md#41-identity-idn) · [DATA-004 §4.3](../business/DATA-004-state-machine-catalog.md#43-participant-prt) · [DIA-001 §4.1](../diagrams/DIA-001-entity-relationship-model.md#41-identity)
**Last updated:** 2026-07-05

> This is an **API contract design** for the **Identity** domain. It contains **no** Django code and **no** endpoint implementation. Every endpoint conforms to [API-000](API-000-rest-api-standards.md) (URI versioning, resource naming, status codes, `data`/`meta`/`links` envelope, RFC 9457 Problem Details, JWT/RBAC, idempotency, UUID v7, ISO-8601 UTC). It exposes the Identity business objects of [DATA-001](../business/DATA-001-business-data-model.md), enforces the Identity rules of [DATA-002](../business/DATA-002-business-rules-catalog.md), and produces/consumes the Identity events of [DATA-003](../business/DATA-003-domain-event-catalog.md). It must not contradict its sources.

---

## Table of Contents

1. [Scope & Conventions](#1-scope--conventions)
2. [Resource Overview](#2-resource-overview)
3. [Authentication Model](#3-authentication-model)
4. [Endpoints](#4-endpoints)
   - [Registration](#41-registration)
   - [Email Verification](#42-email-verification)
   - [Phone Verification](#43-phone-verification)
   - [Login](#44-login)
   - [Refresh Token](#45-refresh-token)
   - [Logout](#46-logout)
   - [Password Reset](#47-password-reset)
   - [Current User](#48-current-user)
   - [Sessions](#49-sessions)
   - [Consents](#410-consents)
   - [Roles](#411-roles)
   - [Permissions](#412-permissions)
5. [Common Error Catalog](#5-common-error-catalog)
6. [Endpoint Summary Matrix](#6-endpoint-summary-matrix)

---

## 1. Scope & Conventions

### 1.1 In Scope

Authentication (register, login, logout, refresh, password reset), email & phone verification, the current-user resource, session management, consent management, and read access to roles & permissions — the Identity bounded context ([DATA-001 §3.3](../business/DATA-001-business-data-model.md#33-domain-1--identity)).

### 1.2 Base & Conventions (from API-000)

- **Base path:** `/api/v1` (URI versioning, [API-000 §2](API-000-rest-api-standards.md#2-versioning)).
- **Tag:** `Identity` ([API-000 §25](API-000-rest-api-standards.md#25-openapi-conventions)).
- **Envelope:** single resource under `data`; collections under `data` + `meta.page` + `links` ([API-000 §7](API-000-rest-api-standards.md#7-response-format)).
- **Errors:** RFC 9457 `application/problem+json`; `code` = DATA-002 rule id where a rule is violated ([API-000 §8](API-000-rest-api-standards.md#8-error-format)).
- **Ids:** UUID v7, opaque ([API-000 §23](API-000-rest-api-standards.md#23-uuid-policy)). **Times:** ISO-8601 UTC ([API-000 §22](API-000-rest-api-standards.md#22-time-format)).
- **Headers:** `Authorization: Bearer`, `Idempotency-Key` (creates), `X-Request-ID`, `If-Match` (concurrency) ([API-000 §6](API-000-rest-api-standards.md#6-request-format)).
- **Refresh cookie:** for the web client, the refresh token is an **httpOnly, Secure, SameSite** cookie ([ARCH-001 §11.1](../architecture/ARCH-001-vt-platform-architecture.md#11-authentication)).

### 1.3 Per-Endpoint Fields

Each endpoint specifies: **Method · URL · Purpose · Authentication · Authorization · Request · Response · Status Codes · Business Rules · Events Produced · Events Consumed · Errors.**

### 1.4 Minor-Privacy Note

Children (participants) do **not** hold accounts here ([IDN-004](../business/DATA-002-business-rules-catalog.md#rule-idn-004)); Identity manages **adult** accounts (guardian, teacher, jury, organizer, administrator) and the **consent** they grant for minors. No minor PII is exposed by Identity endpoints.

---

## 2. Resource Overview

| Resource | Collection | DATA-001 object | Aggregate |
|----------|-----------|-----------------|-----------|
| User account | `/users` (self via `/users/me`) | USER_ACCOUNT | USER_ACCOUNT |
| Auth session | `/users/me/sessions` | AUTHENTICATION_SESSION | USER_ACCOUNT |
| Consent | `/consents` | CONSENT | CONSENT |
| Consent type | `/consent-types` | CONSENT_TYPE | CONSENT_TYPE |
| Role | `/roles` | ROLE | ROLE |
| Permission | `/permissions` | PERMISSION | ROLE (ref) |
| Auth (actions) | `/auth/*` | — (controller sub-resources) | — |

> `/auth/*` are **action controllers** with noun segments (`registration`, `sessions`, `token`, `password-reset`, `email-verification`, `phone-verification`) per [API-000 §3.3](API-000-rest-api-standards.md#3-resource-naming) — never verbs.

---

## 3. Authentication Model

Per [ARCH-001 §11](../architecture/ARCH-001-vt-platform-architecture.md#11-authentication) and [API-000 §17](API-000-rest-api-standards.md#17-authentication):

- **Access token:** short-lived JWT (~15 min), sent as `Authorization: Bearer <token>`.
- **Refresh token:** rotating, days-long TTL; **web** stores it in an httpOnly cookie; native clients store it securely and send it in the refresh request body.
- **Rotation + reuse detection:** a replayed refresh token invalidates the whole token family.
- **MFA:** required for privileged roles (Administrator, Organizer, Jury) — [IDN-002](../business/DATA-002-business-rules-catalog.md#rule-idn-002); **step-up** required for high-risk operations.
- **Email verification** gate before sensitive actions — [IDN-001](../business/DATA-002-business-rules-catalog.md#rule-idn-001).

---

## 4. Endpoints

### 4.1 Registration

#### POST /api/v1/auth/registration
- **Method:** POST
- **URL:** `/api/v1/auth/registration`
- **Purpose:** Create a new adult user account and trigger email verification.
- **Authentication:** None (public).
- **Authorization:** Public; rate-limited (auth endpoints, [API-000 §20](API-000-rest-api-standards.md#20-rate-limiting)).
- **Request:** `Idempotency-Key` required ([API-000 §19](API-000-rest-api-standards.md#19-idempotency)).

```json
{
  "email": "parent@example.com",
  "password": "••••••••••",
  "displayName": "Ирина С.",
  "locale": "ru-RU",
  "acceptedTermsVersion": "2026-01"
}
```

- **Response:** `201 Created`, `Location: /api/v1/users/{id}`.

```json
{
  "data": {
    "id": "018f9c2a-7e3b-7c21-9a1b-2c4e6f8a0d11",
    "type": "user",
    "email": "parent@example.com",
    "displayName": "Ирина С.",
    "status": "registered",
    "emailVerified": false,
    "mfaEnabled": false,
    "locale": "ru-RU",
    "createdAt": "2026-07-05T09:12:00Z"
  },
  "meta": { "requestId": "018f9c2a-...-req" }
}
```

- **Status Codes:** `201` created · `400` malformed · `409` email already in use · `422` weak/breached password or missing terms · `429` rate-limited.
- **Business Rules:** [IDN-003](../business/DATA-002-business-rules-catalog.md#rule-idn-003) (one verified email ↔ one active account), [IDN-010](../business/DATA-002-business-rules-catalog.md#rule-idn-010) (terms acceptance), [IDN-004](../business/DATA-002-business-rules-catalog.md#rule-idn-004) (adults only), password policy ([ARCH-001 §11.2](../architecture/ARCH-001-vt-platform-architecture.md#11-authentication)).
- **Events Produced:** `AccountRegistered` ([EVT-IDN-001](../business/DATA-003-domain-event-catalog.md#evt-idn-001)); `TermsAccepted` ([EVT-IDN-007](../business/DATA-003-domain-event-catalog.md#evt-idn-007)).
- **Events Consumed:** —
- **Errors:** `409` email conflict; `422` validation (below).

```json
{
  "type": "https://api.vzlyot-talantov.ru/problems/validation-error",
  "title": "Validation failed",
  "status": 422,
  "detail": "One or more fields are invalid.",
  "instance": "/api/v1/auth/registration",
  "requestId": "018f9c2a-...-req",
  "errors": [
    { "pointer": "/password", "code": "weak-password",
      "detail": "Password fails policy or appears in a breach list." },
    { "pointer": "/acceptedTermsVersion", "code": "IDN-010",
      "detail": "The current terms version must be accepted." }
  ]
}
```

Email-conflict example:
```json
{
  "type": "https://api.vzlyot-talantov.ru/problems/conflict",
  "title": "Email already in use",
  "status": 409,
  "detail": "An active account already exists for this email.",
  "instance": "/api/v1/auth/registration",
  "code": "IDN-003",
  "requestId": "018f9c2a-...-req"
}
```

---

### 4.2 Email Verification

#### POST /api/v1/auth/email-verification/requests
- **Method:** POST · **URL:** `/api/v1/auth/email-verification/requests`
- **Purpose:** (Re)send an email-verification challenge.
- **Authentication:** Bearer (the just-registered/unverified user) **or** the pending-registration context.
- **Authorization:** Self only.
- **Request:** empty body; `Idempotency-Key` recommended.
- **Response:** `202 Accepted` (email dispatched asynchronously, [API-000 §5](API-000-rest-api-standards.md#5-http-status-codes)).
- **Status Codes:** `202` · `401` · `409` already verified · `429`.
- **Business Rules:** [IDN-001](../business/DATA-002-business-rules-catalog.md#rule-idn-001).
- **Events Produced:** *(triggers a `NotificationQueued` in Notifications, [EVT-NTF-001](../business/DATA-003-domain-event-catalog.md#evt-ntf-001))*.
- **Events Consumed:** `AccountRegistered`.
- **Errors:** `409` `already-verified`.

#### POST /api/v1/auth/email-verification/confirmations
- **Method:** POST · **URL:** `/api/v1/auth/email-verification/confirmations`
- **Purpose:** Confirm ownership using the emailed token.
- **Authentication:** None (token is the proof) or Bearer.
- **Authorization:** Token-scoped.
- **Request:**
```json
{ "token": "eyJhbGciOi...verify" }
```
- **Response:** `200 OK`
```json
{ "data": { "id": "018f9c2a-...-d11", "type": "user", "emailVerified": true, "status": "active" },
  "meta": { "requestId": "…" } }
```
- **Status Codes:** `200` · `400` malformed · `410` token expired · `409` already verified · `422` invalid token.
- **Business Rules:** [IDN-001](../business/DATA-002-business-rules-catalog.md#rule-idn-001).
- **Events Produced:** `EmailVerified` ([EVT-IDN-002](../business/DATA-003-domain-event-catalog.md#evt-idn-002)).
- **Events Consumed:** —
- **Errors:** expired token:
```json
{ "type": "https://api.vzlyot-talantov.ru/problems/token-expired",
  "title": "Verification token expired", "status": 410,
  "detail": "Request a new verification email.",
  "instance": "/api/v1/auth/email-verification/confirmations",
  "code": "email-verification-expired", "requestId": "…" }
```

---

### 4.3 Phone Verification

#### POST /api/v1/auth/phone-verification/requests
- **Method:** POST · **URL:** `/api/v1/auth/phone-verification/requests`
- **Purpose:** Send an OTP to a phone number (guardian contact quality; future SMS channel per [ARCH-001 §2.1](../architecture/ARCH-001-vt-platform-architecture.md#2-business-goals)).
- **Authentication:** Bearer (self).
- **Authorization:** Self only.
- **Request:**
```json
{ "phoneNumber": "+7 900 000-00-00" }
```
- **Response:** `202 Accepted`.
- **Status Codes:** `202` · `400` invalid number · `401` · `429` (tight OTP limit).
- **Business Rules:** contact-data validation; PhoneNumber value object ([DATA-001 §8](../business/DATA-001-business-data-model.md#8-value-objects)).
- **Events Produced:** *(SMS `NotificationQueued`)*.
- **Events Consumed:** —
- **Errors:** `429` `otp-rate-limited` with `Retry-After`.

#### POST /api/v1/auth/phone-verification/confirmations
- **Method:** POST · **URL:** `/api/v1/auth/phone-verification/confirmations`
- **Purpose:** Confirm phone ownership with the OTP.
- **Authentication:** Bearer (self).
- **Authorization:** Self only.
- **Request:**
```json
{ "phoneNumber": "+7 900 000-00-00", "otp": "482913" }
```
- **Response:** `200 OK`
```json
{ "data": { "id": "018f9c2a-...-d11", "type": "user", "phoneVerified": true },
  "meta": { "requestId": "…" } }
```
- **Status Codes:** `200` · `400` · `401` · `422` wrong/expired OTP · `429`.
- **Business Rules:** contact validation.
- **Events Produced:** *(profile contact updated)*.
- **Events Consumed:** —
- **Errors:** `422` `invalid-otp`.

---

### 4.4 Login

#### POST /api/v1/auth/sessions
- **Method:** POST · **URL:** `/api/v1/auth/sessions`
- **Purpose:** Authenticate credentials and establish a session (issue access + refresh tokens). "Login" is modeled as **creating a session resource** (noun, [API-000 §3.3](API-000-rest-api-standards.md#3-resource-naming)).
- **Authentication:** None (credentials in body).
- **Authorization:** Public; strict rate limiting + lockout.
- **Request:** `Idempotency-Key` optional.
```json
{ "email": "parent@example.com", "password": "••••••••••" }
```
- **Response:** `201 Created` — access token in body; **refresh token set as httpOnly cookie** for web (native clients receive it in body).
```json
{
  "data": {
    "type": "session",
    "accessToken": "eyJhbGciOi...access",
    "tokenType": "Bearer",
    "expiresIn": 900,
    "user": { "id": "018f9c2a-...-d11", "type": "user", "displayName": "Ирина С.", "emailVerified": true }
  },
  "meta": { "requestId": "…" }
}
```
- **MFA challenge:** if MFA is required and unsatisfied, respond `401` with `code: mfa-required` and an `mfaChallengeId`; the client completes MFA then re-requests.
- **Status Codes:** `201` · `400` · `401` invalid credentials / `mfa-required` · `403` account suspended · `423`→ mapped to `429`/`401` on lockout · `429` rate-limited/locked out.
- **Business Rules:** [IDN-001](../business/DATA-002-business-rules-catalog.md#rule-idn-001) (verification gate for sensitive actions), [IDN-002](../business/DATA-002-business-rules-catalog.md#rule-idn-002) (MFA), [IDN-009](../business/DATA-002-business-rules-catalog.md#rule-idn-009) (lockout/backoff).
- **Events Produced:** `AuthenticationSucceeded` *(session established; audited via `ActionRecorded` [EVT-AUD-001](../business/DATA-003-domain-event-catalog.md#evt-aud-001))*.
- **Events Consumed:** —
- **Errors:** invalid credentials (generic, no user enumeration, [API-000 §26](API-000-rest-api-standards.md#26-security-guidelines)):
```json
{ "type": "https://api.vzlyot-talantov.ru/problems/authentication-failed",
  "title": "Authentication failed", "status": 401,
  "detail": "Invalid email or password.",
  "instance": "/api/v1/auth/sessions", "requestId": "…" }
```
MFA required:
```json
{ "type": "https://api.vzlyot-talantov.ru/problems/mfa-required",
  "title": "Multi-factor authentication required", "status": 401,
  "detail": "Provide a second factor to complete sign-in.",
  "instance": "/api/v1/auth/sessions", "code": "IDN-002",
  "mfaChallengeId": "018f9c2a-...-mfa", "requestId": "…" }
```

---

### 4.5 Refresh Token

#### POST /api/v1/auth/token/refresh
- **Method:** POST · **URL:** `/api/v1/auth/token/refresh`
- **Purpose:** Exchange a valid rotating refresh token for a new access token (and a rotated refresh token).
- **Authentication:** Refresh token — httpOnly cookie (web) or request body (native).
- **Authorization:** Token-family scoped.
- **Request:** empty for web (cookie); native:
```json
{ "refreshToken": "eyJhbGciOi...refresh" }
```
- **Response:** `200 OK`
```json
{ "data": { "type": "session", "accessToken": "eyJ...new", "tokenType": "Bearer", "expiresIn": 900 },
  "meta": { "requestId": "…" } }
```
(Web also receives a rotated refresh cookie.)
- **Status Codes:** `200` · `401` invalid/expired refresh · `403` reuse detected (family revoked) · `429`.
- **Business Rules:** rotation + reuse detection ([ARCH-001 §11.1](../architecture/ARCH-001-vt-platform-architecture.md#11-authentication)).
- **Events Produced:** `AccessTokenRefreshed`; on reuse, `TokenFamilyRevoked` *(audited)*.
- **Events Consumed:** —
- **Errors:** reuse detected:
```json
{ "type": "https://api.vzlyot-talantov.ru/problems/token-reuse-detected",
  "title": "Refresh token reuse detected", "status": 403,
  "detail": "This session has been revoked for your security. Sign in again.",
  "instance": "/api/v1/auth/token/refresh", "requestId": "…" }
```

---

### 4.6 Logout

#### DELETE /api/v1/auth/sessions/current
- **Method:** DELETE · **URL:** `/api/v1/auth/sessions/current`
- **Purpose:** Revoke the current session and its refresh-token family.
- **Authentication:** Bearer (self).
- **Authorization:** Self only.
- **Request:** empty.
- **Response:** `204 No Content` (web: refresh cookie cleared).
- **Status Codes:** `204` · `401`.
- **Business Rules:** session revocation is immediate and audited ([DATA-001 §4.1](../business/DATA-001-business-data-model.md#41-identity)).
- **Events Produced:** `SessionRevoked` *(audited via `ActionRecorded`)*.
- **Events Consumed:** —
- **Errors:** `401` if no valid session.

---

### 4.7 Password Reset

#### POST /api/v1/auth/password-reset/requests
- **Method:** POST · **URL:** `/api/v1/auth/password-reset/requests`
- **Purpose:** Begin password recovery; emails a reset token.
- **Authentication:** None (public).
- **Authorization:** Public; rate-limited.
- **Request:**
```json
{ "email": "parent@example.com" }
```
- **Response:** `202 Accepted` — **always**, whether or not the email exists (no user enumeration, [API-000 §26](API-000-rest-api-standards.md#26-security-guidelines)).
- **Status Codes:** `202` · `400` · `429`.
- **Business Rules:** [IDN-009](../business/DATA-002-business-rules-catalog.md#rule-idn-009) (recovery may lift lockout).
- **Events Produced:** *(`NotificationQueued` reset email)*.
- **Events Consumed:** —
- **Errors:** `429` rate-limited.

#### POST /api/v1/auth/password-reset/confirmations
- **Method:** POST · **URL:** `/api/v1/auth/password-reset/confirmations`
- **Purpose:** Set a new password using the reset token.
- **Authentication:** None (token is the proof).
- **Authorization:** Token-scoped.
- **Request:**
```json
{ "token": "eyJ...reset", "newPassword": "••••••••••" }
```
- **Response:** `204 No Content` (all sessions/refresh families revoked; user must sign in again).
- **Status Codes:** `204` · `400` · `410` token expired · `422` weak/breached password.
- **Business Rules:** password policy; revoke-all-sessions on reset ([ARCH-001 §11.2](../architecture/ARCH-001-vt-platform-architecture.md#11-authentication)).
- **Events Produced:** `PasswordReset`; `AllSessionsRevoked` *(audited)*.
- **Events Consumed:** —
- **Errors:** `422` `weak-password`; `410` `reset-token-expired`.

---

### 4.8 Current User

#### GET /api/v1/users/me
- **Method:** GET · **URL:** `/api/v1/users/me`
- **Purpose:** Return the authenticated user's account and effective roles.
- **Authentication:** Bearer (self).
- **Authorization:** Self only.
- **Request:** supports `?include=roles,notificationPreference` ([API-000 §13](API-000-rest-api-standards.md#13-include-relations)); `ETag` returned.
- **Response:** `200 OK`
```json
{
  "data": {
    "id": "018f9c2a-...-d11", "type": "user",
    "email": "parent@example.com", "displayName": "Ирина С.",
    "status": "active", "emailVerified": true, "phoneVerified": false, "mfaEnabled": false,
    "locale": "ru-RU",
    "roles": [ { "id": "018f...role", "type": "role", "name": "guardian", "scope": "global" } ],
    "createdAt": "2026-07-05T09:12:00Z", "updatedAt": "2026-07-05T09:20:00Z"
  },
  "meta": { "requestId": "…" }
}
```
- **Status Codes:** `200` · `304` (If-None-Match) · `401`.
- **Business Rules:** —
- **Events Produced:** —
- **Events Consumed:** `RoleAssigned` ([EVT-IDN-005](../business/DATA-003-domain-event-catalog.md#evt-idn-005)) *(reflected in roles)*.
- **Errors:** `401`.

#### PATCH /api/v1/users/me
- **Method:** PATCH · **URL:** `/api/v1/users/me`
- **Purpose:** Update self-editable profile fields (display name, locale).
- **Authentication:** Bearer (self); `If-Match` required (optimistic concurrency, [API-000 §21](API-000-rest-api-standards.md#21-caching--concurrency)).
- **Authorization:** Self only.
- **Request:**
```json
{ "displayName": "Ирина Смирнова", "locale": "ru-RU" }
```
- **Response:** `200 OK` (updated representation).
- **Status Codes:** `200` · `400` · `401` · `409`/`412` stale `If-Match` · `422`.
- **Business Rules:** email change is a **separate, verification-gated** flow (not this endpoint) — [IDN-001](../business/DATA-002-business-rules-catalog.md#rule-idn-001), [IDN-003](../business/DATA-002-business-rules-catalog.md#rule-idn-003).
- **Events Produced:** `UserProfileUpdated`.
- **Events Consumed:** —
- **Errors:** `412` precondition failed on stale ETag.

---

### 4.9 Sessions

#### GET /api/v1/users/me/sessions
- **Method:** GET · **URL:** `/api/v1/users/me/sessions`
- **Purpose:** List the user's active authentication sessions (device management).
- **Authentication:** Bearer (self).
- **Authorization:** Self only.
- **Request:** cursor pagination ([API-000 §9](API-000-rest-api-standards.md#9-pagination)).
- **Response:** `200 OK`
```json
{
  "data": [
    { "id": "018f...sess1", "type": "session", "device": "Web · Chrome",
      "current": true, "establishedAt": "2026-07-05T09:12:00Z", "lastSeenAt": "2026-07-05T09:40:00Z" }
  ],
  "meta": { "requestId": "…", "page": { "size": 20, "hasNext": false, "hasPrev": false } },
  "links": { "self": "/api/v1/users/me/sessions?pageSize=20", "next": null, "prev": null }
}
```
- **Status Codes:** `200` · `401`.
- **Business Rules:** —
- **Events Produced:** —
- **Events Consumed:** —
- **Errors:** `401`.

#### DELETE /api/v1/users/me/sessions/{sessionId}
- **Method:** DELETE · **URL:** `/api/v1/users/me/sessions/{sessionId}`
- **Purpose:** Revoke a specific session remotely.
- **Authentication:** Bearer (self); MAY require step-up.
- **Authorization:** Self only (session must belong to the caller).
- **Response:** `204 No Content`.
- **Status Codes:** `204` · `401` · `404` (not the caller's session — existence hidden, [API-000 §26](API-000-rest-api-standards.md#26-security-guidelines)).
- **Business Rules:** immediate revocation, audited.
- **Events Produced:** `SessionRevoked` *(audited)*.
- **Events Consumed:** —
- **Errors:** `404` unknown/foreign session.

---

### 4.10 Consents

Consent is the privacy backbone: a guardian's versioned, purpose-limited authorization for a minor ([DATA-001 §4.1](../business/DATA-001-business-data-model.md#41-identity), [IDN-005](../business/DATA-002-business-rules-catalog.md#rule-idn-005)).

#### GET /api/v1/consent-types
- **Method:** GET · **URL:** `/api/v1/consent-types`
- **Purpose:** List available consent purposes/types (reference data).
- **Authentication:** Bearer.
- **Authorization:** Any authenticated user.
- **Response:** `200 OK` (offset pagination acceptable — small bounded set, [API-000 §9.2](API-000-rest-api-standards.md#9-pagination)).
```json
{ "data": [ { "id": "018f...ct1", "type": "consent-type", "key": "participation", "textVersion": "2026-01" } ],
  "meta": { "requestId": "…" }, "links": { "self": "/api/v1/consent-types" } }
```
- **Status Codes:** `200` · `401`.
- **Business Rules:** [IDN-005](../business/DATA-002-business-rules-catalog.md#rule-idn-005).
- **Events Produced/Consumed:** —
- **Errors:** `401`.

#### POST /api/v1/consents
- **Method:** POST · **URL:** `/api/v1/consents`
- **Purpose:** Grant consent for a specific participant, purpose, and consent-text version.
- **Authentication:** Bearer (self); email **must be verified** ([IDN-001](../business/DATA-002-business-rules-catalog.md#rule-idn-001)).
- **Authorization:** Caller must be a **verified guardian** of the referenced participant ([PRT-003](../business/DATA-002-business-rules-catalog.md#rule-prt-003)); Guardian role required.
- **Request:** `Idempotency-Key` required.
```json
{
  "participantId": "018f...part",
  "consentTypeKey": "participation",
  "consentTextVersion": "2026-01"
}
```
- **Response:** `201 Created`, `Location: /api/v1/consents/{id}`.
```json
{
  "data": {
    "id": "018f...consent", "type": "consent",
    "participantId": "018f...part", "consentTypeKey": "participation",
    "purpose": "participation", "consentTextVersion": "2026-01",
    "status": "active", "grantedAt": "2026-07-05T10:00:00Z", "expiresAt": null
  },
  "meta": { "requestId": "…" }
}
```
- **Status Codes:** `201` · `400` · `401` · `403` not this participant's guardian · `409` active consent for same purpose already exists · `422` unknown purpose / stale text version.
- **Business Rules:** [IDN-005](../business/DATA-002-business-rules-catalog.md#rule-idn-005) (purpose-limited, versioned), [PRT-003](../business/DATA-002-business-rules-catalog.md#rule-prt-003) (guardian scope), enables [PRT-001](../business/DATA-002-business-rules-catalog.md#rule-prt-001)/[APP-001](../business/DATA-002-business-rules-catalog.md#rule-app-001).
- **Events Produced:** `ConsentGranted` ([EVT-IDN-003](../business/DATA-003-domain-event-catalog.md#evt-idn-003)); `ActionRecorded` (consent audit, [AUD-001](../business/DATA-002-business-rules-catalog.md#rule-aud-001)).
- **Events Consumed:** —
- **Errors:** forbidden (not guardian):
```json
{ "type": "https://api.vzlyot-talantov.ru/problems/forbidden",
  "title": "Not permitted", "status": 403,
  "detail": "You may grant consent only for participants you are the verified guardian of.",
  "instance": "/api/v1/consents", "code": "PRT-003", "requestId": "…" }
```

#### GET /api/v1/consents
- **Method:** GET · **URL:** `/api/v1/consents`
- **Purpose:** List consents the caller granted (filter by participant/purpose/status).
- **Authentication:** Bearer (self).
- **Authorization:** Returns only consents **granted by the caller** for **their** participants (scope-enforced, [API-000 §10.3](API-000-rest-api-standards.md#10-filtering)).
- **Request:** `?participant=&purpose=&status=active` (§10); cursor pagination.
- **Response:** `200 OK` (collection envelope).
- **Status Codes:** `200` · `400` · `401`.
- **Business Rules:** [PRT-003](../business/DATA-002-business-rules-catalog.md#rule-prt-003).
- **Events Produced/Consumed:** —
- **Errors:** `400` unknown filter.

#### DELETE /api/v1/consents/{consentId}
- **Method:** DELETE · **URL:** `/api/v1/consents/{consentId}`
- **Purpose:** **Withdraw** a consent (soft — consent becomes `withdrawn`, never hard-deleted).
- **Authentication:** Bearer (self); MAY require step-up.
- **Authorization:** Granting guardian only.
- **Response:** `204 No Content`.
- **Status Codes:** `204` · `401` · `403` · `404` (not caller's consent) · `409` already withdrawn.
- **Business Rules:** [IDN-006](../business/DATA-002-business-rules-catalog.md#rule-idn-006) (withdrawal honored & cascades per retention; financial/audit retained under lawful basis — [FIN-008](../business/DATA-002-business-rules-catalog.md#rule-fin-008), [AUD-004](../business/DATA-002-business-rules-catalog.md#rule-aud-004)).
- **Events Produced:** `ConsentWithdrawn` ([EVT-IDN-004](../business/DATA-003-domain-event-catalog.md#evt-idn-004)); `ActionRecorded`.
- **Events Consumed:** —
- **Errors:** `409` `already-withdrawn`.

---

### 4.11 Roles

#### GET /api/v1/roles
- **Method:** GET · **URL:** `/api/v1/roles`
- **Purpose:** List defined roles (reference/governance data).
- **Authentication:** Bearer.
- **Authorization:** **Administrator** only (or Organizer/Institution Admin for the subset they may assign). Others → `403`.
- **Request:** offset pagination acceptable (small bounded set, [API-000 §9.2](API-000-rest-api-standards.md#9-pagination)).
- **Response:** `200 OK`
```json
{
  "data": [
    { "id": "018f...role", "type": "role", "name": "jury", "scopeType": "competition",
      "description": "Evaluates assigned performances" }
  ],
  "meta": { "requestId": "…" }, "links": { "self": "/api/v1/roles?page=1&pageSize=50" }
}
```
- **Status Codes:** `200` · `401` · `403`.
- **Business Rules:** [IDN-008](../business/DATA-002-business-rules-catalog.md#rule-idn-008) (scope), roles per [ARCH-001 §12.2](../architecture/ARCH-001-vt-platform-architecture.md#12-authorization-rbac).
- **Events Produced/Consumed:** —
- **Errors:** `403` forbidden.

#### GET /api/v1/users/me/roles
- **Method:** GET · **URL:** `/api/v1/users/me/roles`
- **Purpose:** List the caller's effective role assignments and scopes.
- **Authentication:** Bearer (self).
- **Authorization:** Self only.
- **Response:** `200 OK`
```json
{ "data": [ { "id": "018f...ra", "type": "role-assignment", "role": "organizer",
  "scopeType": "competition", "scopeId": "018f...comp", "grantedAt": "2026-06-01T00:00:00Z" } ],
  "meta": { "requestId": "…" } }
```
- **Status Codes:** `200` · `401`.
- **Business Rules:** [IDN-008](../business/DATA-002-business-rules-catalog.md#rule-idn-008).
- **Events Produced:** —
- **Events Consumed:** `RoleAssigned` ([EVT-IDN-005](../business/DATA-003-domain-event-catalog.md#evt-idn-005)).
- **Errors:** `401`.

> **Note.** Granting/revoking roles to *other* users is an administrative operation governed by the Identity/Institutions admin surface (scoped, MFA-required, audited). Its full contract is specified in the administration API (future `API-002`); this document exposes only self-role reads and the assignment **event** consumption, to avoid privilege-escalation surface here ([IDN-008](../business/DATA-002-business-rules-catalog.md#rule-idn-008), [INS-003](../business/DATA-002-business-rules-catalog.md#rule-ins-003)).

---

### 4.12 Permissions

#### GET /api/v1/permissions
- **Method:** GET · **URL:** `/api/v1/permissions`
- **Purpose:** List atomic permissions (governance reference data).
- **Authentication:** Bearer.
- **Authorization:** **Administrator** only.
- **Request:** offset pagination.
- **Response:** `200 OK`
```json
{ "data": [ { "id": "018f...perm", "type": "permission", "key": "competition.publish",
  "description": "Publish a competition's results" } ],
  "meta": { "requestId": "…" }, "links": { "self": "/api/v1/permissions?page=1&pageSize=50" } }
```
- **Status Codes:** `200` · `401` · `403`.
- **Business Rules:** [IDN-008](../business/DATA-002-business-rules-catalog.md#rule-idn-008) (deny by default; least privilege, [ARCH-001 §12.4](../architecture/ARCH-001-vt-platform-architecture.md#12-authorization-rbac)).
- **Events Produced/Consumed:** —
- **Errors:** `403` forbidden.

#### GET /api/v1/roles/{roleId}/permissions
- **Method:** GET · **URL:** `/api/v1/roles/{roleId}/permissions`
- **Purpose:** List permissions grouped under a role.
- **Authentication:** Bearer.
- **Authorization:** Administrator only.
- **Response:** `200 OK` (collection of permissions).
- **Status Codes:** `200` · `401` · `403` · `404` unknown role.
- **Business Rules:** [IDN-008](../business/DATA-002-business-rules-catalog.md#rule-idn-008).
- **Events Produced/Consumed:** —
- **Errors:** `404` unknown role.

---

## 5. Common Error Catalog

All Identity errors are RFC 9457 Problem Details ([API-000 §8](API-000-rest-api-standards.md#8-error-format)). `code` carries a DATA-002 rule id where a business rule is violated.

| `type` (suffix under `/problems/`) | HTTP | `code` | Used by |
|-----------------------------------|------|--------|---------|
| `validation-error` | 400/422 | field/`weak-password`/rule id | registration, password reset, profile |
| `conflict` | 409 | `IDN-003` | registration (email in use) |
| `authentication-failed` | 401 | — | login |
| `mfa-required` | 401 | `IDN-002` | login (privileged) |
| `insufficient-authentication` | 401 | — | step-up required |
| `account-suspended` | 403 | `IDN-009` | login/actions on suspended account |
| `forbidden` | 403 | `PRT-003`/`IDN-008` | consents, roles, permissions |
| `not-found` | 404 | — | scoped session/consent/role (existence hidden) |
| `token-expired` | 410 | `email-verification-expired`/`reset-token-expired` | verification, password reset |
| `token-reuse-detected` | 403 | — | refresh |
| `already-verified` / `already-withdrawn` | 409 | — | verification, consent withdrawal |
| `rate-limited` | 429 | — | all auth endpoints (`Retry-After`) |

Generic 401 example:
```json
{ "type": "https://api.vzlyot-talantov.ru/problems/unauthorized",
  "title": "Authentication required", "status": 401,
  "detail": "A valid access token is required.",
  "instance": "/api/v1/users/me", "requestId": "018f9c2a-...-req" }
```

---

## 6. Endpoint Summary Matrix

| # | Method | URL | Auth | Authorization | Key rules | Events produced |
|---|--------|-----|------|---------------|-----------|-----------------|
| 1 | POST | `/auth/registration` | Public | — | IDN-003, IDN-010, IDN-004 | AccountRegistered, TermsAccepted |
| 2 | POST | `/auth/email-verification/requests` | Self | Self | IDN-001 | (NotificationQueued) |
| 3 | POST | `/auth/email-verification/confirmations` | Token | Token | IDN-001 | EmailVerified |
| 4 | POST | `/auth/phone-verification/requests` | Self | Self | contact validation | (NotificationQueued) |
| 5 | POST | `/auth/phone-verification/confirmations` | Self | Self | contact validation | (contact updated) |
| 6 | POST | `/auth/sessions` (login) | Public | — | IDN-001, IDN-002, IDN-009 | AuthenticationSucceeded |
| 7 | POST | `/auth/token/refresh` | Refresh token | Family | rotation/reuse | AccessTokenRefreshed |
| 8 | DELETE | `/auth/sessions/current` (logout) | Self | Self | revoke | SessionRevoked |
| 9 | POST | `/auth/password-reset/requests` | Public | — | IDN-009 | (NotificationQueued) |
| 10 | POST | `/auth/password-reset/confirmations` | Token | Token | password policy | PasswordReset, AllSessionsRevoked |
| 11 | GET | `/users/me` | Self | Self | — | — |
| 12 | PATCH | `/users/me` | Self | Self | IDN-001, IDN-003 | UserProfileUpdated |
| 13 | GET | `/users/me/sessions` | Self | Self | — | — |
| 14 | DELETE | `/users/me/sessions/{id}` | Self | Self | revoke | SessionRevoked |
| 15 | GET | `/consent-types` | Auth | Any | IDN-005 | — |
| 16 | POST | `/consents` | Self (verified) | Guardian of participant | IDN-005, PRT-003 | ConsentGranted |
| 17 | GET | `/consents` | Self | Granting guardian | PRT-003 | — |
| 18 | DELETE | `/consents/{id}` | Self | Granting guardian | IDN-006, FIN-008, AUD-004 | ConsentWithdrawn |
| 19 | GET | `/roles` | Auth | Administrator | IDN-008 | — |
| 20 | GET | `/users/me/roles` | Self | Self | IDN-008 | — (consumes RoleAssigned) |
| 21 | GET | `/permissions` | Auth | Administrator | IDN-008 | — |
| 22 | GET | `/roles/{id}/permissions` | Auth | Administrator | IDN-008 | — |

**22 endpoints** across the Identity domain, all compliant with [API-000](API-000-rest-api-standards.md).

---

*End of document — API-001 Identity API v1.0 (contract design). No Django code, no implementation. Governed by [API-000](API-000-rest-api-standards.md); exposes [DATA-001 §4.1](../business/DATA-001-business-data-model.md#41-identity), enforces [DATA-002 §4.1](../business/DATA-002-business-rules-catalog.md#41-identity-idn), emits [DATA-003 §4.1](../business/DATA-003-domain-event-catalog.md#41-identity-idn).*
