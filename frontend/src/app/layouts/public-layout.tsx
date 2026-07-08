import { Link, Outlet } from "react-router";
import { APP_NAME, ROUTES } from "@/shared/config";
import { Button } from "@/shared/ui";
import { ThemeToggle } from "./theme-toggle";

/**
 * PublicLayout — chrome for unauthenticated, public-facing pages (landing,
 * public competition listings).
 *
 * A lightweight top bar (brand + theme + sign-in) over a full-width content
 * region and a simple footer. No sidebar: public pages are marketing-oriented,
 * not app surfaces.
 */
export function PublicLayout(): React.JSX.Element {
  return (
    <div className="flex min-h-svh flex-col bg-background">
      <header className="sticky top-0 z-[var(--z-sticky)] flex h-16 items-center justify-between border-border border-b bg-background/95 px-4 backdrop-blur supports-[backdrop-filter]:bg-background/80 md:px-8">
        <Link
          to={ROUTES.home}
          className="flex items-center gap-2 rounded-md font-semibold text-foreground text-lg tracking-tight outline-none focus-visible:ring-2 focus-visible:ring-ring"
        >
          <span
            aria-hidden="true"
            className="flex size-8 items-center justify-center rounded-md bg-primary font-bold text-primary-foreground text-sm"
          >
            ВТ
          </span>
          {APP_NAME}
        </Link>
        <div className="flex items-center gap-2">
          <ThemeToggle />
          <Button asChild variant="ghost">
            <Link to={ROUTES.login}>Войти</Link>
          </Button>
        </div>
      </header>

      <main className="flex-1">
        <Outlet />
      </main>

      <footer className="border-border border-t px-4 py-6 text-center text-muted-foreground text-xs md:px-8">
        © {new Date().getFullYear()} {APP_NAME}
      </footer>
    </div>
  );
}
