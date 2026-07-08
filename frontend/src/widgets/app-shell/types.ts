import type * as React from "react";
import type { NavModel } from "@/shared/config";

/**
 * Props for {@link AppShell} — the permanent authenticated layout.
 *
 * The shell is intentionally generic and app-agnostic: it renders whatever
 * navigation model it is given and exposes SLOTS for app-level concerns
 * (theme switch, user menu) that live above the widgets layer. This is what
 * lets every future page render inside the shell without the shell ever
 * importing from `app/` or a feature — the FSD dependency rule holds.
 */
export interface AppShellProps {
  /** Navigation model rendered in the sidebar. Defaults to the platform nav. */
  navigation?: NavModel;
  /** Page content — the routed `<Outlet />` in the app. */
  children: React.ReactNode;

  /** Brand link target (logo click). */
  homeHref?: string;

  /**
   * App-injected header controls, right-aligned (theme switch, user menu…).
   * Kept as a slot so the widget stays free of app/auth/theme dependencies.
   */
  headerActions?: React.ReactNode;

  /** Optional footer content; a minimal placeholder renders when omitted. */
  footer?: React.ReactNode;
}

/** State shared across the shell (sidebar collapse + mobile drawer). */
export interface ShellState {
  /** Desktop/tablet: sidebar collapsed to an icon rail. */
  collapsed: boolean;
  toggleCollapsed: () => void;
  setCollapsed: (value: boolean) => void;

  /** Mobile: navigation drawer open. */
  mobileOpen: boolean;
  setMobileOpen: (value: boolean) => void;

  /** True below the `md` breakpoint — navigation moves into a drawer. */
  isMobile: boolean;
}
