import { createBrowserRouter, Navigate, type RouteObject } from "react-router";
import { AuthLayout } from "@/app/layouts/auth-layout";
import { MinimalLayout } from "@/app/layouts/minimal-layout";
import { NotFoundLayout } from "@/app/layouts/not-found-layout";
import { PublicLayout } from "@/app/layouts/public-layout";
import { RootLayout } from "@/app/layouts/root-layout";
import { ParticipantLayout } from "@/applications/participant/layouts/participant-layout";
import {
  PARTICIPANT_NAVIGATION,
  type ParticipantNavItem,
} from "@/applications/participant/navigation";
import { StaffLayout } from "@/applications/staff/layouts/staff-layout";
import { STAFF_NAVIGATION, type StaffNavItem } from "@/applications/staff/navigation";
import { ROUTES } from "@/shared/config";
import { GuestRoute, ProtectedRoute, StaffRoute } from "./guards";
import { RouteError } from "./route-error";

/** Lazily import a page module, mapping its named export to `Component`. */
const lazyPage =
  (loader: () => Promise<Record<string, React.ComponentType>>, name: string) => async () => ({
    Component: (await loader())[name] as React.ComponentType,
  });

const workspacePlaceholder =
  (item: ParticipantNavItem | StaffNavItem, tone: "participant" | "staff") => async () => {
    const { WorkspacePlaceholderPage } = await import(
      tone === "participant"
        ? "@/applications/participant/pages/placeholder"
        : "@/applications/staff/pages/placeholder"
    );
    return {
      Component: () => (
        <WorkspacePlaceholderPage
          title={item.title}
          description={item.description}
          icon={item.icon}
          tone={tone}
        />
      ),
    } satisfies { Component: React.ComponentType };
  };

const participantItem = (path: string) => {
  const item = PARTICIPANT_NAVIGATION.find((candidate) => candidate.path === path);
  if (item == null) {
    throw new Error(`Missing participant navigation for ${path}`);
  }
  return item;
};

const staffItem = (path: string) => {
  const item = STAFF_NAVIGATION.find((candidate) => candidate.path === path);
  if (item == null) {
    throw new Error(`Missing staff navigation for ${path}`);
  }
  return item;
};

/**
 * Application route tree (React Router v7, data router).
 *
 * VT Platform is composed as two independent frontend applications sharing
 * auth, CurrentUser, the API client and the design system:
 *   - `/cabinet/**` → ParticipantLayout, available to every authenticated user.
 *   - `/staff/**`   → StaffLayout, gated by CurrentUser.staffMembership.
 */
const routes: RouteObject[] = [
  {
    element: <RootLayout />,
    errorElement: <RouteError />,
    children: [
      {
        element: <PublicLayout />,
        children: [{ index: true, lazy: lazyPage(() => import("@/pages/home"), "HomePage") }],
      },
      {
        element: <MinimalLayout />,
        children: [
          {
            path: ROUTES.staffInvitation.slice(1),
            lazy: lazyPage(() => import("@/pages/staff-invitation"), "StaffInvitationPage"),
          },
        ],
      },
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
      {
        element: <ProtectedRoute />,
        children: [
          {
            element: <ParticipantLayout />,
            children: [
              {
                path: ROUTES.cabinet.slice(1),
                lazy: lazyPage(
                  () => import("@/applications/participant/pages/dashboard"),
                  "ParticipantDashboardPage",
                ),
              },
              {
                path: ROUTES.cabinetProfile.slice(1),
                lazy: lazyPage(() => import("@/pages/profile"), "ProfilePage"),
              },
              {
                path: ROUTES.cabinetParticipants.slice(1),
                lazy: lazyPage(() => import("@/pages/participants"), "ParticipantsPage"),
              },
              {
                path: ROUTES.cabinetApplications.slice(1),
                lazy: workspacePlaceholder(
                  participantItem(ROUTES.cabinetApplications),
                  "participant",
                ),
              },
              {
                path: ROUTES.cabinetCompetitions.slice(1),
                lazy: workspacePlaceholder(
                  participantItem(ROUTES.cabinetCompetitions),
                  "participant",
                ),
              },
              {
                path: ROUTES.cabinetDocuments.slice(1),
                lazy: workspacePlaceholder(participantItem(ROUTES.cabinetDocuments), "participant"),
              },
              {
                path: ROUTES.cabinetNotifications.slice(1),
                lazy: workspacePlaceholder(
                  participantItem(ROUTES.cabinetNotifications),
                  "participant",
                ),
              },
              {
                path: ROUTES.cabinetSettings.slice(1),
                lazy: workspacePlaceholder(participantItem(ROUTES.cabinetSettings), "participant"),
              },
            ],
          },
          { path: ROUTES.dashboard.slice(1), element: <Navigate to={ROUTES.cabinet} replace /> },
          {
            path: ROUTES.profile.slice(1),
            element: <Navigate to={ROUTES.cabinetProfile} replace />,
          },
          {
            path: ROUTES.participants.slice(1),
            element: <Navigate to={ROUTES.cabinetParticipants} replace />,
          },
          {
            path: ROUTES.applications.slice(1),
            element: <Navigate to={ROUTES.cabinetApplications} replace />,
          },
          {
            path: ROUTES.competitions.slice(1),
            element: <Navigate to={ROUTES.cabinetCompetitions} replace />,
          },
          {
            path: ROUTES.settings.slice(1),
            element: <Navigate to={ROUTES.cabinetSettings} replace />,
          },
        ],
      },
      {
        element: <StaffRoute />,
        children: [
          {
            element: <StaffLayout />,
            children: [
              {
                path: ROUTES.staff.slice(1),
                lazy: lazyPage(
                  () => import("@/applications/staff/pages/dashboard"),
                  "StaffDashboardPage",
                ),
              },
              {
                path: ROUTES.staffCompetitions.slice(1),
                lazy: workspacePlaceholder(staffItem(ROUTES.staffCompetitions), "staff"),
              },
              {
                path: ROUTES.staffApplications.slice(1),
                lazy: workspacePlaceholder(staffItem(ROUTES.staffApplications), "staff"),
              },
              {
                path: ROUTES.staffParticipants.slice(1),
                lazy: workspacePlaceholder(staffItem(ROUTES.staffParticipants), "staff"),
              },
              {
                path: ROUTES.staffJudges.slice(1),
                lazy: workspacePlaceholder(staffItem(ROUTES.staffJudges), "staff"),
              },
              {
                path: ROUTES.staffSchedules.slice(1),
                lazy: workspacePlaceholder(staffItem(ROUTES.staffSchedules), "staff"),
              },
              {
                path: ROUTES.staffOrganization.slice(1),
                lazy: workspacePlaceholder(staffItem(ROUTES.staffOrganization), "staff"),
              },
              {
                path: ROUTES.staffUsers.slice(1),
                lazy: workspacePlaceholder(staffItem(ROUTES.staffUsers), "staff"),
              },
              {
                path: ROUTES.staffInvitations.slice(1),
                lazy: workspacePlaceholder(staffItem(ROUTES.staffInvitations), "staff"),
              },
              {
                path: ROUTES.staffFinance.slice(1),
                lazy: workspacePlaceholder(staffItem(ROUTES.staffFinance), "staff"),
              },
              {
                path: ROUTES.staffAnalytics.slice(1),
                lazy: workspacePlaceholder(staffItem(ROUTES.staffAnalytics), "staff"),
              },
              {
                path: ROUTES.staffSettings.slice(1),
                lazy: workspacePlaceholder(staffItem(ROUTES.staffSettings), "staff"),
              },
            ],
          },
        ],
      },
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
