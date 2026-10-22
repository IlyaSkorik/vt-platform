import { Link, Outlet } from "react-router";

import { UserMenu } from "@/app/layouts/user-menu";
import { APP_NAME, ROUTES } from "@/shared/config";
import { useSectionSeo } from "@/shared/seo";

import { ThemeToggle } from "./theme-toggle";

/**
 * JuryLayout — the shell a judge marks from.
 *
 * Its own shell rather than one of the two workspaces, for the reason the routes give:
 * a jury member is a guest of the organization, and the staff shell would hand them the
 * applications, the money and the participants along with the marks.
 *
 * Not `MinimalLayout` either, which is where this screen started. That one centres a
 * 384px column in the viewport — right for an invitation card, wrong for a programme of
 * forty acts on a tablet held sideways in a dark hall.
 *
 * The link back to the cabinet matters more than it looks: a judge is usually also a
 * teacher with entries of their own, and this is the only way between the two.
 */
export function JuryLayout(): React.JSX.Element {
  useSectionSeo({ title: "Судейство", standaloneTitle: true, robots: "noindex" });

  return (
    <div className="flex min-h-svh flex-col bg-background text-foreground">
      <header className="sticky top-0 z-[var(--z-sticky)] flex min-h-16 items-center gap-3 border-border border-b bg-background/95 px-4 backdrop-blur supports-[backdrop-filter]:bg-background/80 md:px-6">
        <Link
          to={ROUTES.jury}
          className="min-w-0 rounded-md font-semibold text-foreground tracking-tight outline-none focus-visible:ring-2 focus-visible:ring-ring"
        >
          <span className="block truncate">{APP_NAME}</span>
          <span className="block truncate font-normal text-muted-foreground text-xs">
            Судейство
          </span>
        </Link>
        <div className="flex-1" />
        <Link
          to={ROUTES.cabinet}
          className="rounded-md px-2 py-1 text-muted-foreground text-sm outline-none transition-colors hover:text-foreground focus-visible:ring-2 focus-visible:ring-ring"
        >
          Личный кабинет
        </Link>
        <ThemeToggle />
        <UserMenu />
      </header>
      <main className="min-w-0 flex-1 overflow-x-clip">
        <Outlet />
      </main>
    </div>
  );
}
