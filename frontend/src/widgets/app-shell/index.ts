/**
 * Public API of the `app-shell` widget — the platform's permanent layout.
 *
 * A widget slice (FSD): composes `shared/ui` + `shared/config` navigation into
 * the authenticated application shell. It never imports from `app/` or
 * `features/`; app-level controls are injected via the `headerActions` slot.
 */
export { AppShell } from "./app-shell";
export { Breadcrumbs } from "./breadcrumbs";
export { useShell } from "./shell-context";
export type { AppShellProps, ShellState } from "./types";
