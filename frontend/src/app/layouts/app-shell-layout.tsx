import { Outlet } from "react-router";
import { useAuth } from "@/app/providers";
import { getNavigation, ROUTES } from "@/shared/config";
import { AppShell } from "@/widgets/app-shell";
import { ThemeToggle } from "./theme-toggle";
import { UserMenu } from "./user-menu";

/**
 * AppShellLayout — the route element wrapping every authenticated page in the
 * permanent {@link AppShell}.
 *
 * It is a thin adapter: it injects the app-level header controls (theme
 * switch, user menu) into the shell's `headerActions` slot and renders the
 * routed page through `<Outlet />`. All layout, navigation and responsive
 * behaviour lives in the shell widget, so pages never touch chrome.
 */
export function AppShellLayout(): React.JSX.Element {
  const { staffMembership } = useAuth();

  return (
    <AppShell
      navigation={getNavigation({ hasStaffAccess: staffMembership != null })}
      homeHref={ROUTES.cabinet}
      headerActions={
        <>
          <ThemeToggle />
          <UserMenu />
        </>
      }
    >
      <Outlet />
    </AppShell>
  );
}
