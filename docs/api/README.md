# API Documentation

## Purpose

Define the platform's API contracts and the standards every endpoint must follow. The API is the primary integration surface (API First): the web SPA, future mobile apps, and integrations are all consumers of the same versioned contract.

## Scope

- **In scope:** API design guidelines, versioning & deprecation policy, error format (RFC 9457), pagination/filtering conventions, authentication headers, the OpenAPI 3.1 contract, and generated-client guidance.
- **Out of scope:** internal domain design (see [../architecture](../architecture/README.md)) and endpoint handler code.

## Prefix

Documents in this domain use the `API-` prefix (e.g. `API-001-design-guidelines.md`).

## Documents

| ID | Title | Status |
|----|-------|--------|
| API-000 | [REST API Standards v1.0](API-000-rest-api-standards.md) | **Approved (normative)** |
| API-001 | [Identity API v1.0](API-001-identity.md) | Draft for review |

> **API-000 is the official, normative REST API standard** — every current and future endpoint MUST comply. It refines the API architecture established in [ARCH-001 §10](../architecture/ARCH-001-vt-platform-architecture.md#10-api-architecture) and covers versioning, resource naming, methods, status codes, request/response/error formats (RFC 9457), pagination, filtering, auth (JWT/RBAC), idempotency, rate limiting, caching, UUID v7, lifecycle, OpenAPI conventions, security, and a per-endpoint design checklist.
>
> **API-001 (Identity)** is the first per-domain contract built to the API-000 standard: authentication, registration, verification, sessions, password reset, current user, consents, roles, and permissions.

## Future Documents

- `API-002` … — Per-domain contracts (Participants, Institutions, Competitions, Applications, Performances, Judging, Results, Finance, Notifications), each built to API-000.
- OpenAPI 3.1 contract (`openapi.yaml`) & schema governance, generated to match these designs.
- Webhooks / outbound integration contracts.
- Generated-client usage guidance.
