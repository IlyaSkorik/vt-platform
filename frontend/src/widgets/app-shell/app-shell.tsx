import { Link } from "react-router";
import { APP_NAME, NAVIGATION } from "@/shared/config";
import {
  Drawer,
  DrawerContent,
  DrawerDescription,
  DrawerTitle,
  TooltipProvider,
} from "@/shared/ui";
import { Header } from "./header";
import { ShellProvider, useShell } from "./shell-context";
import { Sidebar } from "./sidebar";
import { SidebarNav } from "./sidebar-nav";
import type { AppShellProps } from "./types";

const SKIP_TARGET_ID = "app-shell-main";

function ShellFrame({
  navigation,
  children,
  homeHref,
  headerActions,
  footer,
}: Required<Pick<AppShellProps, "navigation" | "homeHref">> &
  Pick<AppShellProps, "children" | "headerActions" | "footer">): React.JSX.Element {
  const { collapsed, toggleCollapsed, isMobile, mobileOpen, setMobileOpen } = useShell();

  return (
    <div className="flex min-h-svh w-full bg-background">
      <a
        href={`#${SKIP_TARGET_ID}`}
        className="sr-only rounded-md bg-primary px-4 py-2 text-primary-foreground focus:not-sr-only focus:absolute focus:top-4 focus:left-4 focus:z-[var(--z-toast)]"
      >
        Перейти к содержимому
      </a>

      {/* Desktop / tablet sidebar. */}
      <Sidebar
        navigation={navigation}
        collapsed={collapsed}
        onToggleCollapsed={toggleCollapsed}
        homeHref={homeHref}
      />

      {/* Mobile navigation drawer. */}
      <Drawer open={mobileOpen} onOpenChange={setMobileOpen}>
        <DrawerContent side="left" className="w-72 max-w-[80vw] gap-0 p-0">
          <div className="flex h-16 shrink-0 items-center border-border border-b px-4">
            <Link
              to={homeHref}
              onClick={() => setMobileOpen(false)}
              className="flex items-center gap-2 font-semibold text-foreground text-lg tracking-tight"
            >
              <span
                aria-hidden="true"
                className="flex size-8 items-center justify-center rounded-md bg-primary font-bold text-primary-foreground text-sm"
              >
                ВТ
              </span>
              <DrawerTitle className="text-lg">{APP_NAME}</DrawerTitle>
            </Link>
          </div>
          <DrawerDescription className="sr-only">
            Основная навигация по разделам платформы.
          </DrawerDescription>
          <div className="flex-1 overflow-y-auto p-2">
            <SidebarNav
              navigation={navigation}
              collapsed={false}
              onNavigate={() => setMobileOpen(false)}
            />
          </div>
        </DrawerContent>
      </Drawer>

      <div className="flex min-w-0 flex-1 flex-col">
        <Header
          showMenuButton={isMobile}
          onOpenMenu={() => setMobileOpen(true)}
          actions={headerActions}
        />

        <main id={SKIP_TARGET_ID} tabIndex={-1} className="flex-1 p-4 outline-none md:p-6 lg:p-8">
          {children}
        </main>

        <footer className="shrink-0 border-border border-t px-4 py-4 text-muted-foreground text-xs md:px-8">
          {footer ?? (
            <span>
              © {new Date().getFullYear()} {APP_NAME}
            </span>
          )}
        </footer>
      </div>
    </div>
  );
}

/**
 * AppShell — the permanent authenticated layout of the platform.
 *
 * Every authenticated page renders inside this shell: a collapsible sidebar
 * (drawer on mobile), a sticky header with breadcrumbs + search/notifications
 * placeholders, a main content region, and a footer. It composes ARIA
 * landmarks (`complementary`, `banner`, `main`, `contentinfo`) and a skip link
 * for keyboard users (WCAG 2.1 AA).
 *
 * The shell is app-agnostic and data-driven: it renders the given navigation
 * model and takes app-level controls (theme, user menu) through the
 * `headerActions` SLOT, so it never imports from `app/` or a feature. New
 * pages drop into `children` without ever modifying the shell.
 */
export function AppShell({
  navigation = NAVIGATION,
  children,
  homeHref = "/",
  headerActions,
  footer,
}: AppShellProps): React.JSX.Element {
  return (
    <TooltipProvider>
      <ShellProvider>
        <ShellFrame
          navigation={navigation}
          homeHref={homeHref}
          headerActions={headerActions}
          footer={footer}
        >
          {children}
        </ShellFrame>
      </ShellProvider>
    </TooltipProvider>
  );
}
