# VT Platform — Frontend

Production frontend for **«Взлёт талантов»** (VT Platform) — a mobile-first,
accessible React SPA that consumes the platform's versioned REST API.

> Architecture is defined in
> [`docs/architecture/ARCH-001` §8 & §15](../docs/architecture/ARCH-001-vt-platform-architecture.md#8-frontend-architecture).
> This is the long-term foundation, not an MVP.

## Tech stack

| Concern            | Choice |
| ------------------ | ------ |
| UI / language      | React 19 · TypeScript 6 (strict) |
| Build / dev server | Vite 7 |
| Package manager    | pnpm (via Corepack) |
| Routing            | React Router v7 (data router) |
| Server state       | TanStack Query v5 |
| Tables             | TanStack Table v8 |
| HTTP client        | Ky (never Axios) |
| Forms / validation | React Hook Form · Zod |
| Styling            | Tailwind CSS v4 (CSS-first, `@theme`) |
| Components         | shadcn/ui · Radix UI · Lucide icons |
| API SDK            | Orval (generated from OpenAPI 3.1) |
| Docs / workshop    | Storybook 9 |
| Testing            | Vitest · Testing Library · Playwright |
| Lint / format      | Biome |
| Git hooks          | Lefthook |

## Architecture — Feature-Sliced Design (v2.1)

Layers, with a strict **downward-only** dependency rule:

```
app  →  pages  →  widgets  →  features  →  entities  →  shared
```

| Layer      | Responsibility |
| ---------- | -------------- |
| `app/`     | Composition root: providers (Query, Theme, Auth, Error Boundary), router, layouts, entry. |
| `pages/`   | Route-level composition. Bootstrap: layout placeholders only. |
| `widgets/` | Composite UI blocks (dashboards, tables). _Empty at bootstrap._ |
| `features/`| User-facing capabilities (auth, submit-work…). _Empty at bootstrap._ |
| `entities/`| Domain models and their display components. _Empty at bootstrap._ |
| `shared/`  | Design-system-agnostic reusables — see below. |

### `shared/` segments

| Segment      | Contents |
| ------------ | -------- |
| `api/`       | Ky client, request/response/auth hooks, retry & timeout policy, RFC 9457 error mapper, TanStack Query client, Orval mutator, generated SDK (`generated/`). |
| `config/`    | Validated env, route registry, app metadata. |
| `constants/` | App-wide constants (theme key, breakpoints). |
| `hooks/`     | Generic hooks (`useMediaQuery`). |
| `lib/`       | Utilities (`cn`). |
| `styles/`    | Design tokens & global stylesheet (light/dark, radius, elevation, typography). |
| `types/`     | Cross-cutting utility types. |
| `ui/`        | In-repo design system (shadcn/ui + Radix). |
| `assets/`    | Static assets. |

Every slice/segment exposes a **public API** via `index.ts`; import across
layers only through those, never deep paths.

## Getting started

```bash
corepack enable            # provisions the pinned pnpm
pnpm install
cp .env.example .env.local # adjust VITE_API_BASE_URL as needed
pnpm dev                   # http://localhost:5173
```

## Scripts

| Script                | Purpose |
| --------------------- | ------- |
| `pnpm dev`            | Vite dev server. |
| `pnpm build`          | Type-check (`tsc -b`) then production build. |
| `pnpm preview`        | Serve the production build. |
| `pnpm typecheck`      | Strict type-check, no emit. |
| `pnpm lint`           | Biome check (lint + format + import order). |
| `pnpm lint:fix`       | Biome check with autofix. |
| `pnpm test`           | Vitest (unit/component). |
| `pnpm test:coverage`  | Vitest with V8 coverage. |
| `pnpm e2e`            | Playwright end-to-end. |
| `pnpm storybook`      | Storybook dev server (port 6006). |
| `pnpm build-storybook`| Static Storybook build. |
| `pnpm api:generate`   | Generate the typed API SDK from the OpenAPI contract (Orval). |
| `pnpm hooks:install`  | Install Lefthook git hooks (opt-in). |

## API SDK generation

The typed SDK is **not** committed — it is regenerated from the backend's
OpenAPI 3.1 contract:

```bash
# backend: publish the schema
python manage.py spectacular --file ../frontend/openapi/schema.yaml
# frontend: generate client + TanStack Query hooks into src/shared/api/generated
pnpm api:generate
```

All generated calls route through the shared Ky client (auth, retry, timeout,
error mapping), so the transport stays centralized.

## Conventions

- **Strict TypeScript**, no `any` in committed code.
- **Absolute imports** via the `@/*` alias.
- **Accessibility** (WCAG 2.1 AA) is a component acceptance criterion.
- **Mobile-first**: design for the smallest viewport, enhance upward.
- **ru-RU** primary locale; user-facing strings are externalized.
