import {
  Bell,
  BriefcaseBusiness,
  CalendarDays,
  ClipboardList,
  FileText,
  Landmark,
  LayoutDashboard,
  ListChecks,
  Medal,
  Settings,
  ShieldCheck,
  UserCog,
  Users,
} from "lucide-react";

import { ROUTES, type RoutePath } from "./routes";

export type WorkspaceNavItem = {
  title: string;
  path: RoutePath;
  icon: React.ComponentType<{ className?: string }>;
};

export const PARTICIPANT_NAVIGATION: WorkspaceNavItem[] = [
  { title: "Главная", path: ROUTES.cabinet, icon: LayoutDashboard },
  { title: "Участники", path: ROUTES.cabinetParticipants, icon: Users },
  { title: "Заявки", path: ROUTES.cabinetApplications, icon: ClipboardList },
  { title: "Конкурсы", path: ROUTES.cabinetCompetitions, icon: Medal },
  { title: "Документы", path: ROUTES.cabinetDocuments, icon: FileText },
  { title: "Уведомления", path: ROUTES.cabinetNotifications, icon: Bell },
  { title: "Настройки", path: ROUTES.cabinetSettings, icon: Settings },
];

export const STAFF_NAVIGATION: WorkspaceNavItem[] = [
  { title: "Панель управления", path: ROUTES.staff, icon: ShieldCheck },
  { title: "Конкурсы", path: ROUTES.staffCompetitions, icon: Medal },
  { title: "Заявки", path: ROUTES.staffApplications, icon: ListChecks },
  { title: "Участники", path: ROUTES.staffParticipants, icon: Users },
  { title: "Судьи", path: ROUTES.staffJudges, icon: UserCog },
  { title: "Расписание", path: ROUTES.staffSchedules, icon: CalendarDays },
  { title: "Финансы", path: ROUTES.staffFinance, icon: Landmark },
  { title: "Организация", path: ROUTES.staffOrganization, icon: BriefcaseBusiness },
  { title: "Пользователи", path: ROUTES.staffUsers, icon: Users },
  { title: "Приглашения", path: ROUTES.staffInvitations, icon: ClipboardList },
  { title: "Настройки", path: ROUTES.staffSettings, icon: Settings },
];
