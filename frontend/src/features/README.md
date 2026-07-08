# `features/` — User-facing capabilities layer

Feature-Sliced Design layer for **capabilities (verbs)** the user performs:
`auth`, `register-participant`, `submit-work`, `score-submission`,
`manage-competition`, etc.

Each feature is a **slice** owning its UI, TanStack Query hooks, forms
(React Hook Form + Zod), and interaction logic, exposed via a public API
(`index.ts`).

## Dependency rule

```
pages → widgets → features → entities → shared
```

A feature may import from `entities/` and `shared/` (via their public APIs). It
must never import from `widgets/`, `pages/`, or `app/`, nor from a sibling
feature's internals.

> Intentionally empty during bootstrap. The Auth context/provider and route
> guards live in `app/` for now (composition root); the full **auth** feature
> (forms, session lifecycle, API integration) will be implemented here.
