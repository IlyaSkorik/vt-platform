import { Menu, PanelLeftClose, PanelLeftOpen, Search } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import { Link, NavLink, Outlet, useLocation } from "react-router";
import { SiteFooter } from "@/app/layouts/site-footer";
import { ThemeToggle } from "@/app/layouts/theme-toggle";
import { UserMenu } from "@/app/layouts/user-menu";
import {
  isStaffWorkspaceRoute,
  STAFF_NAVIGATION,
  type StaffNavItem,
} from "@/applications/staff/navigation";
import { WorkspaceSwitcher } from "@/applications/workspace-switcher";
import { APP_NAME, ROUTES } from "@/shared/config";
import { cn } from "@/shared/lib";
import {
  BrandMark,
  Button,
  Drawer,
  DrawerContent,
  DrawerDescription,
  DrawerTitle,
  EmptyState,
  IconButton,
  Skeleton,
} from "@/shared/ui";

const SKIP_TARGET_ID = "staff-main";

function findStaffItem(pathname: string): StaffNavItem {
  const fallback = STAFF_NAVIGATION[0];
  if (fallback == null) {
    throw new Error("Staff navigation is empty");
  }

  return (
    STAFF_NAVIGATION.find(
      (item) => pathname === item.path || pathname.startsWith(`${item.path}/`),
    ) ?? fallback
  );
}

function StaffNav({
  collapsed,
  onNavigate,
}: {
  collapsed: boolean;
  onNavigate?: () => void;
}): React.JSX.Element {
  return (
    <nav aria-label="Навигация панели управления" className="flex flex-col gap-1">
      {STAFF_NAVIGATION.map((item) => {
        const Icon = item.icon;
        return (
          <NavLink
            key={item.path}
            to={item.path}
            end={item.path === ROUTES.staff}
            onClick={onNavigate}
            className={({ isActive }) =>
              cn(
                "flex min-h-9 items-center gap-3 rounded-md px-3 py-2 text-sm font-medium outline-none transition-colors focus-visible:ring-2 focus-visible:ring-ring",
                collapsed && "justify-center px-2",
                isActive
                  ? "bg-primary/10 text-primary"
                  : "text-muted-foreground hover:bg-accent hover:text-accent-foreground",
              )
            }
          >
            <Icon className="size-4 shrink-0" aria-hidden="true" />
            {!collapsed && <span className="truncate">{item.title}</span>}
          </NavLink>
        );
      })}
    </nav>
  );
}

function StaffBreadcrumbs(): React.JSX.Element {
  const { pathname } = useLocation();
  const item = findStaffItem(pathname);
  const competitionMatch = pathname.match(/^\/staff\/competitions\/([^/]+)/);
  const competitionId = competitionMatch?.[1];
  const isCompetitionWorkspace =
    competitionId != null && competitionId !== "new" && item.path === ROUTES.staffCompetitions;

  return (
    // No "Панель управления" root: the sidebar already names the workspace two
    // columns to the left, and repeating it here bought nothing but a second copy
    // of the same words. The trail starts at the page you are actually on.
    <nav aria-label="Хлебные крошки панели управления" className="min-w-0">
      <ol className="flex items-center gap-1.5 text-sm">
        {item.path !== ROUTES.staff && (
          <li className="min-w-0">
            {isCompetitionWorkspace ? (
              <Link
                to={ROUTES.staffCompetitions}
                className="block truncate text-muted-foreground outline-none hover:text-foreground focus-visible:ring-2 focus-visible:ring-ring"
              >
                {item.title}
              </Link>
            ) : (
              <span aria-current="page" className="block truncate font-medium text-foreground">
                {item.title}
              </span>
            )}
          </li>
        )}
        {isCompetitionWorkspace ? (
          <>
            <li aria-hidden="true" className="text-muted-foreground">
              /
            </li>
            <li className="min-w-0">
              <span aria-current="page" className="block truncate font-medium text-foreground">
                Рабочее пространство
              </span>
            </li>
          </>
        ) : null}
        {pathname === ROUTES.staffCompetitionsNew ? (
          <>
            <li aria-hidden="true" className="text-muted-foreground">
              /
            </li>
            <li className="min-w-0">
              <span aria-current="page" className="block truncate font-medium text-foreground">
                Создание
              </span>
            </li>
          </>
        ) : null}
      </ol>
    </nav>
  );
}

function StaffSidebar({
  collapsed,
  onToggleCollapsed,
}: {
  collapsed: boolean;
  onToggleCollapsed: () => void;
}): React.JSX.Element {
  return (
    <aside
      aria-label="Боковая навигация панели управления"
      data-collapsed={collapsed}
      className={cn(
        "sticky top-0 hidden h-svh shrink-0 flex-col border-border border-r bg-card transition-[width] duration-normal ease-standard md:flex",
        collapsed ? "w-16" : "w-72",
      )}
    >
      <div
        className={cn(
          "flex h-16 shrink-0 items-center border-border border-b",
          collapsed ? "justify-center px-2" : "px-4",
        )}
      >
        <Link
          to={ROUTES.staff}
          className="flex items-center gap-2 rounded-md font-semibold text-foreground outline-none focus-visible:ring-2 focus-visible:ring-ring"
        >
          <BrandMark className="size-8 rounded-md" />
          {!collapsed && (
            <span className="flex min-w-0 flex-col">
              <span className="truncate">{APP_NAME}</span>
              <span className="truncate font-normal text-muted-foreground text-xs">
                Панель управления
              </span>
            </span>
          )}
        </Link>
      </div>
      <div className="flex-1 overflow-y-auto p-2">
        <StaffNav collapsed={collapsed} />
      </div>
      <div
        className={cn(
          "flex border-border border-t p-2",
          collapsed ? "justify-center" : "justify-end",
        )}
      >
        <IconButton
          variant="ghost"
          size="sm"
          onClick={onToggleCollapsed}
          aria-pressed={collapsed}
          aria-label={collapsed ? "Развернуть меню" : "Свернуть меню"}
          icon={
            collapsed ? <PanelLeftOpen aria-hidden="true" /> : <PanelLeftClose aria-hidden="true" />
          }
        />
      </div>
    </aside>
  );
}

function SearchPlaceholder(): React.JSX.Element {
  return (
    <button
      type="button"
      className="hidden h-9 w-full max-w-xs items-center gap-2 rounded-md border border-border bg-background px-3 text-muted-foreground text-sm outline-none transition-colors hover:bg-accent focus-visible:ring-2 focus-visible:ring-ring lg:flex"
    >
      <Search className="size-4 shrink-0" aria-hidden="true" />
      <span className="flex-1 text-left">Поиск…</span>
      <kbd className="rounded border border-border bg-muted px-1.5 font-mono text-[0.625rem] text-muted-foreground">
        ⌘K
      </kbd>
    </button>
  );
}

export function StaffLoadingState(): React.JSX.Element {
  return (
    <div role="status" className="space-y-4" aria-label="Загрузка панели управления">
      <div className="grid gap-4 md:grid-cols-4">
        <Skeleton className="h-24" />
        <Skeleton className="h-24" />
        <Skeleton className="h-24" />
        <Skeleton className="h-24" />
      </div>
      <Skeleton className="h-72 w-full" />
    </div>
  );
}

export function StaffErrorState(): React.JSX.Element {
  return (
    <EmptyState
      title="Не удалось открыть панель управления"
      description="Проверьте доступ к рабочему пространству и повторите попытку."
      action={
        <Button asChild variant="outline">
          <Link to={ROUTES.staff}>Вернуться в Dashboard</Link>
        </Button>
      }
    />
  );
}

export function StaffLayout(): React.JSX.Element {
  const { pathname } = useLocation();
  const workspace = isStaffWorkspaceRoute(pathname);
  const [collapsed, setCollapsed] = useState(workspace);
  const [mobileOpen, setMobileOpen] = useState(false);

  // Crossing into a workspace folds the navigation away; leaving unfolds it again.
  // Only the crossing does this, so a staffer who opens the menu inside a workspace
  // keeps it open while they move around in there.
  const wasWorkspace = useRef(workspace);
  useEffect(() => {
    if (workspace === wasWorkspace.current) {
      return;
    }
    wasWorkspace.current = workspace;
    setCollapsed(workspace);
  }, [workspace]);

  return (
    <div className="flex min-h-svh bg-background text-foreground">
      <a
        href={`#${SKIP_TARGET_ID}`}
        className="sr-only rounded-md bg-primary px-4 py-2 text-primary-foreground focus:not-sr-only focus:absolute focus:top-4 focus:left-4 focus:z-[var(--z-toast)]"
      >
        Перейти к содержимому
      </a>
      <StaffSidebar
        collapsed={collapsed}
        onToggleCollapsed={() => setCollapsed((value) => !value)}
      />
      <Drawer open={mobileOpen} onOpenChange={setMobileOpen}>
        <DrawerContent side="left" className="w-80 max-w-[86vw] gap-0 p-0">
          <div className="flex h-16 items-center border-border border-b px-4">
            <DrawerTitle className="text-base">{APP_NAME}</DrawerTitle>
            <DrawerDescription className="sr-only">Навигация панели управления</DrawerDescription>
          </div>
          <div className="p-2">
            <StaffNav collapsed={false} onNavigate={() => setMobileOpen(false)} />
          </div>
        </DrawerContent>
      </Drawer>
      <div className="flex min-w-0 flex-1 flex-col">
        <header className="sticky top-0 z-[var(--z-sticky)] flex min-h-16 items-center gap-3 border-border border-b bg-background/95 px-4 backdrop-blur supports-[backdrop-filter]:bg-background/80">
          <IconButton
            variant="ghost"
            size="sm"
            className="md:hidden"
            onClick={() => setMobileOpen(true)}
            aria-label="Открыть меню"
            icon={<Menu aria-hidden="true" />}
          />
          <div className="flex min-w-0 flex-1 items-center gap-4">
            <StaffBreadcrumbs />
            <div className="ml-auto hidden flex-1 justify-end lg:flex">
              <SearchPlaceholder />
            </div>
          </div>
          <div className="flex shrink-0 items-center gap-1">
            <WorkspaceSwitcher className="hidden xl:flex" />
            <ThemeToggle />
            <UserMenu />
          </div>
        </header>
        <div className="bg-background px-4 py-2 xl:hidden">
          <WorkspaceSwitcher />
        </div>
        {/* `overflow-x-clip`: a page can be wider than this column - a table, a preview, a
            long unbreakable string - and a flex item's width cannot be pushed on the cross
            axis, so the excess would spill out and scroll the *document* instead, dragging
            the sidebar and the sticky header sideways with it. Clipping keeps that contained;
            anything legitimately wide scrolls in its own container. `clip` rather than
            `hidden` because `hidden` would make this a scroll container and break `sticky`. */}
        <main
          id={SKIP_TARGET_ID}
          tabIndex={-1}
          className="min-w-0 flex-1 overflow-x-clip p-4 outline-none md:p-6 lg:p-8"
        >
          <Outlet />
        </main>
        <SiteFooter />
      </div>
    </div>
  );
}
