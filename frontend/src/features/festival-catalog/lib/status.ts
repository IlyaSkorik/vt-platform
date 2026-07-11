import type { BadgeProps } from "@/shared/ui";
import type { PublicStatus } from "./types";

type BadgeVariant = NonNullable<BadgeProps["variant"]>;

/** How the primary call-to-action renders for a given status. */
export interface CatalogStatusAction {
  /** Whether the "Apply" button is shown at all (hidden for running/finished). */
  visible: boolean;
  /** Whether it is actionable (only when registration is genuinely open). */
  enabled: boolean;
  label: string;
}

export interface CatalogStatusConfig {
  /** Short status label shown on the card badge. */
  label: string;
  badgeVariant: BadgeVariant;
  apply: CatalogStatusAction;
}

const CONFIG: Record<PublicStatus, CatalogStatusConfig> = {
  REGISTRATION_OPEN: {
    label: "Регистрация открыта",
    badgeVariant: "success",
    apply: { visible: true, enabled: true, label: "Подать заявку" },
  },
  COMING_SOON: {
    label: "Скоро",
    badgeVariant: "info",
    apply: { visible: true, enabled: false, label: "Регистрация скоро" },
  },
  REGISTRATION_CLOSED: {
    label: "Регистрация закрыта",
    badgeVariant: "warning",
    apply: { visible: true, enabled: false, label: "Регистрация закрыта" },
  },
  RUNNING: {
    label: "Идёт",
    badgeVariant: "primary",
    apply: { visible: false, enabled: false, label: "Идёт" },
  },
  COMPLETED: {
    label: "Завершён",
    badgeVariant: "neutral",
    apply: { visible: false, enabled: false, label: "Завершён" },
  },
};

const FALLBACK: CatalogStatusConfig = {
  label: "Фестиваль",
  badgeVariant: "neutral",
  apply: { visible: false, enabled: false, label: "Подробнее" },
};

/** Resolve the presentation config for a public status (tolerant of unknowns). */
export function catalogStatusConfig(status: string): CatalogStatusConfig {
  return CONFIG[status as PublicStatus] ?? FALLBACK;
}

/** Type guard narrowing an arbitrary string to a known public status. */
export function isPublicStatus(status: string): status is PublicStatus {
  return status in CONFIG;
}
