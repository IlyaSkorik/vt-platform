import { createBrowserRouter, Navigate, type RouteObject } from "react-router";
import { AuthLayout } from "@/app/layouts/auth-layout";
import { MinimalLayout } from "@/app/layouts/minimal-layout";
import { NotFoundLayout } from "@/app/layouts/not-found-layout";
import { ParticipantLayout } from "@/app/layouts/participant-layout";
import { PublicLayout } from "@/app/layouts/public-layout";
import { RootLayout } from "@/app/layouts/root-layout";
import { StaffLayout } from "@/app/layouts/staff-layout";
import { ROUTES } from "@/shared/config";
import { GuestRoute, ProtectedRoute, StaffRoute } from "./guards";
import { RouteError } from "./route-error";

/** Lazily import a page module, mapping its named export to `Component`. */
const lazyPage =
  (loader: () => Promise<Record<string, React.ComponentType>>, name: string) => async () => ({
    Component: (await loader())[name] as React.ComponentType,
  });

const participantPage = (title: string, description: string) => async () => {
  const { WorkspacePlaceholderPage } = await import("@/pages/workspace-placeholder");
  return {
    Component: () => <WorkspacePlaceholderPage title={title} description={description} />,
  } satisfies { Component: React.ComponentType };
};

const staffPage = participantPage;

/**
 * Application route tree (React Router v7, data router).
 *
 * Participant Cabinet and Staff Workspace are independent protected workspaces:
 * `/cabinet/**` is always available to authenticated users, while `/staff/**`
 * is guarded by CurrentUser.staffMembership and rendered in its own layout.
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
                lazy: lazyPage(() => import("@/pages/dashboard"), "DashboardPage"),
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
                lazy: participantPage("Заявки", "Заявки участника и их текущие статусы."),
              },
              {
                path: ROUTES.cabinetCompetitions.slice(1),
                lazy: participantPage("Конкурсы", "Доступные конкурсы для личного кабинета."),
              },
              {
                path: ROUTES.cabinetDocuments.slice(1),
                lazy: participantPage("Документы", "Файлы и документы участника."),
              },
              {
                path: ROUTES.cabinetNotifications.slice(1),
                lazy: participantPage("Уведомления", "События и сообщения личного кабинета."),
              },
              {
                path: ROUTES.cabinetSettings.slice(1),
                lazy: participantPage("Настройки", "Персональные настройки кабинета."),
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
                lazy: staffPage("Панель управления", "Операционная панель организации."),
              },
              {
                path: ROUTES.staffCompetitions.slice(1),
                lazy: staffPage("Конкурсы", "Управление конкурсами организации."),
              },
              {
                path: ROUTES.staffApplications.slice(1),
                lazy: staffPage("Заявки", "Проверка и обработка заявок."),
              },
              {
                path: ROUTES.staffParticipants.slice(1),
                lazy: staffPage("Участники", "Работа с участниками организации."),
              },
              {
                path: ROUTES.staffJudges.slice(1),
                lazy: staffPage("Судьи", "Команда судей и назначений."),
              },
              {
                path: ROUTES.staffSchedules.slice(1),
                lazy: staffPage("Расписание", "Планирование событий и выступлений."),
              },
              {
                path: ROUTES.staffFinance.slice(1),
                lazy: staffPage("Финансы", "Финансовые операции организации."),
              },
              {
                path: ROUTES.staffOrganization.slice(1),
                lazy: staffPage("Организация", "Профиль и параметры организации."),
              },
              {
                path: ROUTES.staffUsers.slice(1),
                lazy: staffPage("Пользователи", "Управление доступами сотрудников."),
              },
              {
                path: ROUTES.staffInvitations.slice(1),
                lazy: staffPage("Приглашения", "Приглашения сотрудников в организацию."),
              },
              {
                path: ROUTES.staffSettings.slice(1),
                lazy: staffPage("Настройки", "Настройки панели управления."),
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
