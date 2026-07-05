# VT Platform Architecture v1.0

**Project:** «Взлёт талантов» — цифровая экосистема для организации детских творческих конкурсов
**Document type:** Principal Technical Architecture Document
**Status:** Approved baseline (v1.0)
**Owner:** Platform Architecture Group
**Last updated:** 2026-07-05

---

## Table of Contents

1. [Vision](#1-vision)
2. [Business Goals](#2-business-goals)
3. [Non-Functional Requirements](#3-non-functional-requirements)
4. [Architecture Principles](#4-architecture-principles)
5. [High-Level Architecture](#5-high-level-architecture)
6. [Technology Stack](#6-technology-stack)
7. [Backend Architecture](#7-backend-architecture)
8. [Frontend Architecture](#8-frontend-architecture)
9. [Database Architecture](#9-database-architecture)
10. [API Architecture](#10-api-architecture)
11. [Authentication](#11-authentication)
12. [Authorization (RBAC)](#12-authorization-rbac)
13. [Domain-Driven Design](#13-domain-driven-design)
14. [Django Apps Structure](#14-django-apps-structure)
15. [React Project Structure](#15-react-project-structure)
16. [Infrastructure](#16-infrastructure)
17. [Docker Architecture](#17-docker-architecture)
18. [CI/CD](#18-cicd)
19. [Logging](#19-logging)
20. [Monitoring](#20-monitoring)
21. [Security](#21-security)
22. [Performance](#22-performance)
23. [Scalability](#23-scalability)
24. [Backup Strategy](#24-backup-strategy)
25. [Disaster Recovery](#25-disaster-recovery)
26. [Coding Standards](#26-coding-standards)
27. [Git Strategy](#27-git-strategy)
28. [Testing Strategy](#28-testing-strategy)
29. [Deployment Strategy](#29-deployment-strategy)
30. [Architecture Decision Records (ADR)](#30-architecture-decision-records-adr)
31. [Future Evolution](#31-future-evolution)

---

## 1. Vision

### 1.1 Purpose

«Взлёт талантов» (hereafter **VT Platform**) is a digital ecosystem for organizing, running, and judging children's creative competitions. The platform connects children, their parents, teachers, educational institutions, jury members, organizers, and administrators around a single, trustworthy, and delightful experience for discovering and celebrating young talent.

### 1.2 Problem Statement

Children's creative competitions today are fragmented across spreadsheets, messengers, email threads, and ad-hoc websites. This creates friction and risk:

- Manual, error-prone registration and submission collection.
- No standardized, fair, or auditable judging process.
- Weak protection of minors' personal data.
- No single source of truth for results, certificates, and analytics.
- Poor experience on mobile devices, where most parents actually operate.

### 1.3 Product Vision Statement

> Build the most trusted platform in the region for children's creative competitions — one where a parent can register a child in three minutes, a teacher can manage a whole class, a jury can score fairly and transparently, and an organizer can run a nationwide competition with confidence in data privacy, fairness, and scale.

### 1.4 Target Scale

- Initial launch: thousands of users, dozens of competitions.
- Growth horizon (24–36 months): **tens of thousands of concurrent users**, hundreds of competitions per season, millions of stored creative works (images, audio, video, documents).

### 1.5 Guiding Tenets

- **Trust first.** We handle children's data. Privacy and fairness are non-negotiable product features, not compliance afterthoughts.
- **Mobile is primary.** The majority of parents and teachers interact via phones.
- **Fairness is auditable.** Every scoring action is traceable and defensible.
- **Boring, proven technology.** We optimize for maintainability and predictability over novelty.

---

## 2. Business Goals

| # | Goal | Success Metric (KPI) |
|---|------|----------------------|
| BG-1 | Reduce time-to-register a participant | < 3 minutes median, > 95% completion rate |
| BG-2 | Increase organizer efficiency | One organizer manages ≥ 10 competitions/season |
| BG-3 | Ensure fair, transparent judging | 100% of scores auditable; dispute rate < 1% |
| BG-4 | Protect minors' data | Zero reportable data-privacy incidents |
| BG-5 | Enable institutional adoption | Onboard educational institutions with bulk workflows |
| BG-6 | Monetize sustainably | Support paid competitions, tiered plans, certificates |
| BG-7 | Achieve platform reliability | 99.9% availability of core flows |
| BG-8 | Scale economically | Linear cost growth vs. super-linear user growth |

### 2.1 Business Capabilities

- Competition lifecycle management (draft → open → submission → judging → results → archive).
- Participant & guardian management with verified consent.
- Institution and class/group management with delegated administration.
- Submission intake with large-media handling.
- Multi-round, multi-criteria, weighted judging.
- Results publication, ranking, certificates, and diplomas.
- Notifications across email and in-app (SMS/push as future channels).
- Analytics and reporting for organizers and institutions.
- Billing and payments for paid competitions (phased).

### 2.2 Actors and Primary Value

| Actor | Primary Value |
|-------|---------------|
| Participant (child) | Showcase work, receive recognition |
| Parent / Guardian | Register child, give consent, track progress |
| Teacher | Manage class submissions, mentor participants |
| Educational Institution | Delegate management, view institutional analytics |
| Jury | Score submissions fairly and efficiently |
| Organizer | Configure and run competitions end-to-end |
| Administrator | Operate, moderate, and govern the platform |

---

## 3. Non-Functional Requirements

### 3.1 NFR Catalogue

| ID | Category | Requirement | Target |
|----|----------|-------------|--------|
| NFR-01 | Availability | Core flows uptime | 99.9% monthly |
| NFR-02 | Performance | API p95 latency (read) | < 300 ms |
| NFR-03 | Performance | API p95 latency (write) | < 600 ms |
| NFR-04 | Performance | Web LCP (mobile, p75) | < 2.5 s |
| NFR-05 | Scalability | Concurrent active users | 30,000+ |
| NFR-06 | Scalability | Peak submissions burst | 5,000 submissions/hour |
| NFR-07 | Durability | Media object durability | 99.999999999% (S3-class) |
| NFR-08 | Security | Data encryption | TLS 1.2+ in transit, AES-256 at rest |
| NFR-09 | Privacy | Minor data minimization | Enforced by design (see §21) |
| NFR-10 | Recoverability | RPO | ≤ 15 minutes |
| NFR-11 | Recoverability | RTO | ≤ 2 hours |
| NFR-12 | Maintainability | Test coverage (backend domain) | ≥ 85% |
| NFR-13 | Observability | Trace coverage of critical paths | 100% |
| NFR-14 | Accessibility | WCAG level | 2.1 AA |
| NFR-15 | Localization | Primary locale | ru-RU; i18n-ready |
| NFR-16 | Compliance | Personal-data regulation | 152-ФЗ (RF PD Law) aligned |
| NFR-17 | Portability | Environment parity | Docker-based dev/stage/prod parity |

### 3.2 Quality Attribute Scenarios (samples)

- **Load spike (submission deadline):** When a submission deadline approaches and traffic increases 10×, the system must accept submissions with p95 < 1 s by autoscaling stateless workers and offloading media directly to S3.
- **Judging integrity:** When a jury member submits a score, the action is recorded immutably in an audit log within the same transaction boundary as the score write.
- **Data subject request:** When a guardian requests deletion of a child's data, the system must fulfill it within regulatory timelines, cascading through media storage and backups per the retention policy.

---

## 4. Architecture Principles

These principles are binding. Deviations require a recorded ADR (see §30).

### 4.1 Clean Architecture
Dependencies point inward. The **domain** (entities, business rules) knows nothing about Django, DRF, PostgreSQL, or HTTP. Frameworks are details at the edges. This enables testability and long-term replaceability of infrastructure.

### 4.2 SOLID
- **S**ingle Responsibility: each module/service has one reason to change.
- **O**pen/Closed: extend via new strategies/policies, not by editing core rules.
- **L**iskov Substitution: repository and gateway interfaces are honestly substitutable.
- **I**nterface Segregation: narrow, role-specific ports over fat interfaces.
- **D**ependency Inversion: application layer depends on abstractions; concrete adapters are injected.

### 4.3 Domain-Driven Design
The system is decomposed into **bounded contexts** with a shared **ubiquitous language**. See §13.

### 4.4 API First
Every capability is exposed through a versioned, contract-first API (OpenAPI). The web frontend is just one consumer; mobile and integrations are first-class future consumers.

### 4.5 Mobile First
UI is designed for the smallest viewport first, then progressively enhanced. Performance budgets assume mid-range mobile devices on constrained networks.

### 4.6 Security by Design
Threat modeling, least privilege, secure defaults, and defense in depth are built into every layer from day one (see §21).

### 4.7 Privacy by Design
Data minimization, purpose limitation, consent tracking, and minor-data protection are structural, not bolt-on (see §21.6).

### 4.8 Event-Driven
State changes emit **domain events** (e.g., `SubmissionAccepted`, `ScoringCompleted`). Cross-context reactions (notifications, analytics, certificate generation) are handled asynchronously via an event bus backed by Redis/Celery.

### 4.9 Modular Monolith
We start as a **single deployable Django application** internally partitioned into strict modules (bounded contexts) with explicit interfaces and no cross-module ORM reach-in. This gives us DDD boundaries and future extractability **without** premature microservice operational overhead.

---

## 5. High-Level Architecture

### 5.1 System Context (C4 — Level 1)

```
                         ┌─────────────────────────────┐
   Parents / Teachers    │                             │   Email / S3 / Payments
   Jury / Organizers ───▶│        VT Platform          │◀──▶  (external systems)
   Administrators        │  (Modular Monolith + SPA)   │
                         │                             │
                         └─────────────────────────────┘
```

### 5.2 Container View (C4 — Level 2)

```
┌────────────┐     HTTPS      ┌──────────────────────────────────────────┐
│  Browser   │◀──────────────▶│                 Nginx                      │
│ React SPA  │                │  (TLS, reverse proxy, static, rate limit)  │
└────────────┘                └───────┬───────────────────────┬───────────┘
                                       │ /api                  │ /static, /media (signed)
                                       ▼                       ▼
                          ┌────────────────────────┐   ┌──────────────────┐
                          │  Django 6 + DRF (ASGI)  │   │   S3 Object Store │
                          │  Gunicorn/Uvicorn       │   │  (media, exports) │
                          │  Modular Monolith        │   └──────────────────┘
                          └───┬──────────┬──────────┘
                              │          │ enqueue
                    read/write│          ▼
                              │   ┌───────────────┐        ┌───────────────┐
                              │   │     Redis     │◀──────▶│ Celery Workers │
                              │   │ cache/broker  │        │  + Beat        │
                              │   └───────────────┘        └───────────────┘
                              ▼
                     ┌────────────────┐
                     │  PostgreSQL     │
                     │ (primary+replica)│
                     └────────────────┘
```

### 5.3 Logical Layering (per module)

```
┌───────────────────────────────────────────────┐
│  Interface / Presentation                       │  DRF views, serializers, URL routing
├───────────────────────────────────────────────┤
│  Application (Use Cases / Services)             │  orchestrates, transactions, events
├───────────────────────────────────────────────┤
│  Domain (Entities, Value Objects, Rules)        │  framework-free business logic
├───────────────────────────────────────────────┤
│  Infrastructure (Adapters)                      │  ORM repos, S3, email, Celery gateways
└───────────────────────────────────────────────┘
```

### 5.4 Key Flows

- **Synchronous request path:** Browser → Nginx → DRF view → application service → domain → repository → PostgreSQL → response.
- **Media upload path:** Browser requests a **pre-signed S3 URL** from the API → uploads directly to S3 → notifies API → domain event `SubmissionMediaAttached`.
- **Asynchronous path:** Application service emits domain event → published to Redis → Celery worker consumes → side effects (notifications, thumbnails, certificate PDF, analytics projection).

---

## 6. Technology Stack

### 6.1 Backend
| Concern | Choice | Rationale |
|---------|--------|-----------|
| Language | Python 3.13+ | Ecosystem, hiring, Django alignment |
| Web framework | **Django 6** | Batteries-included, ORM, admin, maturity |
| API framework | **Django REST Framework** | Serialization, viewsets, auth integration |
| Async serving | ASGI (Uvicorn workers under Gunicorn) | WebSocket/async readiness |
| Task queue | **Celery** | Mature distributed task processing |
| Broker/cache | **Redis** | Broker, cache, rate limiting, locks |
| API schema | drf-spectacular (OpenAPI 3.1) | Contract-first, generated clients |

### 6.2 Frontend
| Concern | Choice |
|---------|--------|
| UI library | **React 19** |
| Language | **TypeScript (strict)** |
| Build tool | **Vite** |
| Styling | **Tailwind CSS** |
| Component system | **shadcn/ui** (Radix primitives) |
| Server state | **TanStack Query** |
| Client state | Zustand (lightweight, local UI state) |
| Forms/validation | React Hook Form + Zod |
| Routing | React Router |
| Testing | Vitest + React Testing Library + Playwright (E2E) |

### 6.3 Data & Infrastructure
| Concern | Choice |
|---------|--------|
| Primary DB | **PostgreSQL 16+** (primary + read replica) |
| Cache / broker | **Redis 7+** |
| Object storage | **S3-compatible** (media, exports, backups) |
| Reverse proxy | **Nginx** |
| Containerization | **Docker** + Docker Compose (dev), orchestrator (prod) |
| CI/CD | **GitHub Actions** |
| Observability | OpenTelemetry, Prometheus, Grafana, Loki, Sentry |

### 6.4 Stack Selection Rationale
The stack is deliberately **proven and cohesive**: Django 6 + DRF gives a productive, secure default; PostgreSQL + Redis + Celery + S3 is a battle-tested backbone for media-heavy, event-driven workloads; React 19 + Vite + Tailwind + shadcn/ui is a modern, mobile-first frontend baseline. No component here is exotic, which directly serves maintainability and hiring at enterprise scale.

---

## 7. Backend Architecture

### 7.1 Overview
The backend is a **modular monolith** built on Django 6. Each bounded context is a Python package (a "module") with a strict internal layering (interface → application → domain → infrastructure). Modules communicate through **published application interfaces and domain events**, never by reaching into another module's ORM models directly.

### 7.2 Layered Responsibilities

- **Interface layer (DRF):** HTTP concerns only — routing, request parsing, DRF serializers, authentication/permission wiring, pagination, throttling. No business logic.
- **Application layer (use cases / services):** Orchestrates a single business operation, owns the transaction boundary, invokes domain logic, calls repositories/gateways via interfaces, and publishes domain events.
- **Domain layer:** Pure Python. Entities, value objects, aggregates, domain services, invariants, and domain events. No Django imports.
- **Infrastructure layer (adapters):** ORM-backed repository implementations, S3 gateway, email gateway, Celery task adapters, external API clients.

### 7.3 Dependency Rule
Inner layers must not import outer layers. The application layer depends on **ports** (abstract interfaces); concrete **adapters** are wired at composition time (Django app config / a lightweight DI container / factory functions). This keeps domain and application logic unit-testable without a database.

### 7.4 Transaction & Consistency Strategy
- One use case = one transaction (`atomic` boundary in the application layer).
- **Strong consistency within a bounded context** (single DB, ACID).
- **Eventual consistency across contexts** via domain events → outbox → Celery.
- **Transactional outbox pattern:** domain events are persisted in the same transaction as state changes, then relayed to Redis by a dispatcher, guaranteeing at-least-once delivery without dual-write inconsistency.

### 7.5 Asynchronous Processing
Celery handles: media post-processing (thumbnails, transcoding, virus scan), certificate/diploma PDF generation, bulk imports/exports, email/notification fan-out, scheduled tasks (Celery Beat) such as deadline transitions and reminder digests, and analytics projections.

### 7.6 Error Handling
- Domain raises typed domain exceptions; application maps them to result objects.
- Interface layer maps results to RFC 9457 (Problem Details) JSON responses.
- Idempotency keys on unsafe operations exposed to clients (e.g., submission create).

---

## 8. Frontend Architecture

### 8.1 Approach
A **mobile-first Single Page Application** (React 19 + TypeScript + Vite). It consumes the versioned REST API and is one of several possible API consumers (API First).

### 8.2 State Management
- **Server state:** TanStack Query is the single source of truth for server data — caching, background refetch, optimistic updates, pagination, and request deduplication. No server data is duplicated into a global client store.
- **Client/UI state:** Zustand for ephemeral UI state (modals, wizards, filters).
- **Form state:** React Hook Form + Zod schemas; Zod schemas are shared conceptually with backend contracts.

### 8.3 Design System
- **Tailwind CSS** for utility-first styling with a shared design-token config (colors, spacing, typography, breakpoints).
- **shadcn/ui** components (owned in-repo, built on Radix) provide accessible primitives (dialogs, menus, forms). Accessibility (WCAG 2.1 AA) is a component-level acceptance criterion.

### 8.4 Rendering & Performance
- Route-based code splitting, lazy loading, and Suspense boundaries.
- Image optimization and responsive `srcset` for participant media (thumbnails served from S3/CDN).
- Performance budgets enforced in CI (bundle size, LCP proxy metrics).

### 8.5 API Layer
A typed API client is generated from the backend OpenAPI schema, ensuring the frontend and backend contracts never drift. All network calls go through TanStack Query hooks wrapping this client.

### 8.6 Internationalization
`ru-RU` primary; i18n framework in place from v1 so additional locales are additive. All user-facing strings are externalized.

---

## 9. Database Architecture

### 9.1 Engine & Topology
- **PostgreSQL** as the single system of record.
- **Primary** (read/write) + one or more **read replicas** (analytics, reporting, heavy reads).
- Connection pooling via **PgBouncer** (transaction pooling mode).

### 9.2 Schema Strategy — Schema-per-Context
Each bounded context owns its tables under a dedicated **PostgreSQL schema** (e.g., `competitions`, `participants`, `judging`, `identity`). This physically reinforces module boundaries: cross-schema foreign keys are avoided; cross-context references are held as **IDs**, resolved through the owning module's interface.

### 9.3 Key Data Domains (illustrative)
- **identity:** users, roles, credentials, consents, sessions.
- **participants:** participant profiles, guardians, institution memberships.
- **competitions:** competitions, categories, rounds, criteria, schedules.
- **submissions:** submissions, media references, metadata, status.
- **judging:** assignments, scores, comments, results, rankings.
- **notifications / audit / billing:** supporting contexts.

### 9.4 Data Design Rules
- UUID primary keys for externally referenced entities (avoids enumeration, aids sharding/merge).
- Soft-delete + audit columns (`created_at`, `updated_at`, `created_by`) as standard.
- JSONB for flexible-but-queryable attributes (e.g., dynamic competition criteria), with GIN indexes where filtered.
- Money as integer minor units; never floats.
- Enum-like statuses modeled as constrained text with check constraints and documented state machines.

### 9.5 Indexing & Query Health
- Every foreign-key column indexed.
- Composite/partial indexes designed from actual query patterns.
- Slow-query logging + `pg_stat_statements` reviewed regularly.
- Migrations are backward-compatible (expand/contract pattern) to enable zero-downtime deploys.

### 9.6 Large Media
Binary media is **never** stored in PostgreSQL. Only S3 object keys, checksums, MIME types, and metadata are stored. Actual bytes live in S3.

---

## 10. API Architecture

### 10.1 Style & Contract
- **RESTful JSON** over HTTPS, resource-oriented, contract-first via **OpenAPI 3.1** (drf-spectacular).
- API First: the schema is the source of truth; typed clients and mock servers are generated from it.

### 10.2 Versioning
- URI versioning: `/api/v1/...`.
- Additive changes are non-breaking; breaking changes bump the major version. Deprecation policy: minimum 6-month overlap with `Deprecation`/`Sunset` headers.

### 10.3 Conventions
- Resource naming: plural nouns (`/competitions`, `/submissions/{id}/scores`).
- Cursor-based pagination for large collections; page-based for small admin lists.
- Filtering, ordering, and sparse fieldsets via query parameters.
- Standard error format: **RFC 9457 Problem Details**.
- Idempotency: `Idempotency-Key` header for create/charge operations.
- Concurrency: optimistic locking via `ETag`/`If-Match` on mutable resources.

### 10.4 Cross-Cutting API Concerns
- **Rate limiting / throttling:** per-user and per-IP (DRF throttles + Nginx + Redis).
- **Pagination limits** and max page size enforced server-side.
- **CORS** locked to known origins.
- **Consistent envelope:** data, pagination metadata, and links where relevant.

### 10.5 Realtime (phased)
For live judging dashboards and result reveals, WebSocket/SSE endpoints (Django Channels over ASGI) are introduced in a later phase; v1 uses polling via TanStack Query where near-real-time suffices.

---

## 11. Authentication

### 11.1 Model
- **Token-based authentication using JWT** (short-lived access token + rotating refresh token).
- Access token TTL: ~15 minutes. Refresh token TTL: days, **rotated** on use, stored as an httpOnly, Secure, SameSite cookie for the web client.
- Refresh-token reuse detection invalidates the token family (theft mitigation).

### 11.2 Credential Handling
- Passwords hashed with Argon2 (Django password hashers configured accordingly).
- Password policy, lockout/backoff after repeated failures (Redis-backed), and breach-list checks.
- **Email verification** required before sensitive actions.

### 11.3 Multi-Factor & Elevated Roles
- MFA (TOTP) **required** for Administrators, Organizers, and Jury.
- Step-up authentication for high-risk operations (publishing results, deleting data).

### 11.4 Guardian & Minor Model
- Children (participants) generally **do not hold independent accounts**; they are managed under a verified **guardian** account, or an institution/teacher account with documented consent.
- Consent records are first-class, versioned, and auditable (Privacy by Design, §21.6).

### 11.5 External Identity (phased)
- Social/institutional SSO (OAuth2/OIDC) and Gosuslugi-style integration are future options, isolated behind an identity gateway so the core auth model is unaffected.

---

## 12. Authorization (RBAC)

### 12.1 Model
Authorization is **Role-Based Access Control**, refined with **scope/tenancy** and selective attribute checks (RBAC + light ABAC where context matters, e.g., "jury may score only submissions in competitions they are assigned to").

### 12.2 Roles

| Role | Core Permissions |
|------|------------------|
| Participant | View own profile/submissions/results |
| Parent/Guardian | Manage linked children, submit, give consent, view results |
| Teacher | Manage assigned class participants and submissions |
| Institution Admin | Delegate teacher roles, view institutional analytics |
| Jury | View assigned submissions, submit scores/comments |
| Organizer | Full lifecycle control of owned competitions |
| Administrator | Platform-wide governance, moderation, configuration |

### 12.3 Enforcement Layers
1. **API layer:** DRF permission classes gate endpoints by role + object-level checks.
2. **Application layer:** authorization policies re-checked at use-case entry (defense in depth; the domain never trusts the transport).
3. **Data layer:** row-level scoping (queryset filtering by tenant/assignment) so users cannot even enumerate out-of-scope objects.

### 12.4 Principles
- **Least privilege by default**; permissions are additive and explicit.
- **Deny by default**; absence of a grant is a denial.
- Permission checks are centralized in a policy module per context — not scattered across views.
- All authorization decisions on sensitive resources are auditable.

### 12.5 Scoping / Multi-Tenancy
Institutions form natural tenancy boundaries. Data access is filtered by institution membership and competition assignment, preventing cross-tenant leakage.

---

## 13. Domain-Driven Design

### 13.1 Ubiquitous Language (selected)
- **Competition:** a time-bounded event with categories, rounds, and criteria.
- **Category:** a class of works (e.g., "Рисунок 7–9 лет").
- **Round:** a judging stage (qualification, final).
- **Submission:** a participant's work entered into a category.
- **Criterion:** a weighted dimension of evaluation.
- **Score:** a jury member's evaluation of a submission against criteria.
- **Result:** aggregated, ranked outcome.
- **Consent:** a guardian's recorded authorization for a minor's participation and data use.

### 13.2 Bounded Contexts

| Context | Responsibility | Type |
|---------|----------------|------|
| **Identity & Access** | Accounts, auth, roles, consent | Supporting |
| **Participants** | Participant & guardian profiles, institution links | Core |
| **Competitions** | Competition/category/round/criteria configuration & lifecycle | **Core** |
| **Submissions** | Intake, media references, validation, state | **Core** |
| **Judging** | Assignments, scoring, aggregation, ranking, integrity | **Core** |
| **Notifications** | Multi-channel messaging | Supporting |
| **Billing** | Payments, plans, invoices (phased) | Supporting |
| **Analytics/Reporting** | Read models, dashboards | Generic |
| **Audit** | Immutable event trail | Supporting |

### 13.3 Context Mapping
- Judging is **downstream** of Submissions and Competitions (Customer/Supplier).
- Notifications, Analytics, and Audit are **event consumers** (Published Language via domain events).
- An **Anti-Corruption Layer** wraps external systems (payments, SSO) so their models never leak inward.

### 13.4 Tactical Patterns
- **Aggregates** with clear roots (e.g., `Submission` aggregate owns its media references and status transitions; `Competition` aggregate owns categories/rounds/criteria).
- **Value objects** for concepts like `ScoreValue`, `AgeGroup`, `Money`, `ConsentGrant`.
- **Domain events** as the integration currency between contexts.
- **Repositories** as the only gateway between aggregates and persistence.
- Invariants (e.g., "a submission cannot be scored before its round opens") live in the domain, not in views.

---

## 14. Django Apps Structure

Each bounded context maps to a Django app package with an explicit internal layering. Cross-app imports are limited to each app's **public interface** (`api.py` / `services`) and shared kernel.

```
backend/
├── config/                     # project settings (split by environment), ASGI/WSGI, root urls
│   ├── settings/
│   │   ├── base.py
│   │   ├── dev.py
│   │   ├── stage.py
│   │   └── prod.py
│   ├── asgi.py
│   └── urls.py
├── shared_kernel/              # cross-context value objects, base classes, event bus, result types
│   ├── domain/
│   ├── events/                 # event base + outbox + dispatcher
│   └── infrastructure/         # base repository, S3 gateway, email gateway
├── apps/
│   ├── identity/
│   │   ├── domain/             # entities, value objects, domain services (framework-free)
│   │   ├── application/        # use cases, ports (interfaces), event handlers
│   │   ├── infrastructure/     # ORM models, repositories, adapters
│   │   ├── interface/          # DRF serializers, views, urls, permissions
│   │   ├── migrations/
│   │   └── api.py              # public interface exposed to other apps
│   ├── participants/           # same internal structure
│   ├── competitions/
│   ├── submissions/
│   ├── judging/
│   ├── notifications/
│   ├── billing/
│   ├── analytics/
│   └── audit/
├── tasks/                      # Celery app, beat schedule, task registration
├── manage.py
└── pyproject.toml
```

**Rules**
- ORM models live only in `infrastructure/`; the domain layer imports nothing Django.
- No app imports another app's ORM models — only its `api.py`.
- Each app declares its DRF routes; `config/urls.py` mounts them under `/api/v1/`.
- Migrations are per-app; each app maps to its own PostgreSQL schema (§9.2).

---

## 15. React Project Structure

A **feature-based (feature-sliced)** structure keeps the SPA modular and mobile-first.

```
frontend/
├── public/
├── src/
│   ├── app/                    # app shell, providers (Query, Router, Theme), global styles
│   ├── shared/                 # design-system-agnostic reusables
│   │   ├── ui/                 # shadcn/ui components (owned in-repo)
│   │   ├── lib/                # utils, formatters, config
│   │   ├── api/                # generated OpenAPI client + query client setup
│   │   └── hooks/
│   ├── entities/               # domain models & their read/display components
│   │   ├── competition/
│   │   ├── submission/
│   │   ├── participant/
│   │   └── user/
│   ├── features/               # user-facing capabilities (verbs)
│   │   ├── auth/
│   │   ├── register-participant/
│   │   ├── submit-work/
│   │   ├── score-submission/
│   │   └── manage-competition/
│   ├── pages/                  # route-level composition
│   ├── widgets/                # composite blocks (dashboards, tables)
│   └── styles/                 # tailwind config, tokens
├── tests/                      # unit + integration (Vitest, RTL)
├── e2e/                        # Playwright
├── index.html
├── vite.config.ts
├── tailwind.config.ts
└── tsconfig.json
```

**Rules**
- Dependency direction: `pages → widgets → features → entities → shared` (never reversed).
- All server data access goes through `shared/api` + TanStack Query hooks colocated in `features`/`entities`.
- Components meet WCAG 2.1 AA and are mobile-first by default.

---

## 16. Infrastructure

### 16.1 Environments
- **dev** (local, Docker Compose), **stage** (production-like), **prod** — with configuration parity enforced by Docker images and 12-factor config (env vars/secrets).

### 16.2 Production Topology
```
Internet ──▶ CDN ──▶ Load Balancer (TLS termination)
                        │
                        ▼
                   Nginx (per node: proxy, static, security headers)
                        │
        ┌───────────────┼──────────────────┐
        ▼               ▼                   ▼
  Django API pods   Django API pods    Celery worker pods (+ Beat)
        │               │                   │
        └──────┬────────┴─────────┬─────────┘
               ▼                  ▼
        PgBouncer ──▶ PostgreSQL primary ──▶ read replica(s)
               │
               ▼
             Redis (broker + cache; HA)
               │
               ▼
           S3 object storage (media, exports, backups)
```

### 16.3 Configuration & Secrets
- 12-factor configuration via environment variables.
- Secrets managed by a dedicated secrets manager / Vault; never committed. Rotation policy defined per secret class.

### 16.4 Networking
- Private network for DB/Redis; only Nginx/LB exposed publicly.
- Security groups / network policies enforce least-privilege connectivity.

### 16.5 Orchestration
- v1 target: container orchestration (Kubernetes or a managed equivalent) for API and worker pods; managed PostgreSQL and Redis where available to reduce operational load.

---

## 17. Docker Architecture

### 17.1 Principles
- **Multi-stage builds** to keep runtime images small and free of build tooling.
- **One process type per container** (API, worker, beat, nginx).
- Non-root container users; read-only root filesystem where possible.
- Pinned base images; images scanned in CI (Trivy).

### 17.2 Images
| Image | Purpose |
|-------|---------|
| `vt-backend` | Django/DRF served by Gunicorn+Uvicorn workers |
| `vt-worker` | Same codebase, entrypoint runs Celery worker |
| `vt-beat` | Celery Beat scheduler |
| `vt-frontend` | Built SPA static assets served by Nginx |
| `vt-nginx` | Reverse proxy + static/media routing |

### 17.3 Local Development (`docker-compose`)
Compose brings up: `backend`, `worker`, `beat`, `postgres`, `redis`, `minio` (S3-compatible), `mailhog` (email), and `frontend` (Vite dev server). This yields full dev/prod parity for the media, cache, and queue subsystems locally.

### 17.4 Build & Runtime Notes
- Frontend build artifacts are produced in a build stage and copied into the Nginx image.
- Health checks (`/healthz` liveness, `/readyz` readiness) defined for orchestrator probes.
- Configuration purely via env vars; no secrets baked into images.

---

## 18. CI/CD

### 18.1 Platform
**GitHub Actions** drives all automation, triggered on pull requests and pushes to protected branches.

### 18.2 Pipeline Stages
```
PR opened / push
   │
   ├─ Lint & Format      (ruff, black, mypy | eslint, prettier, tsc)
   ├─ Unit Tests         (pytest | vitest)  + coverage gate
   ├─ Build              (docker build multi-stage; vite build)
   ├─ Security Scan      (Trivy image scan, pip-audit, npm audit, secret scan)
   ├─ Integration Tests  (spin up postgres/redis services; DRF + DB)
   ├─ E2E (stage)        (Playwright against ephemeral env)   [main only]
   ├─ Publish Images     (tagged, to registry)                [main only]
   └─ Deploy             (stage auto; prod gated approval)
```

### 18.3 Quality Gates
- Coverage thresholds enforced (backend domain ≥ 85%).
- No high/critical vulnerabilities may merge.
- OpenAPI schema diff check — breaking API changes require a version bump + label.
- Migrations checked for backward compatibility.

### 18.4 Deployment Automation
- Immutable, versioned images (git SHA tags).
- Stage deploys on merge to `main`; production deploys require manual approval and run **database migrations as a pre-deploy job** (expand phase) before the new image rolls out.

---

## 19. Logging

### 19.1 Principles
- **Structured JSON logs** with correlation IDs (request ID / trace ID propagated end-to-end).
- Consistent schema: timestamp, level, logger, message, `trace_id`, `user_id` (if any), context, event.
- **No PII or secrets** in logs — child data, tokens, and credentials are redacted by a logging filter (Privacy by Design).

### 19.2 Pipeline
```
App/Worker/Nginx (stdout JSON) → collector (Promtail/Vector) → Loki → Grafana
Application errors/exceptions → Sentry
```

### 19.3 Levels & Retention
- Levels: DEBUG (dev only), INFO, WARNING, ERROR, CRITICAL.
- Hot retention 30 days in Loki; archival to S3 (cold) per compliance retention policy.
- Audit-relevant events (auth, authorization decisions, scoring, data deletion) are written to the **immutable audit log**, separate from operational logs.

---

## 20. Monitoring

### 20.1 Three Pillars
- **Metrics:** Prometheus scrapes app, Celery, PostgreSQL, Redis, Nginx exporters; visualized in Grafana.
- **Traces:** OpenTelemetry instrumentation across API → DB → cache → tasks (100% of critical paths).
- **Logs:** Loki (see §19); errors in Sentry.

### 20.2 Golden Signals & SLOs
| Signal | Metric | SLO |
|--------|--------|-----|
| Latency | API p95 | read < 300 ms, write < 600 ms |
| Traffic | RPS, active users | tracked, capacity-planned |
| Errors | 5xx rate | < 0.1% |
| Saturation | CPU/mem, queue depth, DB connections | alert thresholds defined |

### 20.3 Business & Domain Dashboards
- Submissions/hour, judging progress per competition, notification delivery success, consent completion rate.

### 20.4 Alerting
- Alertmanager routes to on-call (severity-tiered). Every alert links to a runbook.
- Synthetic checks probe critical user journeys (login, submit, score) from external locations.

---

## 21. Security

### 21.1 Security by Design Posture
Threat modeling (STRIDE) is performed per bounded context. Security controls are layered (defense in depth) and default-deny.

### 21.2 Transport & Storage
- TLS 1.2+ everywhere; HSTS; modern cipher suites.
- Encryption at rest for DB, backups, and S3 (AES-256).
- Signed, short-TTL URLs for all media access; no public buckets.

### 21.3 Application Security
- Django/DRF secure defaults: CSRF protection, secure cookies, clickjacking protection, SQL injection avoidance via ORM/parameterization.
- Security headers at Nginx: CSP, X-Content-Type-Options, Referrer-Policy, Permissions-Policy.
- Input validation at the edge (serializers + Zod) **and** domain invariants.
- Rate limiting/throttling and bot mitigation on auth and submission endpoints.
- Uploaded media: MIME/type validation, size limits, **antivirus scanning** (async), and content moderation hooks.

### 21.4 Secrets & Access
- Secrets in a manager/Vault; least-privilege IAM; no long-lived cloud keys in app nodes.
- MFA for privileged roles; audit trail on all admin actions.

### 21.5 Supply Chain
- Dependency pinning + lockfiles; automated dependency updates; SCA (pip-audit/npm audit); image scanning; SBOM generation.

### 21.6 Privacy by Design (minors)
- **Data minimization:** collect only what a competition requires.
- **Consent as a first-class, versioned record** tied to every minor's participation and data-processing purpose.
- **Purpose limitation & retention:** data retained only for defined periods, then purged (including from backups per policy).
- **Access minimization:** child PII visible only to the guardian, assigned teacher, and authorized organizers/jury (jury typically sees anonymized/pseudonymized works to protect fairness and privacy).
- **DSAR support:** export and deletion workflows with cascade to S3.
- **Compliance alignment:** 152-ФЗ (RF Personal Data Law); localization of personal data storage as required.

### 21.7 Auditing
Immutable, append-only audit log for authentication, authorization decisions, scoring, result publication, and personal-data operations.

---

## 22. Performance

### 22.1 Targets
Per §3: read p95 < 300 ms, write p95 < 600 ms, mobile LCP p75 < 2.5 s.

### 22.2 Backend Techniques
- **Caching (Redis):** response caching for hot read endpoints, computed rankings, and reference data; cache invalidation driven by domain events.
- **Query optimization:** `select_related`/`prefetch_related` discipline, avoidance of N+1 (enforced in tests), tuned indexes, `pg_stat_statements` review.
- **Read replicas** for heavy analytics/reporting reads.
- **Async offload:** anything slow (media processing, PDF generation, bulk ops) goes to Celery.
- **Pagination everywhere;** no unbounded queries.

### 22.3 Media & Frontend
- Direct-to-S3 uploads via pre-signed URLs (API never proxies large files).
- CDN + responsive images + thumbnails for delivery.
- SPA code splitting, lazy loading, HTTP caching, and bundle budgets enforced in CI.

### 22.4 Capacity & Load Testing
- Load and soak tests (k6/Locust) model deadline spikes before each season.
- Performance regression gate in CI on critical endpoints.

---

## 23. Scalability

### 23.1 Horizontal Scale
- **Stateless API pods** scale horizontally behind the load balancer; sessions are token-based (no sticky sessions).
- **Celery workers** scale independently by queue; priority queues separate latency-sensitive (notifications) from heavy (media) work.

### 23.2 Data Scale
- Read replicas absorb read growth.
- PgBouncer bounds DB connections.
- Table partitioning (e.g., submissions/scores by competition or time) as volumes grow.
- The **modular monolith with schema-per-context** allows extracting a hot context into its own service/database later with minimal blast radius.

### 23.3 Caching & Queueing
- Redis for cache, rate limiting, distributed locks, and the Celery broker; clustered/HA in production.

### 23.4 Autoscaling
- HPA on CPU/memory and custom metrics (queue depth, RPS). Scale-out policies validated against seasonal deadline spikes.

### 23.5 Evolution to Microservices (only if justified)
Extraction candidates (Judging, Media processing) are identified by scaling pressure or team boundaries — never speculatively. Event-driven boundaries already in place make extraction incremental (see §31).

---

## 24. Backup Strategy

### 24.1 Objectives
- **RPO ≤ 15 minutes**, **RTO ≤ 2 hours** (§3).

### 24.2 PostgreSQL
- Automated **daily full backups** + **continuous WAL archiving** (PITR — point-in-time recovery).
- Backups encrypted (AES-256) and stored in S3, with cross-region copies.
- Retention: 7 daily, 4 weekly, 12 monthly (tiered).

### 24.3 Object Storage (S3)
- Versioning + lifecycle policies; cross-region replication for durability.

### 24.4 Redis
- Treated primarily as cache/broker (rebuildable). Persistence (AOF/RDB) enabled for broker durability where task loss is unacceptable; critical state is always sourced from PostgreSQL, not Redis.

### 24.5 Verification
- **Automated restore drills** on a schedule verify backups are actually recoverable; backup success and freshness are monitored and alerted. An unverified backup is treated as no backup.

### 24.6 Configuration & Secrets
- Infrastructure-as-code and secrets are versioned/backed up separately with restricted access.

---

## 25. Disaster Recovery

### 25.1 Strategy
- **Warm-standby** posture: infrastructure defined as code, database replicated cross-region (streaming replica + PITR), media replicated cross-region in S3.

### 25.2 Scenarios & Response
| Scenario | Response |
|----------|----------|
| Primary DB failure | Promote replica; repoint PgBouncer; resume (within RTO) |
| Region outage | Fail over to secondary region using IaC + replicated data/media |
| Data corruption | PITR to a timestamp before corruption |
| Ransomware/accidental deletion | Restore from immutable, versioned, encrypted backups |
| Redis loss | Rebuild cache; replay outbox for in-flight events |

### 25.3 Runbooks & Governance
- Documented, tested runbooks for each scenario, with named roles (incident commander, comms, ops).
- **DR game-days** performed at least twice yearly; RTO/RPO measured and reported.
- Post-incident reviews are blameless and produce tracked action items.

---

## 26. Coding Standards

### 26.1 Backend (Python)
- **Formatting/linting:** `black` + `ruff`; **typing:** `mypy` (strict on domain/application).
- PEP 8 + project conventions; type hints mandatory in domain and application layers.
- Docstrings on public interfaces; ubiquitous-language names (no anemic generic names in the domain).
- No business logic in views/serializers; no ORM in the domain layer.

### 26.2 Frontend (TypeScript)
- **TypeScript strict mode**; ESLint + Prettier.
- No `any` in committed code (justified exceptions documented).
- Feature-sliced dependency rules enforced by lint rules.
- Accessibility linting (jsx-a11y).

### 26.3 Cross-Cutting
- Meaningful names, small functions, explicit error handling, no dead code.
- Conventional Commits.
- Every PR: linted, typed, tested, reviewed by ≥ 1 peer (2 for security-sensitive areas).
- Definition of Done includes tests, docs, and observability (logs/metrics) for new behavior.

---

## 27. Git Strategy

### 27.1 Model — Trunk-Based with short-lived branches
- **`main`** is always releasable and protected.
- Short-lived **feature branches** (`feat/…`, `fix/…`, `chore/…`) merged via PR; branches live < 2 days ideally.
- Optional **`release/*`** branches for hardening a versioned release when needed.

### 27.2 Branch Protection
- Required green CI, required review(s), no direct pushes to `main`, linear history (squash merge).
- Signed commits for release tags.

### 27.3 Commits & Versioning
- **Conventional Commits** drive changelog generation and **SemVer** versioning.
- Release tags (`vMAJOR.MINOR.PATCH`) map to immutable container images.

### 27.4 Reviews
- PRs must be small and focused; large changes decomposed. Architecture-affecting PRs reference the relevant ADR.

---

## 28. Testing Strategy

### 28.1 Test Pyramid
```
        /\        E2E (Playwright) — critical journeys, few
       /  \
      /----\      Integration (DRF+DB, Celery, contract) — moderate
     /------\
    /--------\    Unit (domain, application, components) — many, fast
```

### 28.2 Backend
- **Domain/application unit tests** run without a database (pure Python) — fast and central to the ≥ 85% coverage gate.
- **Integration tests** with real PostgreSQL/Redis (Docker services in CI): repositories, DRF endpoints, Celery tasks.
- **Contract tests:** responses validated against the OpenAPI schema; N+1 query assertions.
- Factories (`factory_boy`) + `pytest`; deterministic, isolated tests.

### 28.3 Frontend
- **Unit/component:** Vitest + React Testing Library.
- **Integration:** mock the generated API client; test TanStack Query flows.
- **E2E:** Playwright on ephemeral stage environments (register → submit → score → results).
- Accessibility checks (axe) in component and E2E tests.

### 28.4 Non-Functional Testing
- Load/soak tests (k6) pre-season; security tests (SAST/DAST, dependency scans) in CI; periodic penetration testing.

### 28.5 Test Data & Privacy
- No production PII in test environments; synthetic data generators only.

---

## 29. Deployment Strategy

### 29.1 Principles
- **Zero-downtime deployments** via rolling updates and backward-compatible migrations (expand/contract).
- Immutable, versioned images promoted through environments (build once, deploy many).

### 29.2 Flow
```
merge → main → build & scan → deploy STAGE (auto) → E2E + smoke
       → manual approval → migrate (expand) → rolling deploy PROD → smoke → done
       (contract migration ships in a later release once code no longer needs old schema)
```

### 29.3 Progressive Delivery
- Rolling by default; **canary** for high-risk changes (small traffic slice, watch golden signals, auto-rollback on error/latency breach).
- **Feature flags** decouple deploy from release, enabling dark launches and quick disablement.

### 29.4 Rollback
- One-command rollback to the previous immutable image; DB rollbacks avoided by design (never destructive in the expand phase).
- Health/readiness probes gate traffic; failed rollout auto-halts.

### 29.5 Migrations
- Run as an explicit, monitored pre-deploy job; long/locking migrations use online-migration techniques.

---

## 30. Architecture Decision Records (ADR)

### 30.1 Process
- ADRs live in-repo under `docs/adr/NNNN-title.md`, are immutable once accepted (superseded, not edited), and use the MADR format: **Context → Decision → Consequences → Status**.
- Any decision that changes a §4 principle or a cross-cutting concern requires an ADR referenced from the PR.

### 30.2 Baseline ADR Register

| ADR | Decision | Status |
|-----|----------|--------|
| ADR-0001 | Adopt **Modular Monolith** over microservices for v1 | Accepted |
| ADR-0002 | **Django 6 + DRF** as backend framework | Accepted |
| ADR-0003 | **PostgreSQL** as single system of record; media in **S3** | Accepted |
| ADR-0004 | **Schema-per-bounded-context** in PostgreSQL | Accepted |
| ADR-0005 | **Clean Architecture** layering per module | Accepted |
| ADR-0006 | **JWT** (short access + rotating refresh) authentication | Accepted |
| ADR-0007 | **RBAC + scoping** for authorization | Accepted |
| ADR-0008 | **Event-driven** integration via transactional outbox + Redis/Celery | Accepted |
| ADR-0009 | **API First** with OpenAPI 3.1 as contract source of truth | Accepted |
| ADR-0010 | **React 19 + Vite + Tailwind + shadcn/ui + TanStack Query** frontend | Accepted |
| ADR-0011 | **Trunk-based** Git strategy with protected `main` | Accepted |
| ADR-0012 | **Direct-to-S3 pre-signed uploads** for media | Accepted |
| ADR-0013 | **Jury sees pseudonymized submissions** for fairness & privacy | Accepted |

### 30.3 Example ADR (abridged)

**ADR-0001 — Adopt Modular Monolith**
- **Context:** Tens-of-thousands-user target, small initial team, need for DDD boundaries without microservice ops overhead.
- **Decision:** Build a single deployable Django app partitioned into strict bounded-context modules with event-driven integration and schema-per-context.
- **Consequences:** (+) Fast delivery, simple ops, strong boundaries, easy transactions within contexts. (−) Requires discipline to prevent cross-module coupling; shared deployment unit. Mitigation: enforced module boundaries, per-context schemas, and events make future extraction low-risk.

---

## 31. Future Evolution

### 31.1 Roadmap Themes
1. **Selective service extraction:** promote hot contexts (Judging, Media processing) to independent services/databases when scaling pressure or team topology justifies it — enabled by existing event boundaries (ADR-0008).
2. **Realtime experiences:** WebSockets/SSE (Django Channels) for live judging dashboards and result reveals.
3. **Mobile applications:** native/PWA clients consuming the same API First contract.
4. **Payments & monetization:** full Billing context, tiered plans, and marketplace features.
5. **Advanced identity:** SSO/OIDC, Gosuslugi integration, and institution-level federation behind the identity gateway.
6. **Analytics platform:** CQRS read models and a data warehouse fed by domain events for organizer/institution insights.
7. **AI-assisted tooling:** plagiarism/originality checks, content moderation, and jury-assist suggestions (advisory, never decisive), applied with strict privacy safeguards for minors.
8. **Internationalization:** additional locales and multi-region deployment.

### 31.2 Guardrails for Evolution
- Every extraction/expansion is justified by a metric or team-topology need and captured in an ADR.
- Principles in §4 (privacy, security, API First, event-driven) remain invariant across the roadmap.
- Backward compatibility and zero-downtime remain hard requirements.

---

*End of document — VT Platform Architecture v1.0.*
