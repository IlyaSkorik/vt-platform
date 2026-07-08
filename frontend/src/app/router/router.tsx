import { createBrowserRouter, type RouteObject } from "react-router";
import { AuthLayout } from "@/app/layouts/auth-layout";
import { DashboardLayout } from "@/app/layouts/dashboard-layout";
import { RootLayout } from "@/app/layouts/root-layout";
import { ROUTES } from "@/shared/config";
import { GuestRoute, ProtectedRoute } from "./guards";
import { RouteError } from "./route-error";

/**
 * Application route tree (React Router v7, data router).
 *
 * Every page is route-level code-split via `lazy` so the initial bundle stays
 * small and each route loads on demand (ARCH-001 §8.4). The tree encodes the
 * access model structurally:
 *   - Public:    "/" landing.
 *   - Guest:     auth screens, redirected away once authenticated.
 *   - Protected: app screens, redirected to login when unauthenticated.
 *
 * Pages contain layout placeholders only — no business UI (bootstrap scope).
 */
const routes: RouteObject[] = [
  {
    element: <RootLayout />,
    errorElement: <RouteError />,
    children: [
      {
        index: true,
        lazy: async () => ({ Component: (await import("@/pages/home")).HomePage }),
      },
      {
        element: <GuestRoute />,
        children: [
          {
            element: <AuthLayout />,
            children: [
              {
                path: ROUTES.login.slice(1),
                lazy: async () => ({ Component: (await import("@/pages/login")).LoginPage }),
              },
              {
                path: ROUTES.register.slice(1),
                lazy: async () => ({
                  Component: (await import("@/pages/register")).RegisterPage,
                }),
              },
              {
                path: ROUTES.forgotPassword.slice(1),
                lazy: async () => ({
                  Component: (await import("@/pages/forgot-password")).ForgotPasswordPage,
                }),
              },
              {
                path: ROUTES.verifyEmail.slice(1),
                lazy: async () => ({
                  Component: (await import("@/pages/verify-email")).VerifyEmailPage,
                }),
              },
            ],
          },
        ],
      },
      {
        element: <ProtectedRoute />,
        children: [
          {
            element: <DashboardLayout />,
            children: [
              {
                path: ROUTES.dashboard.slice(1),
                lazy: async () => ({
                  Component: (await import("@/pages/dashboard")).DashboardPage,
                }),
              },
              {
                path: ROUTES.profile.slice(1),
                lazy: async () => ({ Component: (await import("@/pages/profile")).ProfilePage }),
              },
              {
                path: ROUTES.participants.slice(1),
                lazy: async () => ({
                  Component: (await import("@/pages/participants")).ParticipantsPage,
                }),
              },
            ],
          },
        ],
      },
      {
        path: "*",
        lazy: async () => ({ Component: (await import("@/pages/not-found")).NotFoundPage }),
      },
    ],
  },
];

export const router = createBrowserRouter(routes);
