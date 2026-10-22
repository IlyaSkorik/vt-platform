/**
 * Public API of `app/layouts` — the route-level layout shells.
 *
 * Each layout is a route `element` that renders `<Outlet />`; the router
 * (`app/router`) composes them with the access guards. `MinimalLayout` is the
 * focused, single-task shell an emailed link lands in; `JuryLayout` is the one a
 * guest judge marks from, which is neither workspace.
 */
export { AppShellLayout } from "./app-shell-layout";
export { AuthLayout } from "./auth-layout";
export { JuryLayout } from "./jury-layout";
export { MinimalLayout } from "./minimal-layout";
export { NotFoundLayout } from "./not-found-layout";
export { PublicLayout } from "./public-layout";
export { RootLayout } from "./root-layout";
export { ThemeToggle } from "./theme-toggle";
export { UserMenu } from "./user-menu";
