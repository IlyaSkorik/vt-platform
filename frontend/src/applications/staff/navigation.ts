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
    title: "Расписание",
    path: ROUTES.staffSchedules,
    icon: CalendarDays,
    description: "Сетка событий и выступлений.",
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
