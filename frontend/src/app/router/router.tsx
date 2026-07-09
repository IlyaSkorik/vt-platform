import { createBrowserRouter, Navigate, type RouteObject } from "react-router";
import { AppShellLayout } from "@/app/layouts/app-shell-layout";
import { AuthLayout } from "@/app/layouts/auth-layout";
import { MinimalLayout } from "@/app/layouts/minimal-layout";
import { NotFoundLayout } from "@/app/layouts/not-found-layout";
import { PublicLayout } from "@/app/layouts/public-layout";
import { RootLayout } from "@/app/layouts/root-layout";
import { ROUTES } from "@/shared/config";
import { GuestRoute, ProtectedRoute } from "./guards";
import { RouteError } from "./route-error";

/** Lazily import a page module, mapping its named export to `Component`. */
const lazyPage =
  (loader: () => Promise<Record<string, React.ComponentType>>, name: string) => async () => ({
    Component: (await loader())[name] as React.ComponentType,
  });

/**
 * Application route tree (React Router v7, data router).
 *
 * Every page is route-level code-split via `lazy` so the initial bundle stays
 * small (ARCH-001 §8.4). The tree encodes the access model AND the layout each
 * area lives in:
 *   - Public:    landing, rendered in `PublicLayout`.
 *   - Guest:     auth screens in `AuthLayout`, redirected away once authed.
 *   - Protected: app screens in the permanent `AppShellLayout`.
 *   - 404:       catch-all in the neutral `NotFoundLayout`.
 *
 * App section pages that a feature has not yet shipped fall back to a shared
 * "coming soon" placeholder so every sidebar link resolves inside the shell.
 */
const routes: RouteObject[] = [
  {
    element: <RootLayout />,
    errorElement: <RouteError />,
    children: [
      // Public.
      {
        element: <PublicLayout />,
        children: [{ index: true, lazy: lazyPage(() => import("@/pages/home"), "HomePage") }],
      },

      // Public focused flows.
      {
        element: <MinimalLayout />,
        children: [
          {
            path: ROUTES.staffInvitation.slice(1),
            lazy: lazyPage(() => import("@/pages/staff-invitation"), "StaffInvitationPage"),
          },
        ],
      },

      // Guest-only (auth).
      {
        element: <GuestRoute />,
        children: [
          {
            element: <AuthLayout />,
            children: [
              {
                path: ROUTES.login.slice(1),
                lazy: lazyPage(() => import("@/pages/login"), "LoginPage"),
              },
              {
                path: ROUTES.register.slice(1),
                lazy: lazyPage(() => import("@/pages/register"), "RegisterPage"),
              },
              {
                path: ROUTES.forgotPassword.slice(1),
                lazy: lazyPage(() => import("@/pages/forgot-password"), "ForgotPasswordPage"),
              },
              {
                path: ROUTES.resetPassword.slice(1),
                lazy: lazyPage(() => import("@/pages/reset-password"), "ResetPasswordPage"),
              },
              {
                path: ROUTES.verifyEmail.slice(1),
                lazy: lazyPage(() => import("@/pages/verify-email"), "VerifyEmailPage"),
              },
            ],
          },
        ],
      },

      // Session / authorization outcome screens — reachable regardless of auth
      // state (a dropped session or a 403 must always render), in the auth
      // layout for a consistent, chrome-light presentation.
      {
        element: <AuthLayout />,
        children: [
          {
            path: ROUTES.sessionExpired.slice(1),
            lazy: lazyPage(() => import("@/pages/session-expired"), "SessionExpiredPage"),
          },
          {
            path: ROUTES.unauthorized.slice(1),
            lazy: lazyPage(() => import("@/pages/unauthorized"), "UnauthorizedPage"),
          },
        ],
      },

      // Protected — the permanent Application Shell.
      {
        element: <ProtectedRoute />,
        children: [
          {
            element: <AppShellLayout />,
            children: [
              {
                path: ROUTES.cabinet.slice(1),
                lazy: lazyPage(() => import("@/pages/dashboard"), "DashboardPage"),
              },
              // Legacy /dashboard → /cabinet (the canonical authenticated home).
              {
                path: ROUTES.dashboard.slice(1),
                element: <Navigate to={ROUTES.cabinet} replace />,
              },
              {
                path: ROUTES.participants.slice(1),
                lazy: lazyPage(() => import("@/pages/participants"), "ParticipantsPage"),
              },
              {
                path: ROUTES.profile.slice(1),
                lazy: lazyPage(() => import("@/pages/profile"), "ProfilePage"),
              },
              // Sections whose features have not shipped yet — placeholder page.
              ...[
                ROUTES.competitions,
                ROUTES.applications,
                ROUTES.performances,
                ROUTES.judging,
                ROUTES.results,
                ROUTES.finance,
                ROUTES.analytics,
                ROUTES.settings,
                ROUTES.staff,
              ].map((path) => ({
                path: path.slice(1),
                lazy: lazyPage(() => import("@/pages/placeholder"), "PlaceholderPage"),
              })),
            ],
          },
        ],
      },

      // 404 catch-all.
      {
        element: <NotFoundLayout />,
        children: [
          { path: "*", lazy: lazyPage(() => import("@/pages/not-found"), "NotFoundPage") },
        ],
      },
    ],
  },
];

export const router = createBrowserRouter(routes);
