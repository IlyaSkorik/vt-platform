import { Link, Outlet } from "react-router";
import { APP_NAME, ROUTES } from "@/shared/config";
import { useSectionSeo } from "@/shared/seo";
import { ThemeToggle } from "./theme-toggle";

/**
 * Auth layout — the shell for guest/authentication screens (login, register,
 * password reset, email verification).
 *
 * Mobile-first: a single centered column that scales up gracefully. Contains
 * layout placeholders only; the auth forms are added by the Auth feature.
 */
export function AuthLayout(): React.JSX.Element {
  // A sign-in form is not a search result, and a password-reset URL carries a
  // token that must never be crawled. Closed here so every screen added to the
  // shell inherits it.
  useSectionSeo({ title: "Вход", robots: "noindex" });

  return (
    <div className="flex min-h-svh flex-col">
      <header className="flex items-center justify-between p-4">
        <Link to={ROUTES.home} className="font-semibold text-lg tracking-tight">
          {APP_NAME}
        </Link>
        <ThemeToggle />
      </header>

      <main className="flex flex-1 items-center justify-center p-4">
        <div className="w-full max-w-sm rounded-xl border bg-card p-6 shadow-elevation-2">
          <Outlet />
        </div>
      </main>

      <footer className="p-4 text-center text-muted-foreground text-xs">© {APP_NAME}</footer>
    </div>
  );
}
