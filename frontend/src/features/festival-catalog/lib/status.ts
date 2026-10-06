import type { BadgeProps } from "@/shared/ui";
import type { PublicStatus } from "./types";

type BadgeVariant = NonNullable<BadgeProps["variant"]>;

/**
 * How the primary call-to-action renders for a given status.
 *
 * The slot is always filled. A festival that cannot be applied to does not drop
 * the button — it says why instead, which is the one piece of information the
 * reader actually wants at that point. An empty place where an action used to be
 * answers nothing and leaves the card a head shorter than the one beside it.
 */
export interface CatalogStatusAction {
  /** Whether it links anywhere, or merely states why it does not. */
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
    apply: { enabled: true, label: "Подать заявку" },
  },
  COMING_SOON: {
    label: "Скоро",
    badgeVariant: "info",
    apply: { enabled: false, label: "Регистрация скоро" },
  },
  REGISTRATION_CLOSED: {
    label: "Регистрация закрыта",
    badgeVariant: "warning",
    apply: { enabled: false, label: "Регистрация закрыта" },
  },
  // The action says what the *festival* is doing, not what the badge above it
  // already said: «Фестиваль идёт» rather than a bare «Идёт», which in the place
  // of a button reads as a half-sentence.
  RUNNING: {
    label: "Идёт",
    badgeVariant: "primary",
    apply: { enabled: false, label: "Фестиваль идёт" },
  },
  COMPLETED: {
    label: "Завершён",
    badgeVariant: "neutral",
    apply: { enabled: false, label: "Фестиваль завершён" },
  },
};

const FALLBACK: CatalogStatusConfig = {
  label: "Фестиваль",
  badgeVariant: "neutral",
  apply: { enabled: false, label: "Регистрация недоступна" },
};

/** Resolve the presentation config for a public status (tolerant of unknowns). */
export function catalogStatusConfig(status: string): CatalogStatusConfig {
  return CONFIG[status as PublicStatus] ?? FALLBACK;
}

/** Type guard narrowing an arbitrary string to a known public status. */
export function isPublicStatus(status: string): status is PublicStatus {
  return status in CONFIG;
}
