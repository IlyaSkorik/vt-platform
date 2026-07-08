# `entities/` — Domain entities layer

Feature-Sliced Design layer for **business domain models** and their read/display
representations: `competition`, `submission`, `participant`, `user`, etc.

Each entity is a **slice** with segments (`model/`, `ui/`, `api/`, `lib/`) and a
public API (`index.ts`). Entities know their own shape and how to render
themselves, but contain **no user-facing capabilities** (those live in
`features/`).

## Dependency rule

```
pages → widgets → features → entities → shared
```

An entity may import only from `shared/` and other entities via their public
API. It must never import from `features/`, `widgets/`, `pages/`, or `app/`.

> Intentionally empty during bootstrap — no business logic is implemented yet
> (see the foundation scope). Add slices here as domains come online.
