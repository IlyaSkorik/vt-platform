import {
  BarChart3,
  Bell,
  BriefcaseBusiness,
  CalendarDays,
  ClipboardList,
  FileText,
  Gavel,
  Home,
  Landmark,
  MailPlus,
  Medal,
  Settings,
  UserCog,
  Users,
} from "lucide-react";

import { ROUTES, type RoutePath } from "./routes";

export type WorkspaceNavItem = {
  title: string;
  path: RoutePath;
  icon: React.ComponentType<{ className?: string }>;
  description: string;
};

export const PARTICIPANT_NAVIGATION: WorkspaceNavItem[] = [
  {
    title: "Главная",
    path: ROUTES.cabinet,
    icon: Home,
    description: "Личная сводка участника.",
  },
  {
    title: "Мои участники",
    path: ROUTES.cabinetParticipants,
    icon: Users,
    description: "Профили участников, привязанные к аккаунту.",
  },
  {
    title: "Мои заявки",
    path: ROUTES.cabinetApplications,
    icon: ClipboardList,
    description: "Заявки и статусы подачи.",
  },
  {
    title: "Конкурсы",
    path: ROUTES.cabinetCompetitions,
    icon: Medal,
    description: "Конкурсы, доступные для участия.",
  },
  {
    title: "Документы",
    path: ROUTES.cabinetDocuments,
    icon: FileText,
    description: "Файлы и документы личного кабинета.",
  },
  {
    title: "Уведомления",
    path: ROUTES.cabinetNotifications,
    icon: Bell,
    description: "Личные сообщения и события.",
  },
  {
    title: "Настройки",
    path: ROUTES.cabinetSettings,
    icon: Settings,
    description: "Персональные параметры аккаунта.",
  },
];

export const STAFF_NAVIGATION: WorkspaceNavItem[] = [
  {
    title: "Dashboard",
    path: ROUTES.staff,
    icon: Home,
    description: "Операционная сводка организации.",
  },
  {
    title: "Конкурсы",
    path: ROUTES.staffCompetitions,
    icon: Medal,
    description: "Управление конкурсами и сезонами.",
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
