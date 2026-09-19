import { createBrowserRouter, Navigate, Outlet, type RouteObject } from "react-router";
import { AuthLayout } from "@/app/layouts/auth-layout";
import { MinimalLayout } from "@/app/layouts/minimal-layout";
import { NotFoundLayout } from "@/app/layouts/not-found-layout";
import { PublicLayout } from "@/app/layouts/public-layout";
import { RootLayout } from "@/app/layouts/root-layout";
import { ParticipantLayout } from "@/applications/participant/layouts/participant-layout";
import { PlatformLayout } from "@/applications/platform/layouts/platform-layout";
import { StaffLayout } from "@/applications/staff/layouts/staff-layout";
import { STAFF_NAVIGATION, type StaffNavItem } from "@/applications/staff/navigation";
import { ROUTES } from "@/shared/config";
import { GuestRoute, ModuleRoute, PlatformRoute, ProtectedRoute, StaffRoute } from "./guards";
import { RouteError } from "./route-error";
import { RouteHydrateFallback } from "./route-hydrate-fallback";

/** Lazily import a page module, mapping its named export to `Component`. */
const lazyPage =
  (loader: () => Promise<Record<string, React.ComponentType>>, name: string) => async () => {
    const module = await loader();
    const Component = module[name];
    if (Component == null) {
      throw new Error(`Page export "${name}" was not found in lazy route module.`);
    }
    return { Component };
  };

const workspacePlaceholder = (item: StaffNavItem, tone: "participant" | "staff") => async () => {
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
/** Exported for the tests that assert route-tree invariants; the app uses `router`. */
export const routes: RouteObject[] = [
  {
    element: <RootLayout />,
    errorElement: <RouteError />,
    // Every child route is `lazy`, so the first paint always waits on a chunk.
    // Without this the router renders nothing and warns about it.
    HydrateFallback: RouteHydrateFallback,
    children: [
      {
        element: <PublicLayout />,
        children: [
          { index: true, lazy: lazyPage(() => import("@/pages/home"), "HomePage") },
          {
            path: ROUTES.competitions.slice(1),
            element: <Outlet />,
            children: [
              {
                index: true,
                lazy: lazyPage(() => import("@/pages/festivals"), "PublicFestivalCatalogPage"),
              },
              {
                path: ":festivalId",
                lazy: lazyPage(() => import("@/pages/festivals"), "PublicFestivalLandingPage"),
              },
            ],
          },
          {
            // Public and unauthenticated: reached by scanning a printed diploma.
            path: ROUTES.verifyDiploma.slice(1),
            lazy: lazyPage(() => import("@/pages/verify"), "DiplomaVerifyPage"),
          },
          {
            // Public and unauthenticated: a programme link handed to the sound
            // engineer, the host, the jury, or a screen beside the stage.
            path: ROUTES.publicProgram.slice(1),
            lazy: lazyPage(() => import("@/pages/program"), "PublicProgramPage"),
          },
          {
            // Public and unauthenticated: linked from the festival's "Результаты" section
            // and from the letter every participant is sent when the results are published.
            path: ROUTES.publicProtocol.slice(1),
            lazy: lazyPage(() => import("@/pages/protocol"), "PublicProtocolPage"),
          },
          {
            // The audience vote, reached by scanning a code on a poster. No account:
            // the slug is the only credential, because nobody registers to clap.
            path: ROUTES.publicBallot.slice(1),
            lazy: lazyPage(() => import("@/pages/vote"), "PublicVotePage"),
          },
          {
            // The same ballot as a scoreboard for the projector beside the stage —
            // a screen nobody taps, read from the back of the hall.
            path: ROUTES.publicBallotBoard.slice(1),
            lazy: lazyPage(() => import("@/pages/vote-board"), "PublicVoteBoardPage"),
          },
          {
            // The review form, reached by scanning a code on a banner. No account:
            // the slug is the only credential, because nobody registers to say
            // thank you on their way out of a hall.
            path: ROUTES.publicReview.slice(1),
            lazy: lazyPage(() => import("@/pages/reviews"), "PublicReviewPage"),
          },
          {
            // The contract itself, public and unauthenticated: it has to be readable
            // before registering, because registering is accepting it (LEGAL-003 §3.3).
            path: ROUTES.termsOfService.slice(1),
            lazy: lazyPage(() => import("@/pages/legal"), "TermsOfServicePage"),
          },
          {
            path: ROUTES.privacyPolicy.slice(1),
            lazy: lazyPage(() => import("@/pages/legal"), "PrivacyPolicyPage"),
          },
          {
            path: ROUTES.cookiesPolicy.slice(1),
            lazy: lazyPage(() => import("@/pages/legal"), "CookiesPolicyPage"),
          },
        ],
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
                path: ROUTES.cabinetParticipantNew.slice(1),
                lazy: lazyPage(() => import("@/pages/participants"), "ParticipantsProfilePage"),
              },
              {
                path: ROUTES.cabinetParticipantProfile.slice(1),
                lazy: lazyPage(() => import("@/pages/participants"), "ParticipantsProfilePage"),
              },
              {
                path: ROUTES.cabinetTeachers.slice(1),
                lazy: lazyPage(() => import("@/pages/teachers"), "TeachersPage"),
              },
              {
                path: ROUTES.cabinetTeacherNew.slice(1),
                lazy: lazyPage(() => import("@/pages/teachers"), "TeacherProfilePage"),
              },
              {
                path: ROUTES.cabinetTeacherProfile.slice(1),
                lazy: lazyPage(() => import("@/pages/teachers"), "TeacherProfilePage"),
              },
              {
                path: ROUTES.cabinetApplications.slice(1),
                element: <Outlet />,
                children: [
                  {
                    index: true,
                    lazy: lazyPage(() => import("@/pages/applications"), "MyApplicationsPage"),
                  },
                  {
                    path: ":applicationId",
                    lazy: lazyPage(() => import("@/pages/applications"), "ApplicationDetailPage"),
                  },
                  {
                    path: ":applicationId/edit",
                    lazy: lazyPage(() => import("@/pages/applications"), "ApplicationEditPage"),
                  },
                ],
              },
              {
                path: ROUTES.cabinetCompetitions.slice(1),
                element: <Outlet />,
                children: [
                  {
                    index: true,
                    lazy: lazyPage(
                      () => import("@/applications/participant/pages/festivals"),
                      "FestivalCatalogPage",
                    ),
                  },
                  {
                    path: ":festivalId",
                    lazy: lazyPage(
                      () => import("@/applications/participant/pages/festivals"),
                      "FestivalLandingPage",
                    ),
                  },
                  {
                    path: ":festivalId/apply",
                    lazy: lazyPage(() => import("@/pages/applications"), "FestivalApplyPage"),
                  },
                ],
              },
              {
                path: ROUTES.cabinetDocuments.slice(1),
                lazy: lazyPage(() => import("@/pages/documents"), "MyDocumentsPage"),
              },
              {
                path: ROUTES.cabinetNotifications.slice(1),
                lazy: lazyPage(() => import("@/pages/notifications"), "NotificationsPage"),
              },
              {
                path: ROUTES.cabinetSettings.slice(1),
                lazy: lazyPage(() => import("@/pages/settings"), "SettingsPage"),
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
                element: <ModuleRoute module="COMPETITIONS" />,
                children: [
                  {
                    path: ROUTES.staffCompetitions.slice(1),
                    element: <Outlet />,
                    children: [
                      {
                        index: true,
                        lazy: lazyPage(
                          () => import("@/applications/staff/pages/competitions"),
                          "StaffCompetitionsPage",
                        ),
                      },
                      {
                        path: "new",
                        lazy: lazyPage(
                          () => import("@/applications/staff/pages/competitions/new"),
                          "StaffCreateCompetitionPage",
                        ),
                      },
                      {
                        path: ":competitionId",
                        lazy: lazyPage(
                          () => import("@/applications/staff/pages/competition-workspace"),
                          "StaffCompetitionWorkspacePage",
                        ),
                      },
                    ],
                  },
                ],
              },
              {
                element: <ModuleRoute module="APPLICATIONS" />,
                children: [
                  {
                    path: ROUTES.staffApplications.slice(1),
                    lazy: lazyPage(
                      () => import("@/applications/staff/pages/applications"),
                      "StaffApplicationsProcessingPage",
                    ),
                  },
                ],
              },
              {
                element: <ModuleRoute module="PARTICIPANTS" />,
                children: [
                  {
                    path: ROUTES.staffParticipants.slice(1),
                    lazy: lazyPage(
                      () => import("@/applications/staff/pages/participants"),
                      "StaffParticipantsPage",
                    ),
                  },
                ],
              },
              {
                element: <ModuleRoute module="JURY" />,
                children: [
                  {
                    path: ROUTES.staffJudges.slice(1),
                    lazy: lazyPage(
                      () => import("@/applications/staff/pages/judges"),
                      "StaffJudgesPage",
                    ),
                  },
                ],
              },
              {
                element: <ModuleRoute module="PROGRAMS" />,
                children: [
                  {
                    path: ROUTES.staffProgram.slice(1),
                    lazy: lazyPage(
                      () => import("@/applications/staff/pages/program"),
                      "StaffProgramPage",
                    ),
                  },
                ],
              },
              {
                element: <ModuleRoute module="VOTING" />,
                children: [
                  {
                    path: ROUTES.staffVoting.slice(1),
                    lazy: lazyPage(
                      () => import("@/applications/staff/pages/voting"),
                      "StaffVotingPage",
                    ),
                  },
                ],
              },
              {
                element: <ModuleRoute module="REVIEWS" />,
                children: [
                  {
                    path: ROUTES.staffReviews.slice(1),
                    lazy: lazyPage(
                      () => import("@/applications/staff/pages/reviews"),
                      "StaffReviewsPage",
                    ),
                  },
                ],
              },
              {
                element: <ModuleRoute module="DIPLOMAS" />,
                children: [
                  {
                    path: ROUTES.staffDiplomas.slice(1),
                    element: <Outlet />,
                    children: [
                      {
                        index: true,
                        lazy: lazyPage(
                          () => import("@/applications/staff/pages/diplomas"),
                          "StaffDiplomasPage",
                        ),
                      },
                      {
                        path: "templates/:templateId/constructor",
                        lazy: lazyPage(
                          () => import("@/applications/staff/pages/diplomas/constructor"),
                          "StaffDiplomaTemplateConstructorPage",
                        ),
                      },
                    ],
                  },
                ],
              },
              {
                path: ROUTES.staffOrganization.slice(1),
                lazy: lazyPage(
                  () => import("@/applications/staff/pages/organization"),
                  "StaffOrganizationPage",
                ),
              },
              {
                path: ROUTES.staffUsers.slice(1),
                lazy: lazyPage(() => import("@/applications/staff/pages/users"), "StaffUsersPage"),
              },
              {
                path: ROUTES.staffInvitations.slice(1),
                lazy: lazyPage(
                  () => import("@/applications/staff/pages/invitations"),
                  "StaffInvitationsPage",
                ),
              },
              {
                element: <ModuleRoute module="FINANCE" />,
                children: [
                  {
                    path: ROUTES.staffFinance.slice(1),
                    lazy: workspacePlaceholder(staffItem(ROUTES.staffFinance), "staff"),
                  },
                ],
              },
              {
                element: <ModuleRoute module="ANALYTICS" />,
                children: [
                  {
                    path: ROUTES.staffAnalytics.slice(1),
                    lazy: workspacePlaceholder(staffItem(ROUTES.staffAnalytics), "staff"),
                  },
                ],
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
        // The platform operator's console, gated on `platformAdmin` rather than
        // on staff membership: an organization's owner is not admitted here.
        element: <PlatformRoute />,
        children: [
          {
            element: <PlatformLayout />,
            children: [
              {
                path: ROUTES.platform.slice(1),
                lazy: lazyPage(
                  () => import("@/applications/platform/pages/dashboard"),
                  "PlatformDashboardPage",
                ),
              },
              {
                path: ROUTES.platformOrganizations.slice(1),
                lazy: lazyPage(
                  () => import("@/applications/platform/pages/organizations"),
                  "PlatformOrganizationsPage",
                ),
              },
              {
                path: ROUTES.platformTesting.slice(1),
                lazy: lazyPage(
                  () => import("@/applications/platform/pages/testing"),
                  "PlatformTestingPage",
                ),
              },
              {
                path: ROUTES.platformReviews.slice(1),
                lazy: lazyPage(
                  () => import("@/applications/platform/pages/reviews"),
                  "PlatformReviewsPage",
                ),
              },
              {
                path: ROUTES.platformErase.slice(1),
                lazy: lazyPage(
                  () => import("@/applications/platform/pages/erase"),
                  "PlatformErasePage",
                ),
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

/**
 * Build the data router.
 *
 * A function rather than a module-level constant: `createBrowserRouter` starts
 * navigating the moment it is called, so a constant made importing this module a
 * side effect — and any test that wanted to read the route tree paid for a full
 * navigation it never asked for. The app calls this once, which is what it did
 * before.
 */
export function createAppRouter(): ReturnType<typeof createBrowserRouter> {
  return createBrowserRouter(routes);
}
