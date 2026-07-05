# API-000 — REST API Standards v1.0

**Project:** «Взлёт талантов» — цифровая экосистема для организации детских творческих конкурсов
**Document type:** Official Platform API Standard (normative)
**Status:** Approved baseline (v1.0)
**Owner:** API Architecture Group
**Source of truth:** [ARCH-001](../architecture/ARCH-001-vt-platform-architecture.md) · [DATA-001](../business/DATA-001-business-data-model.md) · [DATA-002](../business/DATA-002-business-rules-catalog.md) · [DATA-003](../business/DATA-003-domain-event-catalog.md) · [DATA-004](../business/DATA-004-state-machine-catalog.md) · [DIA-001](../diagrams/DIA-001-entity-relationship-model.md)
**Last updated:** 2026-07-05

> This document is the **official, normative REST API standard** for the VT Platform. **Every** current and future endpoint MUST comply. It defines *how* APIs are shaped and behaved; it does **not** implement endpoints, does **not** contain the OpenAPI contract, and does **not** contain Django code. It refines the API decisions of [ARCH-001 §10](../architecture/ARCH-001-vt-platform-architecture.md#10-api-architecture), the authentication/authorization decisions of [§11–§12](../architecture/ARCH-001-vt-platform-architecture.md#11-authentication), and exposes the business objects ([DATA-001](../business/DATA-001-business-data-model.md)), rules ([DATA-002](../business/DATA-002-business-rules-catalog.md)), and state machines ([DATA-004](../business/DATA-004-state-machine-catalog.md)) as resources. It must not contradict its sources.
>
> **Normative keywords** — **MUST**, **MUST NOT**, **SHOULD**, **SHOULD NOT**, **MAY** — are used per RFC 2119. Code/JSON blocks are **illustrative**, not implementations.

---

## Table of Contents

1. [API Philosophy](#1-api-philosophy) · 2. [Versioning](#2-versioning) · 3. [Resource Naming](#3-resource-naming) · 4. [HTTP Methods](#4-http-methods) · 5. [HTTP Status Codes](#5-http-status-codes) · 6. [Request Format](#6-request-format) · 7. [Response Format](#7-response-format) · 8. [Error Format](#8-error-format) · 9. [Pagination](#9-pagination) · 10. [Filtering](#10-filtering) · 11. [Sorting](#11-sorting) · 12. [Sparse Fields](#12-sparse-fields) · 13. [Include Relations](#13-include-relations) · 14. [Searching](#14-searching) · 15. [Bulk Operations](#15-bulk-operations) · 16. [File Upload](#16-file-upload) · 17. [Authentication](#17-authentication) · 18. [Authorization](#18-authorization) · 19. [Idempotency](#19-idempotency) · 20. [Rate Limiting](#20-rate-limiting) · 21. [Caching](#21-caching) · 22. [Time Format](#22-time-format) · 23. [UUID Policy](#23-uuid-policy) · 24. [API Lifecycle](#24-api-lifecycle) · 25. [OpenAPI Conventions](#25-openapi-conventions) · 26. [Security Guidelines](#26-security-guidelines) · 27. [API Design Checklist](#27-api-design-checklist)

---

## 1. API Philosophy

The VT Platform API is the **primary integration surface** of the product. The web SPA is only one consumer; mobile apps and institutional integrations are first-class future consumers ([ARCH-001 §4.4](../architecture/ARCH-001-vt-platform-architecture.md#4-architecture-principles)).

- **API First.** Every capability is exposed through a versioned, contract-first API before any UI is built. The contract (OpenAPI 3.1, §25) is the source of truth; clients and mocks are generated from it ([ARCH-001 §10.1](../architecture/ARCH-001-vt-platform-architecture.md#10-api-architecture)).
- **Resource-oriented design.** The API models **business resources** (the entities of [DIA-001](../diagrams/DIA-001-entity-relationship-model.md)), not procedures. State changes are expressed as operations on resources, never as RPC verbs in URLs.
- **Consistency over cleverness.** A predictable, uniform API beats a locally clever one. Every endpoint uses the same naming, pagination, filtering, error, and auth conventions defined here. Surprises are bugs.
- **Predictable responses.** Same request shape → same response shape. Field names, envelopes, and error structures are uniform across all resources.
- **Idempotency.** Unsafe operations that clients may retry (creates, payments) MUST be safely repeatable via `Idempotency-Key` (§19), so a network retry never double-charges or double-submits.
- **Backward compatibility.** Within a major version, changes are **additive only**. Breaking changes require a new major version with a deprecation window (§2, §24). Consumers must never break because the platform shipped.
- **Privacy & fairness by default.** The API enforces minor-data protection and judging fairness at the contract level — pseudonymization to jury, consent gates, scoped visibility ([DATA-002](../business/DATA-002-business-rules-catalog.md) rules JDG-006, APP-001, PRT-006).

---

## 2. Versioning

### 2.1 Scheme — URI Versioning

The platform uses **URI major versioning** ([ARCH-001 §10.2](../architecture/ARCH-001-vt-platform-architecture.md#10-api-architecture)):

```
https://api.vzlyot-talantov.ru/api/v1/participants
                                    ^^^
```

- The version segment is `v<MAJOR>` (`v1`, `v2`, …). Only the **major** version appears in the URI.
- Minor/additive evolution happens **in place** within the same major version — no URI change.
- Every endpoint MUST be mounted under a version segment. Unversioned paths MUST NOT serve business data.

### 2.2 What is Backward-Compatible (allowed within a major version)

- Adding a new endpoint, resource, or optional query parameter.
- Adding a new **optional** request field.
- Adding a new field to a response.
- Adding a new enum value **only** where clients are documented to tolerate unknown values (otherwise it is breaking).
- Adding a new optional response header.

### 2.3 What is Breaking (requires a new major version)

- Removing/renaming a resource, endpoint, field, or query parameter.
- Changing a field's type, meaning, or units.
- Making an optional field required, or tightening validation.
- Changing default behavior (pagination, sorting, filtering semantics).
- Removing or changing the meaning of a status code for an operation.

### 2.4 Rules for Introducing v2

1. `v2` is introduced **only** when a breaking change is unavoidable; additive change MUST stay in `v1`.
2. `v1` and `v2` run **in parallel** for a minimum **6-month deprecation window** ([ARCH-001 §10.2](../architecture/ARCH-001-vt-platform-architecture.md#10-api-architecture)), aligned with the event-versioning window in [DATA-003 §9.3](../business/DATA-003-domain-event-catalog.md#9-event-versioning-policy).
3. Deprecation is announced via `Deprecation` and `Sunset` response headers (§24) and the changelog.
4. A breaking change MUST be recorded in an ADR referenced from the introducing PR ([ARCH-001 §30](../architecture/ARCH-001-vt-platform-architecture.md#30-architecture-decision-records-adr)).
5. `v2` MUST NOT weaken any privacy, fairness, or financial-integrity guarantee of `v1`.

---

## 3. Resource Naming

### 3.1 Core Rules

- **Plural nouns** for collections: `/participants`, `/applications`, `/competitions`.
- **lowercase** only.
- **kebab-case** for multi-word resources: `/judge-assignments`, `/score-aggregations`, `/data-subject-requests`.
- **No verbs in URLs.** Actions are HTTP methods on resources, not URL segments. (`POST /applications`, not `/createApplication`.)
- **Hierarchy via nesting** where a child belongs to one parent aggregate: `/competitions/{id}/nominations`, `/performances/{id}/scorecards`.
- **Identity in the path** uses the resource UUID (§23): `/participants/{participantId}`.
- Query parameters are **camelCase** or lowercase consistently (this standard uses camelCase, e.g., `?pageSize=`, `?sort=`).

### 3.2 Canonical Resource Names (derived from DIA-001 / DATA-001)

| Domain | Collection resources |
|--------|----------------------|
| Identity | `/users`, `/roles`, `/consents` |
| Participants | `/participants`, `/guardians`, `/teachers` |
| Institutions | `/institutions`, `/class-groups` |
| Competitions | `/competitions`, `/competitions/{id}/nominations`, `/competitions/{id}/rounds`, `/competitions/{id}/criteria-sets`, `/competitions/{id}/prizes` |
| Applications | `/applications` |
| Performances | `/performances`, `/performances/{id}/media-assets` |
| Judging | `/jury-members`, `/jury-panels`, `/judge-assignments`, `/scorecards` |
| Results | `/results`, `/rankings`, `/diplomas`, `/result-disputes` |
| Finance | `/orders`, `/invoices`, `/payments`, `/refunds` |
| Notifications | `/notifications`, `/notification-preferences` |
| Analytics | `/reports`, `/data-exports` |
| Audit | `/audit-log-entries`, `/data-subject-requests` |

### 3.3 Sub-resources & Actions

- **Sub-resources** express ownership: `/applications/{id}/performances`.
- **State transitions** that are not naturally a field update MAY use a **controller sub-resource** as a noun, invoked with `POST`, when a plain `PATCH` would be ambiguous. Example: `POST /competitions/{id}/publication` to publish (produces `CompetitionPublished`, [DATA-004 TRN-CMP-001](../business/DATA-004-state-machine-catalog.md#41-competition-cmp)). This is the **only** sanctioned exception to "no verbs" and MUST use a noun (`publication`, not `publish`).
- Singleton sub-resources use singular nouns: `/users/{id}/notification-preference`.

---

## 4. HTTP Methods

| Method | Semantics | Safe | Idempotent | Allowed use |
|--------|-----------|:----:|:----------:|-------------|
| **GET** | Retrieve a resource or collection | ✔ | ✔ | Reads only. MUST NOT change state. Supports filtering/sorting/pagination/sparse/include. |
| **POST** | Create a resource **or** invoke a state-transition controller sub-resource | �’✘ | ✘ (make idempotent via key) | Creation; non-idempotent actions. MUST support `Idempotency-Key` for creates/charges (§19). |
| **PUT** | Full replacement of a resource | ✘ | ✔ | Full, idempotent replacement of a mutable resource where the client sends the complete representation. Rare; prefer PATCH. |
| **PATCH** | Partial update | ✘ | SHOULD be | Partial field updates. Body contains only changed fields (JSON Merge Patch semantics). Used for most mutations, including field-driven state changes. |
| **DELETE** | Remove/retire a resource | ✘ | ✔ | Soft-delete/archive/withdraw per the entity's [Deletion Strategy](../diagrams/DIA-001-entity-relationship-model.md#10-deletion-strategy). MUST honor Restrict rules and Legal Holds. |

Rules:
- **GET/HEAD/OPTIONS are safe** and MUST be side-effect free.
- **PUT/DELETE are idempotent**; repeating them yields the same end state.
- **PATCH SHOULD be idempotent**; where it cannot be, document it.
- Methods not supported on a resource MUST return **405 Method Not Allowed** with an `Allow` header.
- **DELETE** almost never hard-deletes: per [DIA-001 §10](../diagrams/DIA-001-entity-relationship-model.md#10-deletion-strategy) it performs soft-delete/archive/withdraw; true erasure occurs only via the DSAR workflow (`/data-subject-requests`, [AUD-003](../business/DATA-002-business-rules-catalog.md#rule-aud-003)).

---

## 5. HTTP Status Codes

Use the **narrowest correct** code. Only the codes below are sanctioned; introducing others requires an update to this standard.

| Code | Name | When to use |
|------|------|-------------|
| **200** | OK | Successful GET; successful PATCH/PUT returning the representation; successful synchronous action. |
| **201** | Created | Resource created by POST. MUST include a `Location` header and the created representation. |
| **202** | Accepted | Request accepted for **asynchronous** processing (e.g., large media post-processing, bulk import, diploma generation — [ARCH-001 §7.5](../architecture/ARCH-001-vt-platform-architecture.md#7-backend-architecture)). Response references a status/job resource. |
| **204** | No Content | Successful operation with no body (e.g., DELETE, or PATCH where the client opts out of a body). |
| **400** | Bad Request | Malformed syntax: unparseable JSON, wrong types, missing required fields at the **syntactic** level. |
| **401** | Unauthorized | Missing/invalid/expired authentication. Client should (re)authenticate (§17). |
| **403** | Forbidden | Authenticated but not permitted by RBAC/scoping (§18; [DATA-002](../business/DATA-002-business-rules-catalog.md) security rules, e.g., PRT-003, INS-002, JDG-002). |
| **404** | Not Found | Resource does not exist **or** is out of the caller's scope (to avoid leaking existence — §18, §26). |
| **409** | Conflict | The request conflicts with current state: an **invalid state-machine transition** ([DATA-004 §6 Invalid Transition Matrix](../business/DATA-004-state-machine-catalog.md#6-invalid-transition-matrix)), a uniqueness conflict, or an optimistic-concurrency failure. |
| **422** | Unprocessable Content | Syntactically valid but violates a **business rule** ([DATA-002](../business/DATA-002-business-rules-catalog.md)) — e.g., no active consent (APP-001), weights don't sum (CMP-004), refund exceeds capture (FIN-004). |
| **429** | Too Many Requests | Rate limit exceeded (§20). MUST include `Retry-After`. |
| **500** | Internal Server Error | Unexpected server fault. MUST NOT leak internals; MUST carry a correlation id (§6). |

Guidance:
- **400 vs 422:** 400 = the request is malformed (can't be parsed/typed); 422 = the request is well-formed but the business won't accept it. Validation of *format* → 400; violation of a *rule* → 422.
- **409 vs 422:** 409 = conflict with the resource's **current state/version** (retrying later after state changes may succeed); 422 = the request is invalid **regardless of timing**.
- **403 vs 404:** when revealing existence would leak information about minors or other tenants, prefer **404** (§26).

---

## 6. Request Format

### 6.1 Standard Request Headers

| Header | Requirement | Purpose |
|--------|-------------|---------|
| `Authorization: Bearer <access-token>` | Required (except public/auth endpoints) | JWT access token (§17). |
| `Content-Type: application/json; charset=utf-8` | Required for bodies | JSON request bodies. Multipart for uploads (§16). |
| `Accept: application/json` | SHOULD | Content negotiation; default is JSON. Problem responses use `application/problem+json` (§8). |
| `Idempotency-Key: <uuid>` | Required for POST creates/charges | Safe retries (§19). |
| `X-Request-ID: <uuid>` | SHOULD (client-supplied) | Correlation/trace id echoed in responses and logs ([ARCH-001 §19.1](../architecture/ARCH-001-vt-platform-architecture.md#19-logging)). If absent, the server generates one. |
| `If-Match: <etag>` | Required for concurrency-sensitive mutations | Optimistic locking (§21; [ARCH-001 §10.3](../architecture/ARCH-001-vt-platform-architecture.md#10-api-architecture)). |
| `Accept-Language: ru-RU` | MAY | Localization; primary locale `ru-RU` ([ARCH-001 §8.6](../architecture/ARCH-001-vt-platform-architecture.md#8-frontend-architecture)). |

### 6.2 Body Rules

- Request bodies are **JSON** (UTF-8), except file uploads (§16).
- Field names are **camelCase**.
- Timestamps are **ISO-8601 UTC** (§22); money is an object with integer minor units + currency (§7.4; [FIN-001](../business/DATA-002-business-rules-catalog.md#rule-fin-001)).
- Unknown fields in a request SHOULD be rejected with **400** (strict input) on write endpoints to catch client errors early.
- Clients MUST NOT send server-managed fields (id, timestamps, computed values) on create; if sent, they are ignored.

---

## 7. Response Format

### 7.1 Single Resource

```json
{
  "data": {
    "id": "018f9c2a-7e3b-7c21-9a1b-2c4e6f8a0d11",
    "type": "participant",
    "displayAlias": "Участник #A17",
    "ageGroup": { "label": "7–9", "lowerBound": 7, "upperBound": 9 },
    "status": "active",
    "createdAt": "2026-07-05T09:12:00Z",
    "updatedAt": "2026-07-05T09:12:00Z"
  },
  "meta": { "requestId": "018f9c2a-...-req" }
}
```

- Successful single-resource responses wrap the resource under a top-level **`data`** object.
- **`type`** carries the resource type name (matches the OpenAPI schema, §25).
- **`meta`** carries response metadata (e.g., `requestId`); it MUST NOT carry business data.

### 7.2 Collection

```json
{
  "data": [ { "id": "…", "type": "application", "status": "submitted" } ],
  "meta": {
    "requestId": "…",
    "page": { "size": 20, "hasNext": true, "hasPrev": false }
  },
  "links": {
    "self":  "/api/v1/applications?pageSize=20",
    "next":  "/api/v1/applications?pageSize=20&cursor=eyJ...",
    "prev":  null
  }
}
```

- Collections return an **array under `data`**, pagination under `meta.page`, and navigation under **`links`** (§9).

### 7.3 Metadata Rules

- `meta.requestId` MUST echo the correlation id (§6.1).
- Pagination metadata lives under `meta.page` (§9); it MUST NOT include total counts for large collections by default (cursor pagination, §9).
- Rate-limit state is exposed via headers, not the body (§20).
- Responses MUST NOT include null-valued fields solely to pad the shape; absent optional fields MAY be omitted (documented per schema).

### 7.4 Common Value Shapes

- **Money:** `{ "amount": 50000, "currency": "RUB" }` — integer **minor units**, never a float ([FIN-001](../business/DATA-002-business-rules-catalog.md#rule-fin-001)).
- **Timestamps:** ISO-8601 UTC strings (§22).
- **References:** cross-resource references are by **id** (+ `type`), optionally expanded via `?include=` (§13), reflecting the by-identity rule of [DIA-001 §8](../diagrams/DIA-001-entity-relationship-model.md#8-cross-domain-relationships).

---

## 8. Error Format

### 8.1 RFC 9457 Problem Details

All error responses use **`application/problem+json`** ([RFC 9457](https://www.rfc-editor.org/rfc/rfc9457); [ARCH-001 §10.3](../architecture/ARCH-001-vt-platform-architecture.md#10-api-architecture)).

```json
{
  "type": "https://api.vzlyot-talantov.ru/problems/business-rule-violation",
  "title": "Business rule violation",
  "status": 422,
  "detail": "An active guardian consent is required before submitting this application.",
  "instance": "/api/v1/applications",
  "code": "APP-001",
  "requestId": "018f9c2a-...-req",
  "errors": []
}
```

Fields:
- `type` — a stable URI identifying the problem class.
- `title` — short, human-readable summary (stable per `type`).
- `status` — the HTTP status code.
- `detail` — human-readable, request-specific explanation. MUST NOT leak sensitive data.
- `instance` — the request path.
- `code` *(extension)* — machine-readable code; for business-rule violations this is the **DATA-002 Rule ID** (e.g., `APP-001`, `JDG-001`, `FIN-004`).
- `requestId` *(extension)* — correlation id (§6).
- `errors` *(extension)* — array of field/rule-level details (below).

### 8.2 Validation Errors (400 / 422)

```json
{
  "type": "https://api.vzlyot-talantov.ru/problems/validation-error",
  "title": "Validation failed",
  "status": 422,
  "detail": "One or more fields are invalid.",
  "instance": "/api/v1/competitions/{id}/criteria-sets",
  "requestId": "…",
  "errors": [
    { "pointer": "/criteria/weights", "code": "CMP-004",
      "detail": "Criterion weights must sum to 100%." },
    { "pointer": "/schedule/closeDate", "code": "CMP-003",
      "detail": "closeDate must be on or after openDate." }
  ]
}
```

- Each entry has a **`pointer`** (JSON Pointer to the offending field), a **`code`** (rule/validation id), and a **`detail`**.
- Field-shape/type failures use `400`; rule violations use `422` with the DATA-002 rule id in `code`.

### 8.3 Business Rule Violations

- A blocked business rule ([DATA-002](../business/DATA-002-business-rules-catalog.md)) returns **422** with `code` = the rule id and `type` = `.../problems/business-rule-violation`.
- An invalid **state transition** ([DATA-004 §6](../business/DATA-004-state-machine-catalog.md#6-invalid-transition-matrix)) returns **409** with `code` = the invalid-transition id (e.g., `IVT-13`) and a `detail` naming the current and attempted states.
- Authorization denials return **403** (or **404** to avoid leakage, §26) with `type` = `.../problems/forbidden`.

### 8.4 Rules

- Every non-2xx response MUST be a Problem Details document.
- `type` URIs MUST be stable and documented; clients key off `type`/`code`, never off `detail` text.
- Problem responses MUST include `requestId` for support/audit correlation.

---

## 9. Pagination

### 9.1 Cursor Pagination (default)

Cursor pagination is the **default and required** style for all collections ([ARCH-001 §10.3](../architecture/ARCH-001-vt-platform-architecture.md#10-api-architecture)).

```
GET /api/v1/applications?pageSize=20&cursor=eyJvZmZzZXQiOiJ...
```

- `pageSize` — client-requested page size; server enforces a **max** (default 20, max 100). Larger values are clamped.
- `cursor` — opaque, server-generated token encoding position; clients MUST treat it as opaque.
- Response `meta.page` includes `size`, `hasNext`, `hasPrev`; `links.next`/`links.prev` carry ready-to-use cursor URLs.
- Cursor pagination MUST be used for large/growing collections (participants, applications, performances, scorecards, notifications, audit).
- **Total counts are NOT returned by default** (expensive at scale); a bounded `?withCount=true` MAY be offered where cheap.

### 9.2 Offset Pagination (justified exception)

```
GET /api/v1/roles?page=1&pageSize=50
```

- Offset pagination (`page` + `pageSize`) MAY be used **only** for small, bounded, admin-facing lists (e.g., roles, competition templates) where stable ordering and total counts matter and the set is small.
- Its use MUST be justified in the endpoint's OpenAPI description.

---

## 10. Filtering

### 10.1 Convention

Filtering uses query parameters named for the field, optionally with an operator suffix:

```
GET /api/v1/applications?status=submitted&competition={competitionId}
GET /api/v1/performances?participant={participantId}&createdAt[gte]=2026-07-01T00:00:00Z
GET /api/v1/scorecards?round={roundId}&status=locked
```

- **Equality:** `?status=submitted`.
- **Operators:** `[gte]`, `[lte]`, `[gt]`, `[lt]`, `[ne]`, `[in]` (comma-separated). Example: `?ageGroup[in]=7-9,10-12`.
- Multiple filters combine with **AND**.
- Filter values referencing other resources use their **UUID** (`?competition={id}`).

### 10.2 Standard Filter Examples (aligned to DATA-001/DIA-001)

| Filter | Applies to | Example |
|--------|-----------|---------|
| `status` | most stateful resources ([DATA-004](../business/DATA-004-state-machine-catalog.md)) | `?status=accepted` |
| `date` (`createdAt`, `submittedAt`, `publishedAt`) | time-bounded queries | `?submittedAt[gte]=2026-07-01T00:00:00Z` |
| `competition` | applications, performances, results, judge-assignments | `?competition={id}` |
| `nomination` / `ageGroup` / `round` | applications, scorecards | `?round={id}` |
| `teacher` | participants, applications | `?teacher={id}` |
| `participant` | applications, performances, results | `?participant={id}` |
| `institution` | participants, class-groups, reports | `?institution={id}` |

### 10.3 Rules

- Filtering MUST be **scope-enforced**: results are always intersected with the caller's authorization scope (§18) — filters never widen access.
- Unknown filter params MUST return **400**.
- Filtering on minor PII fields is **forbidden**; participants are filtered by opaque ids, and jury-scoped queries never expose identity ([JDG-006](../business/DATA-002-business-rules-catalog.md#rule-jdg-006), [PRT-006](../business/DATA-002-business-rules-catalog.md#rule-prt-006)).

---

## 11. Sorting

```
GET /api/v1/applications?sort=-submittedAt,status
```

- `?sort=` takes a comma-separated list of fields.
- **`-`** prefix = descending; no prefix = ascending.
- Only **allow-listed** sortable fields per resource are permitted (documented in OpenAPI); others return **400**.
- A **deterministic default sort** MUST be defined per collection (typically `-createdAt` then `id`) so cursor pagination is stable.
- Sorting on sensitive fields (scores before results are published, minor PII) is forbidden.

---

## 12. Sparse Fields

```
GET /api/v1/participants/{id}?fields=displayAlias,ageGroup,status
```

- `?fields=` selects a comma-separated subset of top-level fields to return.
- The resource **`id`** and **`type`** are ALWAYS returned regardless of selection.
- Requesting a non-existent or unauthorized field is ignored (not an error) unless it is malformed (→ 400).
- Sparse fieldsets are a **performance** optimization; they MUST NOT be used to bypass authorization — forbidden fields are never returned even if named.

---

## 13. Include Relations

```
GET /api/v1/applications/{id}?include=participant,performances
```

- `?include=` requests related resources to be **compound-documented** alongside the primary resource.
- Included resources are returned under a top-level **`included`** array; the primary resource references them by `{id, type}`.
- Only **allow-listed, in-scope** relations may be included; each is subject to the same authorization as a direct fetch.
- Includes MUST be bounded (no unbounded relation expansion; e.g., `include=scorecards` on a competition is disallowed — too large).
- Depth is limited to **one level** by default; nested includes (`a.b`) require explicit allow-listing.
- Includes MUST NOT re-expose identity that a direct fetch would hide (e.g., a jury-scoped `performance` include never yields participant identity).

---

## 14. Searching

```
GET /api/v1/competitions?q=рисунок&sort=-openDate
```

- Free-text search uses the reserved parameter **`q`**.
- Search is **scoped** to fields the caller may see, and to the caller's authorization scope.
- Search endpoints MUST paginate (cursor, §9) and MAY rank by relevance (documented).
- Search MUST NOT enable enumeration of minors or cross-tenant data; participant search is limited to a guardian's/teacher's own scope.
- Complex/aggregated search over analytics is served by the read-model/report resources (`/reports`), not by overloading `q`.

---

## 15. Bulk Operations

Bulk endpoints support institutional scale ([BG-5](../architecture/ARCH-001-vt-platform-architecture.md#2-business-goals)) — e.g., bulk participant onboarding.

- Bulk create/update uses a dedicated collection action with an array payload:

```
POST /api/v1/participants/batch
{ "operations": [ { "op": "create", "data": { … } }, … ] }
```

- Bulk requests MUST be **bounded** (documented max items per request, e.g., 500).
- Large bulk jobs are processed **asynchronously**: respond **202 Accepted** with a job/status resource to poll ([ARCH-001 §7.5](../architecture/ARCH-001-vt-platform-architecture.md#7-backend-architecture)).
- Bulk responses report **per-item outcomes** (success/failure with Problem Details per item); partial success is reported, not hidden.
- Bulk operations MUST support `Idempotency-Key` (§19) so a retried batch is not duplicated.
- Every item is independently authorized and rule-checked; one item's failure MUST NOT silently apply or skip others.

---

## 16. File Upload

Media (participant works) is central and can be large ([ARCH-001 §9.6, §22.3](../architecture/ARCH-001-vt-platform-architecture.md#9-database-architecture)).

### 16.1 Large File Strategy — Direct-to-Storage (default)

Per [ADR-0012](../architecture/ARCH-001-vt-platform-architecture.md#30-architecture-decision-records-adr), the API does **not** proxy large media. The flow is:

1. **Request an upload target:** `POST /api/v1/performances/{id}/media-assets` returns a **pre-signed, short-TTL upload URL** and an asset id.
2. **Client uploads bytes directly** to object storage (S3) using the pre-signed URL.
3. **Client confirms:** `POST /api/v1/performances/{id}/media-assets/{assetId}/confirmation` → the platform records the asset and triggers async scan/moderation (produces `PerformanceUploaded` → `MediaScanCompleted`, [DATA-003](../business/DATA-003-domain-event-catalog.md#46-performances-prf)).

- The API stores only **references + metadata** (key, checksum, MIME, size), never bytes ([ARCH-001 §9.6](../architecture/ARCH-001-vt-platform-architecture.md#9-database-architecture)).
- Media is served via **signed, short-TTL URLs**; no public buckets ([ARCH-001 §21.2](../architecture/ARCH-001-vt-platform-architecture.md#21-security)).

### 16.2 Multipart Rules (small files only)

- Small files (e.g., profile images, documents under a documented threshold) MAY use `multipart/form-data` directly to the API.
- Uploads MUST validate **MIME type, size, and the nomination's media requirements** ([PRF-003](../business/DATA-002-business-rules-catalog.md#rule-prf-003)); non-conforming uploads → **422**.
- All uploaded media undergoes **antivirus scanning** and moderation **before** it is available or judged ([PRF-001](../business/DATA-002-business-rules-catalog.md#rule-prf-001), [PRF-002](../business/DATA-002-business-rules-catalog.md#rule-prf-002)); infected assets are quarantined and never served.

---

## 17. Authentication

Per [ARCH-001 §11](../architecture/ARCH-001-vt-platform-architecture.md#11-authentication):

### 17.1 JWT Bearer

- Requests authenticate with a **short-lived JWT access token** in `Authorization: Bearer <token>` (TTL ≈ 15 minutes).
- Missing/invalid/expired token → **401** with a Problem Details document.
- Access tokens are **opaque to clients** in meaning; clients MUST NOT parse claims for authorization decisions (the server is authoritative).

### 17.2 Refresh Tokens

- A **rotating refresh token** (TTL in days) is exchanged for a new access token at `POST /api/v1/auth/token/refresh`.
- For the **web client**, the refresh token is stored in an **httpOnly, Secure, SameSite** cookie (not readable by JS).
- Refresh rotation with **reuse detection**: a replayed refresh token invalidates the whole token family (theft mitigation).
- Logout (`POST /api/v1/auth/logout`) revokes the session/refresh family immediately.

### 17.3 MFA & Step-Up

- Privileged roles (Administrator, Organizer, Jury) MUST have MFA ([IDN-002](../business/DATA-002-business-rules-catalog.md#rule-idn-002)); endpoints exercising those roles require an MFA-satisfied token.
- **Step-up** authentication is required for high-risk operations (publishing results, erasing data); such endpoints return **401**/`insufficient_authentication` until step-up is satisfied.

### 17.4 Public Endpoints

- A small allow-list is public (e.g., published competition listings, diploma verification by code). These MUST still enforce privacy rules (no minor PII) and rate limiting.

---

## 18. Authorization

Authorization is **RBAC + scope/tenancy**, re-checked at the application layer ([ARCH-001 §12](../architecture/ARCH-001-vt-platform-architecture.md#12-authorization-rbac); [DATA-002](../business/DATA-002-business-rules-catalog.md) security rules).

- **Deny by default.** Absence of a grant is a denial.
- **Least privilege.** Roles: Participant, Guardian, Teacher, Institution Admin, Jury, Organizer, Administrator ([ARCH-001 §12.2](../architecture/ARCH-001-vt-platform-architecture.md#12-authorization-rbac)).
- **Object-level + scope checks.** Every request is filtered by the caller's scope: guardians see only their linked participants ([PRT-003](../business/DATA-002-business-rules-catalog.md#rule-prt-003)); teachers only their institution/classes ([PRT-004](../business/DATA-002-business-rules-catalog.md#rule-prt-004)); jury only assigned performances ([JDG-002](../business/DATA-002-business-rules-catalog.md#rule-jdg-002)); institutions are tenancy boundaries ([INS-002](../business/DATA-002-business-rules-catalog.md#rule-ins-002)).
- **Row-level scoping.** Out-of-scope resources are **not enumerable**; list/search never returns them, and direct fetch returns **404** (not 403) where existence is sensitive (§26).
- **Fairness/privacy enforcement.** Jury responses are **pseudonymized** ([JDG-006](../business/DATA-002-business-rules-catalog.md#rule-jdg-006)); scores are not visible before results are published ([RES-006](../business/DATA-002-business-rules-catalog.md#rule-res-006)).
- **Auditable.** Authorization decisions on sensitive resources are audited ([AUD-001](../business/DATA-002-business-rules-catalog.md#rule-aud-001)).

---

## 19. Idempotency

### 19.1 POST Rules

- Any **non-idempotent** operation a client might retry (resource creation, order/payment, bulk submit) MUST accept an **`Idempotency-Key`** header (a client-generated UUID, §23).
- The server stores the first response for a given `(key, endpoint, actor)` for a documented window (e.g., 24h). A repeat with the **same key** returns the **same result** without re-executing the side effect.
- A repeat with the same key but a **different body** → **409** (`idempotency-key-reuse`).
- Idempotency keys are REQUIRED for: `POST /applications`, `POST /orders`, `POST /payments`, `POST /performances/{id}/media-assets/.../confirmation`, and all `…/batch` endpoints.

### 19.2 Retry Strategy

- Clients SHOULD retry on **429** (respect `Retry-After`), **502/503/504**, and network timeouts, using **exponential backoff with jitter**.
- Clients MUST reuse the **same `Idempotency-Key`** across retries of the same logical operation.
- Clients MUST NOT retry **4xx** (except 429) — those are client errors that will not succeed on retry.
- GET/PUT/DELETE are idempotent by definition and are safely retryable without a key.

---

## 20. Rate Limiting

Per [ARCH-001 §10.4, §21.3](../architecture/ARCH-001-vt-platform-architecture.md#10-api-architecture):

- Limits apply **per authenticated user** and **per IP** (Redis-backed), with tighter limits on auth and submission endpoints.
- Exceeding a limit → **429** with a Problem Details body and headers:
  - `Retry-After: <seconds>`
  - `RateLimit-Limit`, `RateLimit-Remaining`, `RateLimit-Reset` (per the IETF RateLimit header conventions).
- Limits are **higher for verified institutions** (bulk workflows) and **lower for public/unauthenticated** endpoints.
- Deadline-spike tolerance: submission endpoints are capacity-planned for bursts ([ARCH-001 §3.2, §22.4](../architecture/ARCH-001-vt-platform-architecture.md#3-non-functional-requirements)); limits protect fairness and stability without blocking legitimate last-minute submissions.

---

## 21. Caching & Concurrency

### 21.1 ETag

- Mutable single resources MUST return an **`ETag`** (entity version) on GET.
- Conditional reads use **`If-None-Match`** → **304 Not Modified** when unchanged.
- **Optimistic concurrency** on mutations uses **`If-Match: <etag>`** ([ARCH-001 §10.3](../architecture/ARCH-001-vt-platform-architecture.md#10-api-architecture)):
  - Missing `If-Match` on a concurrency-sensitive mutation → **428 Precondition Required** (or documented **409**).
  - Stale `If-Match` (resource changed) → **412 Precondition Failed** (a concurrency conflict; conceptually a **409** family). Client refetches and retries.

### 21.2 Cache-Control

- Responses set **`Cache-Control`** appropriate to sensitivity:
  - Reference/public data (e.g., published competition metadata): `public, max-age=<short>`.
  - Personalized/authorized data: `private, no-store` or short `private, max-age` with revalidation.
  - **Minor PII and jury-scoped data: `no-store`.**
- Cache invalidation is **event-driven** ([ARCH-001 §22.2](../architecture/ARCH-001-vt-platform-architecture.md#22-performance)); clients MUST revalidate via ETag rather than assume freshness.

---

## 22. Time Format

- All timestamps are **ISO-8601 in UTC** with a trailing `Z`: `2026-07-05T09:12:00Z`.
- The API neither accepts nor returns local-time-without-offset. Clients localize for display.
- Durations use ISO-8601 duration format where needed (`P1D`, `PT15M`).
- Date-only business values (e.g., date of birth for age-group derivation, [PRT-002](../business/DATA-002-business-rules-catalog.md#rule-prt-002)) use `YYYY-MM-DD`.
- Field naming: instants end in `At` (`createdAt`, `submittedAt`, `publishedAt`); windows use `…OpenAt`/`…CloseAt`.

---

## 23. UUID Policy

- **All externally visible resource identifiers are UUIDs**, and specifically **UUID v7** (time-ordered) for new identifiers.
- **Rationale:** UUID v7 is globally unique, non-enumerable (protecting minors from scraping — [PRT-006](../business/DATA-002-business-rules-catalog.md#rule-prt-006)), and time-ordered, which improves index locality at scale. This **refines** the "UUID primary keys for externally referenced entities" decision in [ARCH-001 §9.4](../architecture/ARCH-001-vt-platform-architecture.md#9-database-architecture) and the identity strategy in [DATA-001 §9](../business/DATA-001-business-data-model.md#9-entity-identity-strategy).
- Ids appear in URLs, `data.id`, and references. Clients MUST treat them as **opaque** strings and MUST NOT infer structure or ordering.
- Sequential/guessable integer ids MUST NOT be exposed externally.
- Human-facing reference numbers (invoice number, diploma verification code) are **separate** business artifacts, distinct from resource identity ([DATA-001 §9.4](../business/DATA-001-business-data-model.md#9-entity-identity-strategy)).
- `Idempotency-Key` and `X-Request-ID` are client-generated UUIDs (v4 acceptable for these ephemeral values).

---

## 24. API Lifecycle

Every endpoint/resource has a documented lifecycle stage, surfaced in OpenAPI and headers.

| Stage | Meaning | Guarantees |
|-------|---------|-----------|
| **Experimental** | Preview; may change without a major bump | MUST be marked `x-lifecycle: experimental` and MAY change or be removed with notice. Not for critical integrations. |
| **Stable** | Production-ready | Backward-compatible within the major version (§2); breaking change requires a new major version. |
| **Deprecated** | Scheduled for removal | MUST emit `Deprecation: true` and a `Sunset: <date>` header; documented replacement; minimum **6-month** window ([§2.4](#2-versioning)). |
| **Removed** | No longer served | Returns **410 Gone** for a grace period, then **404**. |

Rules:
- Promotion Experimental → Stable and any Stable → Deprecated transition is announced in the changelog and (for cross-cutting cases) an ADR.
- Deprecated endpoints keep working unchanged until Sunset; they MUST NOT silently degrade.

---

## 25. OpenAPI Conventions

The contract is **OpenAPI 3.1** (drf-spectacular, [ARCH-001 §6.1, §10.1](../architecture/ARCH-001-vt-platform-architecture.md#6-technology-stack)). This standard governs how it is written; the contract itself is a separate deliverable (API-001+, not this document).

- **Naming (schemas):** PascalCase, singular, matching [DATA-001](../business/DATA-001-business-data-model.md) entity names — `Participant`, `Application`, `Scorecard`, `Result`. Request/response variants use suffixes: `ParticipantCreateRequest`, `ParticipantResponse`, `PageOfApplications`, `ProblemDetails`.
- **Tags:** one tag per **domain/bounded context** ([DATA-001 §3](../business/DATA-001-business-data-model.md#3-domain-overview)): `Identity`, `Participants`, `Institutions`, `Competitions`, `Applications`, `Performances`, `Judging`, `Results`, `Finance`, `Notifications`, `Analytics`, `Audit`. Every operation MUST carry exactly one primary domain tag.
- **Operation IDs:** `camelCase`, `verbResource` form, stable and unique — `listApplications`, `getApplication`, `createApplication`, `submitApplication` (for the `publication`/transition sub-resources, `publishCompetitionResults`). Operation IDs are the contract for generated client method names and MUST NOT change within a major version.
- **Schemas:** every field documented with type, format, and constraints; timestamps `format: date-time`; ids `format: uuid`; money as the Money object; enums enumerate the documented state values from [DATA-004](../business/DATA-004-state-machine-catalog.md).
- **Examples:** every operation MUST include at least one request and one response **example**, plus at least one **error example** (Problem Details). Examples MUST use pseudonymized, non-real data (no real minor PII, [§28.5 of ARCH-001 testing](../architecture/ARCH-001-vt-platform-architecture.md#28-testing-strategy)).
- **Errors:** all operations reference the shared `ProblemDetails` schema and enumerate the status codes they can return (§5).
- **Security:** operations declare their security scheme (bearer JWT) and required role/scope in the description.

---

## 26. Security Guidelines

Grounded in [ARCH-001 §21](../architecture/ARCH-001-vt-platform-architecture.md#21-security) (Security & Privacy by Design):

- **Transport:** TLS 1.2+ only; HSTS. No plaintext.
- **AuthN/AuthZ everywhere:** deny by default; re-check authorization in the application layer, never trust the client (§18).
- **Least data:** responses expose only what the caller is authorized to see; minor PII is minimized and never returned to jury or public consumers ([JDG-006](../business/DATA-002-business-rules-catalog.md#rule-jdg-006), [PRT-006](../business/DATA-002-business-rules-catalog.md#rule-prt-006)).
- **Existence hiding:** prefer **404** over **403** where confirming existence would leak information about minors or other tenants.
- **Input validation:** strict validation at the edge (§6) plus domain invariants; reject unknown fields on writes.
- **Injection-safe:** all inputs parameterized/validated; no reflection of raw input into errors.
- **Rate limiting & bot mitigation** on auth and submission endpoints (§20).
- **No secrets in URLs:** tokens/keys go in headers, never query strings (query strings are logged).
- **Media safety:** signed short-TTL URLs; antivirus + moderation before exposure (§16).
- **Idempotency & concurrency:** protect against double-charge (§19) and lost updates (§21).
- **Audit:** sensitive operations (consent, scoring, result publication, payments, data-subject operations) are audited with correlation ids ([AUD-001](../business/DATA-002-business-rules-catalog.md#rule-aud-001)).
- **CORS:** locked to known origins ([ARCH-001 §10.4](../architecture/ARCH-001-vt-platform-architecture.md#10-api-architecture)).
- **Error hygiene:** Problem Details never leak stack traces, internal ids, or PII.

---

## 27. API Design Checklist

**Every future endpoint MUST satisfy every item below before it ships.** A PR adding/altering an endpoint MUST link this checklist.

**Design & naming**
- [ ] Mounted under a version segment `/api/v{n}/` (§2).
- [ ] Resource is a **plural noun**, lowercase, kebab-case; **no verbs** in the URL (the only exception: a noun controller sub-resource for a transition, §3.3).
- [ ] Resource and fields match [DATA-001](../business/DATA-001-business-data-model.md)/[DIA-001](../diagrams/DIA-001-entity-relationship-model.md) names; no synonyms invented.

**Methods & status**
- [ ] Correct HTTP method with correct safety/idempotency semantics (§4).
- [ ] Returns only sanctioned status codes with correct 400/422/409/403/404 discipline (§5).
- [ ] Async work returns **202** with a status resource (§5, §15).

**Contracts**
- [ ] Success uses the standard `data`/`meta`/`links` envelope (§7).
- [ ] Errors use RFC 9457 Problem Details with `code` = DATA-002 rule id / IVT id where applicable (§8).
- [ ] Timestamps ISO-8601 UTC; money as Money object; ids UUID v7 (§22, §23, §7.4).

**Collections**
- [ ] Cursor pagination by default (offset only if justified) (§9).
- [ ] Filtering/sorting/sparse-fields/include are allow-listed and scope-enforced (§10–§13).
- [ ] Deterministic default sort defined for stable pagination (§11).

**Security & privacy**
- [ ] AuthN (JWT) and RBAC + scope enforced; row-level scoping applied (§17, §18).
- [ ] MFA/step-up required where the role/operation demands it (§17.3).
- [ ] No minor PII leakage; jury views pseudonymized; scores hidden pre-publication ([JDG-006](../business/DATA-002-business-rules-catalog.md#rule-jdg-006), [RES-006](../business/DATA-002-business-rules-catalog.md#rule-res-006)).
- [ ] Existence-sensitive resources return 404 (not 403) out of scope (§26).

**Behavior & integrity**
- [ ] State transitions honor [DATA-004](../business/DATA-004-state-machine-catalog.md); invalid transitions → 409 with IVT code (§5, §8).
- [ ] Business rules ([DATA-002](../business/DATA-002-business-rules-catalog.md)) enforced; violations → 422 with rule id (§8).
- [ ] Idempotency-Key required and honored for creates/charges/batches (§19).
- [ ] Optimistic concurrency via ETag/If-Match where mutable (§21).
- [ ] Emits the correct domain event(s) ([DATA-003](../business/DATA-003-domain-event-catalog.md)) on state change.

**Operability**
- [ ] Rate limits defined; 429 with `Retry-After` (§20).
- [ ] Cache-Control/ETag set per sensitivity; minor PII `no-store` (§21).
- [ ] Correlation id (`X-Request-ID`) accepted and echoed; sensitive ops audited (§6, §26).

**Documentation**
- [ ] OpenAPI: one domain tag, stable `operationId`, documented schemas, ≥1 request/response/error example (§25).
- [ ] Lifecycle stage marked; deprecations carry `Deprecation`/`Sunset` (§24).

---

*End of document — API-000 REST API Standards v1.0. Normative for all VT Platform endpoints. Refines [ARCH-001 §10–§12](../architecture/ARCH-001-vt-platform-architecture.md#10-api-architecture); exposes [DATA-001](../business/DATA-001-business-data-model.md)–[DATA-004](../business/DATA-004-state-machine-catalog.md) and [DIA-001](../diagrams/DIA-001-entity-relationship-model.md) as resources. Contains no endpoint implementations, no OpenAPI contract, and no Django code.*
