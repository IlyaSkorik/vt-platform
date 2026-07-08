import { createContext, use, useCallback, useEffect, useMemo, useState } from "react";
import { THEME_STORAGE_KEY } from "@/shared/constants";

export type Theme = "light" | "dark" | "system";
export type ResolvedTheme = "light" | "dark";

interface ThemeContextValue {
  /** The user's selected preference (may be "system"). */
  theme: Theme;
  /** The concrete theme currently applied to the document. */
  resolvedTheme: ResolvedTheme;
  /** Update and persist the preference. */
  setTheme: (theme: Theme) => void;
  /** Convenience toggle between light and dark. */
  toggleTheme: () => void;
}

const ThemeContext = createContext<ThemeContextValue | null>(null);

function readStoredTheme(): Theme {
  if (typeof window === "undefined") {
    return "system";
  }
  const stored = window.localStorage.getItem(THEME_STORAGE_KEY);
  return stored === "light" || stored === "dark" || stored === "system" ? stored : "system";
}

function systemTheme(): ResolvedTheme {
  if (typeof window === "undefined" || !window.matchMedia) {
    return "light";
  }
  return window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light";
}

/**
 * Theme provider — owns the light/dark/system colour scheme.
 *
 * Applies the resolved theme by toggling the `.dark` class on <html> (the
 * class-based Tailwind v4 variant). The initial theme is applied pre-paint by
 * the inline script in `index.html`; this provider keeps React state in sync
 * and reacts to system changes and user toggles.
 */
export function ThemeProvider({ children }: { children: React.ReactNode }): React.JSX.Element {
  const [theme, setThemeState] = useState<Theme>(readStoredTheme);
  const [resolvedTheme, setResolvedTheme] = useState<ResolvedTheme>(() =>
    readStoredTheme() === "system" ? systemTheme() : (readStoredTheme() as ResolvedTheme),
  );

  const applyTheme = useCallback((next: Theme) => {
    const resolved = next === "system" ? systemTheme() : next;
    setResolvedTheme(resolved);
    document.documentElement.classList.toggle("dark", resolved === "dark");
  }, []);

  const setTheme = useCallback(
    (next: Theme) => {
      setThemeState(next);
      window.localStorage.setItem(THEME_STORAGE_KEY, next);
      applyTheme(next);
    },
    [applyTheme],
  );

  const toggleTheme = useCallback(() => {
    setTheme(resolvedTheme === "dark" ? "light" : "dark");
  }, [resolvedTheme, setTheme]);

  // Follow the OS preference while the user is on "system".
  useEffect(() => {
    if (theme !== "system" || !window.matchMedia) {
      return;
    }
    const media = window.matchMedia("(prefers-color-scheme: dark)");
    const listener = (): void => applyTheme("system");
    media.addEventListener("change", listener);
    return () => media.removeEventListener("change", listener);
  }, [theme, applyTheme]);

  const value = useMemo<ThemeContextValue>(
    () => ({ theme, resolvedTheme, setTheme, toggleTheme }),
    [theme, resolvedTheme, setTheme, toggleTheme],
  );

  return <ThemeContext value={value}>{children}</ThemeContext>;
}

/** Access the current theme and controls. Must be used within `ThemeProvider`. */
export function useTheme(): ThemeContextValue {
  const context = use(ThemeContext);
  if (!context) {
    throw new Error("useTheme must be used within a ThemeProvider.");
  }
  return context;
}
