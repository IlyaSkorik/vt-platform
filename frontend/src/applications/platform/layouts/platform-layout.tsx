import {
  Building2,
  FlaskConical,
  HandCoins,
  LayoutDashboard,
  MessageSquareQuote,
  Trash2,
  Wallet,
} from "lucide-react";
import { Link, NavLink, Outlet } from "react-router";

import { SiteFooter } from "@/app/layouts/site-footer";
import { ThemeToggle } from "@/app/layouts/theme-toggle";
import { UserMenu } from "@/app/layouts/user-menu";
import { WorkspaceSwitcher } from "@/applications/workspace-switcher";
import { ROUTES } from "@/shared/config";
import { cn } from "@/shared/lib";
import { BrandMark } from "@/shared/ui";

const SKIP_TARGET_ID = "platform-main";

const NAVIGATION = [
  { title: "Сводка", path: ROUTES.platform, icon: LayoutDashboard, end: true },
  { title: "Организации", path: ROUTES.platformOrganizations, icon: Building2, end: false },
  { title: "Расходы", path: ROUTES.platformFinance, icon: Wallet, end: false },
  { title: "Поступления", path: ROUTES.platformCommission, icon: HandCoins, end: false },
  { title: "Тестирование", path: ROUTES.platformTesting, icon: FlaskConical, end: false },
  { title: "Отзывы", path: ROUTES.platformReviews, icon: MessageSquareQuote, end: false },
  // Last, and on its own: the only screen here that destroys anything.
  { title: "Удаление", path: ROUTES.platformErase, icon: Trash2, end: false },
] as const;

/**
 * The platform operator's shell.
 *
 * Deliberately its own, and deliberately plainer than the organizer's: this is
 * the console *above* the organizations, and sharing their chrome would blur
 * exactly the line that matters here.
 */
export function PlatformLayout(): React.JSX.Element {
  return (
    <div className="flex min-h-svh flex-col bg-background text-foreground">
      <a
        href={`#${SKIP_TARGET_ID}`}
        className="sr-only rounded-md bg-primary px-4 py-2 text-primary-foreground focus:not-sr-only focus:absolute focus:top-4 focus:left-4 focus:z-[var(--z-toast)]"
      >
        Перейти к содержимому
      </a>
      <header className="sticky top-0 z-[var(--z-sticky)] flex min-h-16 flex-wrap items-center gap-3 border-border border-b bg-background/95 px-4 backdrop-blur supports-[backdrop-filter]:bg-background/80">
        <Link
          to={ROUTES.platform}
          className="flex items-center gap-2 rounded-md font-semibold outline-none focus-visible:ring-2 focus-visible:ring-ring"
        >
          <BrandMark className="size-8 rounded-md" />
          <span className="flex min-w-0 flex-col">
            <span className="truncate">Платформа</span>
            <span className="truncate font-normal text-muted-foreground text-xs">
              Администрирование платформы
            </span>
          </span>
        </Link>
        <nav aria-label="Навигация платформы" className="flex items-center gap-1">
          {NAVIGATION.map((item) => {
            const Icon = item.icon;
            return (
              <NavLink
                key={item.path}
                to={item.path}
                end={item.end}
                className={({ isActive }) =>
                  cn(
                    "inline-flex min-h-9 items-center gap-2 rounded-md px-3 py-2 font-medium text-sm outline-none transition-colors focus-visible:ring-2 focus-visible:ring-ring",
                    isActive
                      ? "bg-primary/10 text-primary"
                      : "text-muted-foreground hover:bg-accent hover:text-accent-foreground",
                  )
                }
              >
                <Icon className="size-4 shrink-0" aria-hidden="true" />
                <span>{item.title}</span>
              </NavLink>
            );
          })}
        </nav>
        <div className="ml-auto flex shrink-0 items-center gap-1">
          {/* The way back out. Every other shell carries the switcher, and without it the
              console is a one-way door: an operator who is also an organizer would have to
              type `/staff` to return to it. */}
          <WorkspaceSwitcher className="hidden xl:flex" />
          <ThemeToggle />
          <UserMenu />
        </div>
      </header>
      <div className="bg-muted/20 px-4 py-2 xl:hidden">
        <WorkspaceSwitcher />
      </div>
      <main
        id={SKIP_TARGET_ID}
        tabIndex={-1}
        className="min-w-0 flex-1 overflow-x-clip p-4 outline-none md:p-6 lg:p-8"
      >
        <Outlet />
      </main>
      <SiteFooter />
    </div>
  );
}
