import type { BadgeProps } from "@/shared/ui";
import type { PublicStatus } from "./types";

type BadgeVariant = NonNullable<BadgeProps["variant"]>;

/**
 * How the landing page presents a given public status.
 *
 * The single source of truth for the hero status pill and the primary
 * call-to-action. Only {@link canApply} (registration genuinely open) routes to
 * the registration wizard; every other state renders an informational,
 * non-actionable button so the CTA always matches the public status.
 */
export interface LandingCta {
  /** Short status pill label shown in the hero. */
  statusLabel: string;
  badgeVariant: BadgeVariant;
  /** Primary call-to-action label. */
  ctaLabel: string;
  /** Whether the CTA is an actionable "Apply" (links to the registration wizard). */
  canApply: boolean;
}

const CONFIG: Record<PublicStatus, LandingCta> = {
  REGISTRATION_OPEN: {
    statusLabel: "Регистрация открыта",
    badgeVariant: "success",
    ctaLabel: "Подать заявку",
    canApply: true,
  },
  COMING_SOON: {
    statusLabel: "Скоро открытие",
    badgeVariant: "info",
    ctaLabel: "Регистрация скоро откроется",
    canApply: false,
  },
  REGISTRATION_CLOSED: {
    statusLabel: "Регистрация закрыта",
    badgeVariant: "warning",
    ctaLabel: "Регистрация закрыта",
    canApply: false,
  },
  RUNNING: {
    statusLabel: "Идёт сейчас",
    badgeVariant: "primary",
    ctaLabel: "Фестиваль идёт",
    canApply: false,
  },
  COMPLETED: {
    statusLabel: "Завершён",
    badgeVariant: "neutral",
    ctaLabel: "Фестиваль завершён",
    canApply: false,
  },
};

const FALLBACK: LandingCta = {
  statusLabel: "Фестиваль",
  badgeVariant: "neutral",
  ctaLabel: "Подробнее",
  canApply: false,
};

/** Resolve the landing presentation config for a public status (tolerant of unknowns). */
export function landingCta(status: string): LandingCta {
  return CONFIG[status as PublicStatus] ?? FALLBACK;
}

/** Type guard narrowing an arbitrary string to a known public status. */
export function isPublicStatus(status: string): status is PublicStatus {
  return status in CONFIG;
}
