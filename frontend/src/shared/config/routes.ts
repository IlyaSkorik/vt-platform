/**
 * Centralized route path registry.
 *
 * Every navigable path in the app is declared here so links, guards and the
 * router never drift apart via stringly-typed paths scattered across the code.
 *
 * Paths are grouped by access model:
 *   - Public / guest: landing and authentication screens.
 *   - App (protected): the sections rendered inside the Application Shell.
 *
 * The app section paths back the navigation model (`./navigation`). They are
 * declared up front so the shell can link to every section, even before the
 * owning feature ships its page (unmatched routes fall through to 404).
 */
export const ROUTES = {
  // Public / guest.
  home: "/",
  login: "/login",
  register: "/register",
  forgotPassword: "/forgot-password",
  resetPassword: "/reset-password",
  verifyEmail: "/verify-email",

  // Session / authorization outcome screens (guest-accessible).
  sessionExpired: "/session-expired",
  unauthorized: "/403",

  // App shell sections (protected).
  // The personal cabinet is the authenticated home for EVERY user (participants,
  // parents, teachers). Login always lands here — never on a staff-only surface.
  cabinet: "/cabinet",
  dashboard: "/dashboard",
  participants: "/participants",
  competitions: "/competitions",
  applications: "/applications",
  performances: "/performances",
  judging: "/judging",
  results: "/results",
  finance: "/finance",
  analytics: "/analytics",
  settings: "/settings",
  profile: "/profile",

  notFound: "/404",
} as const;

export type RoutePath = (typeof ROUTES)[keyof typeof ROUTES];
