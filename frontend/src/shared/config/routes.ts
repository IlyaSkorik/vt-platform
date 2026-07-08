/**
 * Centralized route path registry.
 *
 * Every navigable path in the app is declared here so links, guards and the
 * router never drift apart via stringly-typed paths scattered across the code.
 */
export const ROUTES = {
  home: "/",
  login: "/login",
  register: "/register",
  forgotPassword: "/forgot-password",
  verifyEmail: "/verify-email",
  dashboard: "/dashboard",
  profile: "/profile",
  participants: "/participants",
  notFound: "/404",
} as const;

export type RoutePath = (typeof ROUTES)[keyof typeof ROUTES];
