# Festival Catalog — Participant Portal entry point

The first screen every participant sees: a modern, Eventbrite-style catalog of
creative festivals. It is read-only discovery — no applications, participants or
payments here.

Route: `/cabinet/competitions` ("Фестивали"). Screenshots live in
`docs/screenshots/festival-catalog/`.

## Data source — a dedicated public read model

The catalog is **not** wired to the organizer Competition API (staff-only, thin
projection). It is backed by a purpose-built, unauthenticated read model:

```
GET /api/v1/public/festivals   →  { data: PublicFestival[], meta }
```

- Backend: `apps/competitions/application/read_models/public_catalog.py` (pure
  DTOs + projection rules) + `infrastructure/read_models/public_catalog.py`
  (ORM query). Completely separate from the `Competition` aggregate and the
  organizer `CompetitionViewSet` — a CQRS read side (ARCH-001 §7.2, §14).
- Visible lifecycle states: `PUBLISHED, REGISTRATION_OPEN, REGISTRATION_CLOSED,
  RUNNING, COMPLETED`. **Never** `DRAFT / CONFIGURED / READY / ARCHIVED`.
- Each maps to a coarse **public status** driving the card CTA:

  | Domain state          | Public status        | Card action              |
  | --------------------- | -------------------- | ------------------------ |
  | `PUBLISHED`           | `COMING_SOON`        | "Регистрация скоро" (off)|
  | `REGISTRATION_OPEN`   | `REGISTRATION_OPEN`  | "Подать заявку" (on)     |
  | `REGISTRATION_CLOSED` | `REGISTRATION_CLOSED`| "Регистрация закрыта"(off)|
  | `RUNNING`             | `RUNNING`            | "Подробнее" only         |
  | `COMPLETED`           | `COMPLETED`          | "Подробнее" only         |

- Organizer identity resolves through the Organization context's published
  `OrganizationDirectory` read-port (no cross-context aggregate import).

## Component hierarchy (Feature-Sliced Design)

```
pages/  applications/participant/pages/festivals/
        └─ FestivalCatalogPage                     (route index: heading + container)
           FestivalLandingPlaceholderPage          (:festivalId  — prepared, landing later)
           FestivalApplyPlaceholderPage            (:festivalId/apply — prepared, wizard later)

widgets/ festival-catalog/
        └─ FestivalCatalog                          (orchestrator: data + state + layout)
           ├─ FestivalCatalogToolbar                (search · sort · filters toggle)
           ├─ FestivalFiltersPanel                  (registration · format · category · city · dates)
           ├─ FestivalGrid / FestivalGridSkeleton   (responsive grid: 1 / 2 / 3 cols)
           │   └─ FestivalCard / FestivalCardSkeleton
           ├─ FestivalFeaturedPanel                 (right rail: featured + upcoming; ≥xl)
           └─ Catalog{NoFestivals,NoResults,Error}  (empty / no-match / error states)

features/ festival-catalog/
        ├─ api/   usePublicFestivals (TanStack Query) · festivalCatalogKeys
        └─ lib/   filter-festivals · format · status · modes · highlights · media (pure)
```

## Catalog architecture

- **One cached read** (`usePublicFestivals`, `staleTime` 60s) backs the whole
  screen. Search, filtering and sorting are computed client-side over the cached
  array (`useMemo`), so every interaction is instant and never hits the network —
  "live filtering" with zero round-trips.
- Explicit states: **loading** (skeleton grid), **error** (retry), **empty** (no
  festivals), **no-results** (search/filters exclude everything → reset action).
- Skeleton grid renders immediately (optimistic loading).

## Search architecture

`searchFestivals(list, query)` — case-insensitive, whitespace-tokenized. Every
term must appear (AND) in a haystack of `title + city + organizer + categories`.
Empty query matches all. Debounce-free (dataset is small; filtering is O(n)).

## Filter architecture

`CatalogFilters` is a flat, additive record — each axis independent, so a new
facet is a new field + one branch (future-ready):

- **Registration**: `OPEN`, `CLOSING_SOON` (cut-off within 7 days of now).
- **Participation format**: `IN_PERSON | ONLINE | HYBRID` (normalized from
  free-text format names via a keyword heuristic in the backend read model).
- **Category** & **City**: data-driven options via `deriveFilterOptions`.
- **Competition dates**: inclusive from/to window (period-overlap match).

Axes are ANDed; options within one axis are ORed. `sortFestivals` offers Newest ·
Registration closing soon · Competition date · Alphabetical. All pure + unit-tested.

## API integration

- Orval target `vtPublicCatalog` (tag `Public Catalog`) generates the typed
  `listPublicFestivals` client + models into `shared/api/generated/**`.
- `usePublicFestivals` wraps it in TanStack Query, unwrapping the `{ data, meta }`
  envelope through the shared Ky mutator (correlation ids, error normalization).
- Navigation is prepared but deferred: **More details → landing** and
  **Apply → registration wizard** route to `:festivalId` / `:festivalId/apply`
  placeholders (no 404), a drop-in point for the later features.

## Known data gaps (surfaced, not faked)

- **Registration progress**: needs the Applications BC (not built) + a capacity
  model (not modelled). The `PublicFestival` view omits it; the card footer
  renders without a progress bar and gains it for free when the data exists.
- **City**: the host city (`contacts_config.venue_details.city`) — a distinct
  fact, not the venue place name (`venue_name`, exposed separately for the later
  landing page). `null` when the organizer hasn't set it.
- **Organizer logo**: the Organization aggregate stores none yet — `logo` is
  `null`; the card shows initials. The contract already carries the field.
