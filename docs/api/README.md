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
| — | _No documents yet._ | — |

> API architecture principles are established in [ARCH-001 §10](../architecture/ARCH-001-vt-platform-architecture.md#10-api-architecture).

## Future Documents

- `API-001` — API design guidelines & conventions.
- `API-002` — Versioning & deprecation policy.
- `API-003` — Error handling (Problem Details) standard.
- `API-004` — OpenAPI 3.1 contract (`openapi.yaml`) & schema governance.
- `API-005` — Authentication & authorization for API consumers.
