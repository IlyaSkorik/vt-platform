import { createContext, use, useCallback, useEffect, useMemo, useState } from "react";
import { SIDEBAR_STORAGE_KEY } from "@/shared/constants";
import { useMediaQuery } from "@/shared/hooks";
import type { ShellState } from "./types";

const ShellContext = createContext<ShellState | null>(null);

function readStoredCollapsed(): boolean {
  if (typeof window === "undefined") {
    return false;
  }
  return window.localStorage.getItem(SIDEBAR_STORAGE_KEY) === "true";
}

/**
 * Shell state provider — owns sidebar collapse (desktop/tablet) and the mobile
 * navigation drawer.
 *
 * The collapsed preference is persisted so the layout is stable across visits.
 * Below the `md` breakpoint the sidebar is replaced by a drawer; the drawer is
 * auto-dismissed when the viewport grows back to desktop so state never gets
 * stuck open behind a now-visible sidebar.
 */
export function ShellProvider({ children }: { children: React.ReactNode }): React.JSX.Element {
  const isMobile = useMediaQuery("(max-width: 767px)");
  const [collapsed, setCollapsedState] = useState<boolean>(readStoredCollapsed);
  const [mobileOpen, setMobileOpen] = useState<boolean>(false);

  const setCollapsed = useCallback((value: boolean) => {
    setCollapsedState(value);
    if (typeof window !== "undefined") {
      window.localStorage.setItem(SIDEBAR_STORAGE_KEY, String(value));
    }
  }, []);

  const toggleCollapsed = useCallback(() => {
    setCollapsed(!collapsed);
  }, [collapsed, setCollapsed]);

  // Close the mobile drawer once we leave the mobile breakpoint.
  useEffect(() => {
    if (!isMobile && mobileOpen) {
      setMobileOpen(false);
    }
  }, [isMobile, mobileOpen]);

  const value = useMemo<ShellState>(
    () => ({
      collapsed,
      toggleCollapsed,
      setCollapsed,
      mobileOpen,
      setMobileOpen,
      isMobile,
    }),
    [collapsed, toggleCollapsed, setCollapsed, mobileOpen, isMobile],
  );

  return <ShellContext value={value}>{children}</ShellContext>;
}

/** Access the shell state. Must be used within {@link ShellProvider}. */
export function useShell(): ShellState {
  const context = use(ShellContext);
  if (!context) {
    throw new Error("useShell must be used within a ShellProvider.");
  }
  return context;
}
