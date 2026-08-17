import {
  Award,
  BarChart3,
  BriefcaseBusiness,
  CalendarDays,
  ClipboardList,
  Gavel,
  Home,
  Landmark,
  MailPlus,
  Medal,
  Settings,
  UserCog,
  Users,
} from "lucide-react";

import { ROUTES, type RoutePath } from "@/shared/config";

export type StaffNavItem = {
  title: string;
  path: RoutePath;
  icon: React.ComponentType<{ className?: string }>;
  description: string;
};

/**
 * Whether this route is a workspace rather than a page.
 *
 * A constructor, a builder, a processing screen: places a staffer settles into for
 * an hour and that use every pixel they are given — the festival workspace with its
 * own section rail, the diploma template canvas, the programme builder, the
 * application queue. The navigation is how you *get* to one; once inside it is a
 * column of links taking a fifth of the screen away from the work. So the sidebar
 * collapses itself on the way in and comes back on the way out (see StaffLayout),
 * without touching what the staffer chose for ordinary pages.
 */
export function isStaffWorkspaceRoute(pathname: string): boolean {
  if (pathname === ROUTES.staffProgram || pathname === ROUTES.staffApplications) {
    return true;
  }
  if (pathname.startsWith(`${ROUTES.staffDiplomas}/`) && pathname.endsWith("/constructor")) {
    return true;
  }
  // A single festival — its workspace. The list and the creation form are ordinary pages.
  const rest = pathname.startsWith(`${ROUTES.staffCompetitions}/`)
    ? pathname.slice(ROUTES.staffCompetitions.length + 1)
    : null;
  return rest != null && rest.length > 0 && rest !== "new" && !rest.includes("/");
}

export const STAFF_NAVIGATION: StaffNavItem[] = [
  {
    title: "Dashboard",
    path: ROUTES.staff,
    icon: Home,
    description: "Операционная сводка организации.",
  },
  {
    title: "Фестивали",
    path: ROUTES.staffCompetitions,
    icon: Medal,
    description: "Управление фестивалями и сезонами.",
  },
  {
    title: "Заявки",
    path: ROUTES.staffApplications,
    icon: ClipboardList,
    description: "Очередь заявок на проверку.",
  },
  {
    title: "Участники",
    path: ROUTES.staffParticipants,
    icon: Users,
    description: "Реестр участников организации.",
  },
  {
    title: "Жюри",
    path: ROUTES.staffJudges,
    icon: Gavel,
    description: "Состав жюри и назначения.",
  },
  {
    title: "Программа",
    path: ROUTES.staffProgram,
    icon: CalendarDays,
    description: "Конструктор программы фестиваля и публичные ссылки.",
  },
  {
    title: "Дипломы",
    path: ROUTES.staffDiplomas,
    icon: Award,
    description: "Библиотека шаблонов, назначение и выдача дипломов.",
  },
  {
    title: "Организация",
    path: ROUTES.staffOrganization,
    icon: BriefcaseBusiness,
    description: "Профиль и структура организации.",
  },
  {
    title: "Пользователи",
    path: ROUTES.staffUsers,
    icon: UserCog,
    description: "Доступы сотрудников.",
  },
  {
    title: "Приглашения",
    path: ROUTES.staffInvitations,
    icon: MailPlus,
    description: "Приглашения в рабочее пространство.",
  },
  {
    title: "Финансы",
    path: ROUTES.staffFinance,
    icon: Landmark,
    description: "Платежи и финансовые операции.",
  },
  {
    title: "Аналитика",
    path: ROUTES.staffAnalytics,
    icon: BarChart3,
    description: "Метрики без выдуманных графиков.",
  },
  {
    title: "Настройки",
    path: ROUTES.staffSettings,
    icon: Settings,
    description: "Параметры рабочего пространства.",
  },
];
