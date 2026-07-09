import { Outlet } from "react-router";
import { NAVIGATION, ROUTES } from "@/shared/config";
import { AppShell } from "@/widgets/app-shell";
import { ThemeToggle } from "./theme-toggle";
import { UserMenu } from "./user-menu";

/**
 * Legacy shell adapter retained for old app-shell consumers. Staff navigation
 * lives only in StaffLayout; this layout never branches on CurrentUser.
 */
export function AppShellLayout(): React.JSX.Element {
  return (
    <AppShell
      navigation={NAVIGATION}
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
