# `widgets/` — Composite UI blocks layer

Feature-Sliced Design layer for **self-contained composite blocks** that combine
features and entities into a meaningful section of a page: dashboards, data
tables, navigation shells, complex cards.

Each widget is a **slice** with a public API (`index.ts`).

## Dependency rule

```
pages → widgets → features → entities → shared
```

A widget may import from `features/`, `entities/`, and `shared/` (via their
public APIs). It must never import from `pages/` or `app/`.

> Intentionally empty during bootstrap — no widgets are implemented yet.
