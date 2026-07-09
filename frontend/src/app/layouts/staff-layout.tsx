import { NavLink, Outlet } from "react-router";

import { ThemeToggle } from "@/app/layouts/theme-toggle";
import { UserMenu } from "@/app/layouts/user-menu";
import { WorkspaceSwitcher } from "@/app/layouts/workspace-switcher";
import { STAFF_NAVIGATION } from "@/shared/config";
import { cn } from "@/shared/lib";

function StaffSidebar(): React.JSX.Element {
  return (
    <aside className="hidden w-72 shrink-0 bg-slate-950 text-white lg:block">
      <div className="flex h-full flex-col gap-6 px-4 py-6">
        <div>
          <p className="text-xs font-semibold uppercase tracking-wide text-cyan-300">
            Staff Workspace
          </p>
          <h2 className="mt-2 text-lg font-semibold">Панель управления</h2>
        </div>
        <nav aria-label="Навигация панели управления" className="flex flex-col gap-1">
          {STAFF_NAVIGATION.map((item) => {
            const Icon = item.icon;
            return (
              <NavLink
                key={item.path}
                to={item.path}
                end={item.path === "/staff"}
                className={({ isActive }) =>
                  cn(
                    "flex min-h-10 items-center gap-3 rounded-md px-3 py-2 text-sm font-medium transition-colors",
                    isActive
                      ? "bg-cyan-300 text-slate-950"
                      : "text-slate-300 hover:bg-white/10 hover:text-white",
                  )
                }
              >
                <Icon className="h-4 w-4" aria-hidden="true" />
                <span>{item.title}</span>
              </NavLink>
            );
          })}
        </nav>
      </div>
    </aside>
  );
}

export function StaffLayout(): React.JSX.Element {
  return (
    <div className="flex min-h-screen bg-slate-100 text-slate-950">
      <StaffSidebar />
      <div className="flex min-w-0 flex-1 flex-col">
        <header className="border-b border-slate-200 bg-white">
          <div className="flex min-h-16 flex-wrap items-center justify-between gap-3 px-4 py-3 sm:px-6">
            <div>
              <p className="text-xs font-semibold uppercase tracking-wide text-cyan-700">
                Staff Workspace
              </p>
              <h1 className="text-lg font-semibold text-slate-950">Панель управления</h1>
            </div>
            <div className="flex items-center gap-3">
              <WorkspaceSwitcher />
              <ThemeToggle />
              <UserMenu />
            </div>
          </div>
        </header>
        <main className="flex-1 px-4 py-6 sm:px-6 lg:px-8">
          <Outlet />
        </main>
        <footer className="border-t border-slate-200 bg-white px-4 py-4 text-sm text-slate-500 sm:px-6">
          Панель управления организацией
        </footer>
      </div>
    </div>
  );
}
