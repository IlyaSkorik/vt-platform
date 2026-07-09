import {
  Award,
  BarChart3,
  ClipboardList,
  Gauge,
  Gavel,
  LayoutDashboard,
  type LucideIcon,
  Music,
  Settings,
  Trophy,
  Users,
  Wallet,
} from "lucide-react";
import { ROUTES } from "./routes";

/**
 * Navigation model — the single source of truth for the app-shell sidebar.
 *
 * This is DATA, not UI: the shell (`widgets/app-shell`) renders whatever this
 * describes, so adding a section or a nested child never touches shell code.
 * It carries no business logic — only labels, icons and the route each item
 * points at. Every `to` is a declared path in {@link ROUTES}, so navigation
 * and the router cannot drift.
 *
 * Structure:
 *   NavModel  = ordered list of groups
 *   NavGroup  = an optional heading + ordered items
 *   NavItem   = a labelled, icon'd link, optionally with nested children
 */
export interface NavItem {
  /** Stable identity (used for keys, expansion state, active matching). */
  readonly id: string;
  /** Human-readable label (ru-RU primary). */
  readonly label: string;
  /** Target route. Omitted for a pure parent that only groups children. */
  readonly to?: string;
  /** Icon component (top-level items only, by convention). */
  readonly icon?: LucideIcon;
  /** Nested navigation, one level deep. */
  readonly children?: readonly NavItem[];
}

export interface NavGroup {
  readonly id: string;
  /** Optional section heading; when absent the group renders without a label. */
  readonly label?: string;
  readonly items: readonly NavItem[];
}

export type NavModel = readonly NavGroup[];

export interface NavigationOptions {
  readonly hasStaffAccess: boolean;
}

const STAFF_NAV_ITEM: NavItem = {
  id: "staff",
  label: "Панель управления",
  to: ROUTES.staff,
  icon: Gauge,
};

/**
 * The VT Platform primary navigation.
 *
 * Sections are grouped by intent (overview → registry → operations →
 * insights → system) rather than dumped in one flat list, matching the
 * enterprise shells this platform targets (Linear, Vercel, Stripe).
 */
export const NAVIGATION: NavModel = [
  {
    id: "overview",
    items: [{ id: "cabinet", label: "Кабинет", to: ROUTES.cabinet, icon: LayoutDashboard }],
  },
  {
    id: "registry",
    label: "Реестр",
    items: [
      { id: "participants", label: "Участники", to: ROUTES.participants, icon: Users },
      {
        id: "competitions",
        label: "Конкурсы",
        to: ROUTES.competitions,
        icon: Trophy,
        children: [
          { id: "applications", label: "Заявки", to: ROUTES.applications },
          { id: "performances", label: "Выступления", to: ROUTES.performances },
        ],
      },
    ],
  },
  {
    id: "operations",
    label: "Судейство",
    items: [
      { id: "judging", label: "Судейство", to: ROUTES.judging, icon: Gavel },
      { id: "results", label: "Результаты", to: ROUTES.results, icon: Award },
    ],
  },
  {
    id: "insights",
    label: "Аналитика",
    items: [
      { id: "finance", label: "Финансы", to: ROUTES.finance, icon: Wallet },
      { id: "analytics", label: "Аналитика", to: ROUTES.analytics, icon: BarChart3 },
    ],
  },
  {
    id: "system",
    items: [{ id: "settings", label: "Настройки", to: ROUTES.settings, icon: Settings }],
  },
];

export function getNavigation({ hasStaffAccess }: NavigationOptions): NavModel {
  if (!hasStaffAccess) {
    return NAVIGATION;
  }
  const overview = NAVIGATION[0];
  if (overview == null) {
    return NAVIGATION;
  }
  const rest = NAVIGATION.slice(1);
  return [
    {
      id: overview.id,
      ...(overview.label != null ? { label: overview.label } : {}),
      items: [...overview.items, STAFF_NAV_ITEM],
    },
    ...rest,
  ];
}

/** Icons re-exported for empty-section stories/tests without extra imports. */
export const NAV_ICONS = { Music, ClipboardList } as const;

interface NavCrumb {
  readonly id: string;
  readonly label: string;
  readonly to?: string;
}

/**
 * Flattened index from a route path → its breadcrumb trail (root → leaf).
 *
 * Built once at module load from {@link NAVIGATION}. Parent items contribute a
 * crumb even when they have no own `to`, so a nested page reads e.g.
 * "Конкурсы › Заявки". This keeps breadcrumb derivation O(1) per navigation.
 */
const CRUMB_INDEX: ReadonlyMap<string, readonly NavCrumb[]> = (() => {
  const index = new Map<string, NavCrumb[]>();
  for (const group of getNavigation({ hasStaffAccess: true })) {
    for (const item of group.items) {
      const base: NavCrumb = {
        id: item.id,
        label: item.label,
        ...(item.to ? { to: item.to } : {}),
      };
      if (item.to) {
        index.set(item.to, [base]);
      }
      for (const child of item.children ?? []) {
        if (child.to) {
          index.set(child.to, [base, { id: child.id, label: child.label, to: child.to }]);
        }
      }
    }
  }
  return index;
})();

/**
 * Resolve the breadcrumb trail for a pathname against the navigation model.
 *
 * Returns the mapped trail (root → current) or an empty array when the path is
 * not part of the primary navigation (e.g. a detail route a feature owns).
 */
export function resolveBreadcrumbs(pathname: string): readonly NavCrumb[] {
  return CRUMB_INDEX.get(pathname) ?? [];
}

export type { NavCrumb };
