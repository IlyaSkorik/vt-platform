/**
 * Application-wide constants (magic values live here, never inline).
 */

/** localStorage key for the persisted colour theme (kept in sync with index.html). */
export const THEME_STORAGE_KEY = "vt-theme";

/** localStorage key for the persisted app-shell sidebar collapsed state. */
export const SIDEBAR_STORAGE_KEY = "vt-sidebar-collapsed";

/** Tailwind breakpoints (px) mirrored for use in `useMediaQuery` and JS logic. */
export const BREAKPOINTS = {
  sm: 640,
  md: 768,
  lg: 1024,
  xl: 1280,
  "2xl": 1536,
} as const;

export type Breakpoint = keyof typeof BREAKPOINTS;
