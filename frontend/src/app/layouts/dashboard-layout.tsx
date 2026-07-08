import { LayoutDashboard, UserCircle, Users } from "lucide-react";
import type { ComponentType } from "react";
import { Link, NavLink, Outlet } from "react-router";
import { APP_NAME, ROUTES } from "@/shared/config";
import { cn } from "@/shared/lib";
import { ThemeToggle } from "./theme-toggle";

interface NavItem {
  to: string;
  label: string;
  icon: ComponentType<{ className?: string; "aria-hidden"?: boolean }>;
}

const NAV_ITEMS: NavItem[] = [
  { to: ROUTES.dashboard, label: "Панель", icon: LayoutDashboard },
  { to: ROUTES.participants, label: "Участники", icon: Users },
  { to: ROUTES.profile, label: "Профиль", icon: UserCircle },
];

/**
 * Dashboard layout — the authenticated application shell.
 *
 * A responsive frame with a persistent sidebar on desktop and a top bar on
 * mobile (mobile-first, ARCH-001 §4.5). Provides navigation chrome only; page
 * content is a placeholder until the corresponding features land.
 */
export function DashboardLayout(): React.JSX.Element {
  return (
    <div className="flex min-h-svh flex-col md:flex-row">
      <aside className="flex shrink-0 flex-col border-b bg-card md:h-svh md:w-64 md:border-r md:border-b-0">
        <div className="flex items-center justify-between p-4">
          <Link to={ROUTES.dashboard} className="font-semibold text-lg tracking-tight">
            {APP_NAME}
          </Link>
          <div className="md:hidden">
            <ThemeToggle />
          </div>
        </div>
        <nav aria-label="Основная навигация" className="flex gap-1 overflow-x-auto p-2 md:flex-col">
          {NAV_ITEMS.map(({ to, label, icon: Icon }) => (
            <NavLink
              key={to}
              to={to}
              className={({ isActive }) =>
                cn(
                  "flex items-center gap-3 rounded-md px-3 py-2 font-medium text-sm transition-colors",
                  isActive
                    ? "bg-accent text-accent-foreground"
                    : "text-muted-foreground hover:bg-accent hover:text-accent-foreground",
                )
              }
            >
              <Icon className="size-4" aria-hidden />
              {label}
            </NavLink>
          ))}
        </nav>
      </aside>

      <div className="flex flex-1 flex-col">
        <header className="hidden items-center justify-end border-b p-4 md:flex">
          <ThemeToggle />
        </header>
        <main className="flex-1 p-4 md:p-8">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
