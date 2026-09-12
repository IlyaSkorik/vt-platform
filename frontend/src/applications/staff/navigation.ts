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

import type { AuthModule } from "@/app/providers";
import { ROUTES, type RoutePath } from "@/shared/config";

export type StaffNavItem = {
  title: string;
  path: RoutePath;
  icon: React.ComponentType<{ className?: string }>;
  description: string;
  /**
   * The module this section belongs to, when it belongs to one.
   *
   * Items without it are the parts an organization always has — its dashboard,
   * its own profile, its people, its settings. An organization without those is
   * not an organization, so they are never offered as something to switch off.
   */
  module?: AuthModule;
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
    module: "COMPETITIONS",
    icon: Medal,
    description: "Управление фестивалями и сезонами.",
  },
  {
    title: "Заявки",
    path: ROUTES.staffApplications,
    module: "APPLICATIONS",
    icon: ClipboardList,
    description: "Очередь заявок на проверку.",
  },
  {
    title: "Участники",
    path: ROUTES.staffParticipants,
    module: "PARTICIPANTS",
    icon: Users,
    description: "Реестр участников организации.",
  },
  {
    title: "Жюри",
    path: ROUTES.staffJudges,
    module: "JURY",
    icon: Gavel,
    description: "Состав жюри и назначения.",
  },
  {
    title: "Программа",
    path: ROUTES.staffProgram,
    module: "PROGRAMS",
    icon: CalendarDays,
    description: "Конструктор программы фестиваля и публичные ссылки.",
  },
  {
    title: "Дипломы",
    path: ROUTES.staffDiplomas,
    module: "DIPLOMAS",
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
    module: "FINANCE",
    icon: Landmark,
    description: "Платежи и финансовые операции.",
  },
  {
    title: "Аналитика",
    path: ROUTES.staffAnalytics,
    module: "ANALYTICS",
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

/**
 * The sections this organization actually has.
 *
 * Presentation only — what a person is *allowed* to do is decided by the API, and
 * every gated endpoint refuses on its own. Hiding a section they cannot use is a
 * courtesy on top of that, not the enforcement.
 *
 * The platform operator sees everything: they are staff of no organization, so
 * there is no entitlement of theirs to consult.
 */
export function visibleStaffNavigation(
  enabledModules: readonly AuthModule[],
  { isPlatformAdmin = false }: { isPlatformAdmin?: boolean } = {},
): StaffNavItem[] {
  if (isPlatformAdmin) {
    return STAFF_NAVIGATION;
  }
  return STAFF_NAVIGATION.filter(
    (item) => item.module === undefined || enabledModules.includes(item.module),
  );
}
