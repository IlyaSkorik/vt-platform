import { Bell, ClipboardList, FileText, Home, Medal, Settings, Users } from "lucide-react";

import { ROUTES, type RoutePath } from "@/shared/config";

export type ParticipantNavItem = {
  title: string;
  path: RoutePath;
  icon: React.ComponentType<{ className?: string }>;
  description: string;
};

export const PARTICIPANT_NAVIGATION: ParticipantNavItem[] = [
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
