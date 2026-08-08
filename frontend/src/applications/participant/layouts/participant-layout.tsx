import { Menu, PanelLeftClose, PanelLeftOpen } from "lucide-react";
import { useState } from "react";
import { Link, NavLink, Outlet, useLocation } from "react-router";
import { SiteFooter } from "@/app/layouts/site-footer";
import { ThemeToggle } from "@/app/layouts/theme-toggle";
import { UserMenu } from "@/app/layouts/user-menu";
import { useAuth } from "@/app/providers";
import {
  PARTICIPANT_NAVIGATION,
  type ParticipantNavItem,
} from "@/applications/participant/navigation";
import { WorkspaceSwitcher } from "@/applications/workspace-switcher";
import { NotificationBell } from "@/features/notifications";
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

const SKIP_TARGET_ID = "participant-main";

function findParticipantItem(pathname: string): ParticipantNavItem {
  const fallback = PARTICIPANT_NAVIGATION[0];
  if (fallback == null) {
    throw new Error("Participant navigation is empty");
  }

  return (
    PARTICIPANT_NAVIGATION.find(
      (item) => pathname === item.path || pathname.startsWith(`${item.path}/`),
    ) ?? fallback
  );
}

function ParticipantNav({
  collapsed,
  onNavigate,
}: {
  collapsed: boolean;
  onNavigate?: () => void;
}): React.JSX.Element {
  return (
    <nav aria-label="Навигация личного кабинета" className="flex flex-col gap-1">
      {PARTICIPANT_NAVIGATION.map((item) => {
        const Icon = item.icon;
        return (
          <NavLink
            key={item.path}
            to={item.path}
            end={item.path === ROUTES.cabinet}
            onClick={onNavigate}
            className={({ isActive }) =>
              cn(
                "flex min-h-10 items-center gap-3 rounded-md px-3 py-2 text-sm font-medium outline-none transition-colors focus-visible:ring-2 focus-visible:ring-ring",
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

function ParticipantBreadcrumbs(): React.JSX.Element {
  const { pathname } = useLocation();
  const item = findParticipantItem(pathname);

  return (
    <nav aria-label="Хлебные крошки личного кабинета" className="min-w-0">
      <ol className="flex items-center gap-1.5 text-sm">
        <li>
          <Link
            to={ROUTES.cabinet}
            className="text-muted-foreground outline-none hover:text-foreground focus-visible:ring-2 focus-visible:ring-ring"
          >
            Личный кабинет
          </Link>
        </li>
        {item.path !== ROUTES.cabinet && (
          <>
            <li aria-hidden="true" className="text-muted-foreground">
              /
            </li>
            <li className="min-w-0">
              <span aria-current="page" className="block truncate font-medium text-foreground">
                {item.title}
              </span>
            </li>
          </>
        )}
      </ol>
    </nav>
  );
}

function ParticipantSidebar({
  collapsed,
  onToggleCollapsed,
}: {
  collapsed: boolean;
  onToggleCollapsed: () => void;
}): React.JSX.Element {
  return (
    <aside
      aria-label="Боковая навигация личного кабинета"
      data-collapsed={collapsed}
      className={cn(
        "sticky top-0 hidden h-svh shrink-0 flex-col border-border border-r bg-card transition-[width] duration-normal ease-standard md:flex",
        collapsed ? "w-16" : "w-64",
      )}
    >
      <div
        className={cn(
          "flex h-16 shrink-0 items-center border-border border-b",
          collapsed ? "justify-center px-2" : "px-4",
        )}
      >
        <Link
          to={ROUTES.cabinet}
          className="flex items-center gap-2 rounded-md font-semibold text-foreground outline-none focus-visible:ring-2 focus-visible:ring-ring"
        >
          <BrandMark className="size-8 rounded-md" />
          {!collapsed && (
            <span className="flex min-w-0 flex-col">
              <span className="truncate">{APP_NAME}</span>
              <span className="truncate font-normal text-muted-foreground text-xs">
                Личный кабинет
              </span>
            </span>
          )}
        </Link>
      </div>
      <div className="flex-1 overflow-y-auto p-2">
        <ParticipantNav collapsed={collapsed} />
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

export function ParticipantLoadingState(): React.JSX.Element {
  return (
    <div role="status" className="space-y-4" aria-label="Загрузка личного кабинета">
      <Skeleton className="h-9 w-56" />
      <Skeleton className="h-24 w-full" />
      <div className="grid gap-4 md:grid-cols-3">
        <Skeleton className="h-32" />
        <Skeleton className="h-32" />
        <Skeleton className="h-32" />
      </div>
    </div>
  );
}

export function ParticipantErrorState(): React.JSX.Element {
  return (
    <EmptyState
      title="Не удалось открыть личный кабинет"
      description="Обновите страницу или вернитесь в кабинет позже."
      action={
        <Button asChild variant="outline">
          <Link to={ROUTES.cabinet}>Вернуться на главную</Link>
        </Button>
      }
    />
  );
}

export function ParticipantLayout(): React.JSX.Element {
  const { staffMembership, isPlatformAdmin } = useAuth();
  // The cabinet is the one shell every account gets, so the switcher appears here
  // only when there is somewhere to switch *to*. Staff membership is not that
  // condition on its own: platform access is granted by command, to an account that
  // often belongs to no organization at all, and gating on membership alone left
  // those operators with no way into `/platform` but typing the URL.
  const hasOtherWorkspace = staffMembership != null || isPlatformAdmin;
  const [collapsed, setCollapsed] = useState(false);
  const [mobileOpen, setMobileOpen] = useState(false);

  return (
    <div className="flex min-h-svh bg-background text-foreground">
      <a
        href={`#${SKIP_TARGET_ID}`}
        className="sr-only rounded-md bg-primary px-4 py-2 text-primary-foreground focus:not-sr-only focus:absolute focus:top-4 focus:left-4 focus:z-[var(--z-toast)]"
      >
        Перейти к содержимому
      </a>
      <ParticipantSidebar
        collapsed={collapsed}
        onToggleCollapsed={() => setCollapsed((value) => !value)}
      />
      <Drawer open={mobileOpen} onOpenChange={setMobileOpen}>
        <DrawerContent side="left" className="w-72 max-w-[82vw] gap-0 p-0">
          <div className="flex h-16 items-center border-border border-b px-4">
            <DrawerTitle className="text-base">{APP_NAME}</DrawerTitle>
            <DrawerDescription className="sr-only">Навигация личного кабинета</DrawerDescription>
          </div>
          <div className="p-2">
            <ParticipantNav collapsed={false} onNavigate={() => setMobileOpen(false)} />
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
          <div className="min-w-0 flex-1">
            <ParticipantBreadcrumbs />
          </div>
          <div className="flex shrink-0 items-center gap-1">
            {hasOtherWorkspace ? <WorkspaceSwitcher className="hidden xl:flex" /> : null}
            <NotificationBell />
            <ThemeToggle />
            <UserMenu />
          </div>
        </header>
        {hasOtherWorkspace ? (
          <div className="bg-muted/20 px-4 py-2 xl:hidden">
            <WorkspaceSwitcher />
          </div>
        ) : null}
        {/* See the staff shell: content wider than this column must be clipped here, or it
            scrolls the whole document and takes the chrome with it. */}
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
