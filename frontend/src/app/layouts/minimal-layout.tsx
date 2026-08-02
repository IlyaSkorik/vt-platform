import { Link, Outlet } from "react-router";
import { APP_NAME, ROUTES } from "@/shared/config";
import { useSectionSeo } from "@/shared/seo";
import { ThemeToggle } from "./theme-toggle";

/**
 * MinimalLayout — a distraction-free, centered shell.
 *
 * For focused, single-task flows that want neither the app sidebar nor the
 * public marketing chrome: onboarding steps, standalone confirmations, print
 * views. Just a brand line, the theme control, and a centered content column.
 */
export function MinimalLayout(): React.JSX.Element {
  // Single-task flows reached by an emailed link — an invitation token is the
  // whole address, so none of it belongs in an index.
  useSectionSeo({ title: APP_NAME, standaloneTitle: true, robots: "noindex" });

  return (
    <div className="flex min-h-svh flex-col bg-background">
      <header className="flex h-16 items-center justify-between px-4 md:px-8">
        <Link
          to={ROUTES.home}
          className="rounded-md font-semibold text-foreground text-lg tracking-tight outline-none focus-visible:ring-2 focus-visible:ring-ring"
        >
          {APP_NAME}
        </Link>
        <ThemeToggle />
      </header>

      <main className="flex flex-1 items-center justify-center p-4">
        <div className="w-full max-w-md">
          <Outlet />
        </div>
      </main>
    </div>
  );
}
