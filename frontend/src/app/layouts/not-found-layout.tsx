import { Link, Outlet } from "react-router";
import { APP_NAME, ROUTES } from "@/shared/config";

/**
 * NotFoundLayout — chrome for the 404 / catch-all route.
 *
 * A neutral, centered frame with a single route home. Kept separate from the
 * other layouts so an unmatched URL never renders app or public chrome (which
 * could imply the destination exists) and never depends on auth state.
 */
export function NotFoundLayout(): React.JSX.Element {
  return (
    <div className="flex min-h-svh flex-col bg-background">
      <header className="flex h-16 items-center px-4 md:px-8">
        <Link
          to={ROUTES.home}
          className="rounded-md font-semibold text-foreground text-lg tracking-tight outline-none focus-visible:ring-2 focus-visible:ring-ring"
        >
          {APP_NAME}
        </Link>
      </header>
      <main className="flex flex-1 items-center justify-center p-6">
        <Outlet />
      </main>
    </div>
  );
}
