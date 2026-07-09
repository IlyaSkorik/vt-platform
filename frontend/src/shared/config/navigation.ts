import {
  BarChart3,
  Calendar,
  ClipboardList,
  FileCheck,
  LayoutDashboard,
  Settings,
  Trophy,
  Users,
  WalletCards,
} from "lucide-react";

import { ROUTES, type RoutePath } from "./routes";

export type NavItem = {
  id: string;
  label: string;
  to: RoutePath;
  icon: React.ComponentType<{ className?: string }>;
  children?: NavItem[];
};

export type NavGroup = {
  id: string;
  label?: string;
  items: NavItem[];
};

export type NavModel = NavGroup[];

export type NavigationItem = NavItem;

export const NAVIGATION: NavModel = [
  {
    id: "main",
    label: "Реестр",
    items: [
      { id: "cabinet", label: "Кабинет", to: ROUTES.cabinet, icon: LayoutDashboard },
      { id: "participants", label: "Участники", to: ROUTES.participants, icon: Users },
      {
        id: "competitions",
        label: "Конкурсы",
        to: ROUTES.competitions,
        icon: Trophy,
        children: [
          { id: "applications", label: "Заявки", to: ROUTES.applications, icon: ClipboardList },
          { id: "performances", label: "Выступления", to: ROUTES.performances, icon: Calendar },
        ],
      },
    ],
  },
  {
    id: "judging",
    label: "Судейство",
    items: [
      { id: "judging", label: "Судейство", to: ROUTES.judging, icon: FileCheck },
      { id: "results", label: "Результаты", to: ROUTES.results, icon: BarChart3 },
      { id: "finance", label: "Финансы", to: ROUTES.finance, icon: WalletCards },
      { id: "settings", label: "Настройки", to: ROUTES.settings, icon: Settings },
    ],
  },
];

export function resolveBreadcrumbs(pathname: string): NavigationItem[] {
  for (const group of NAVIGATION) {
    for (const item of group.items) {
      if (pathname === item.to || pathname.startsWith(`${item.to}/`)) {
        return [item];
      }

      const child = item.children?.find(
        (candidate) => pathname === candidate.to || pathname.startsWith(`${candidate.to}/`),
      );

      if (child != null) {
        return [item, child];
      }
    }
  }

  return [];
}
