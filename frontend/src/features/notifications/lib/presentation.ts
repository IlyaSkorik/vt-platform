import { AlertTriangle, Bell, CheckCircle2, Clock, FileUp, Trophy, XCircle } from "lucide-react";

import type { NotificationKindEnum } from "@/shared/api/generated/model-notifications";

export type NotificationPresentation = {
  label: string;
  icon: React.ComponentType<{ className?: string }>;
  /** Tailwind classes for the icon chip — accent only, never the sole signal. */
  tone: string;
};

/**
 * How each kind reads in the cabinet.
 *
 * Grouped by what the reader has to *do* rather than by which use case produced
 * the row: two kinds ask for money, two ask for a fix, two are simply news. The
 * label is spelled out beside the icon, because colour alone is not a signal
 * anyone can rely on (WCAG 1.4.1).
 */
const PRESENTATION: Record<string, NotificationPresentation> = {
  APPLICATION_SUBMITTED: {
    label: "Заявка подана",
    icon: CheckCircle2,
    tone: "bg-success/10 text-success",
  },
  PAYMENT_EXPECTED: {
    label: "Ожидается оплата",
    icon: Clock,
    tone: "bg-warning/10 text-warning",
  },
  APPLICATION_APPROVED: {
    label: "Заявка одобрена",
    icon: CheckCircle2,
    tone: "bg-success/10 text-success",
  },
  APPLICATION_CANCELLED: {
    label: "Заявка отменена",
    icon: XCircle,
    tone: "bg-danger/10 text-danger",
  },
  CORRECTION_REQUESTED: {
    label: "Нужно исправить",
    icon: AlertTriangle,
    tone: "bg-warning/10 text-warning",
  },
  FILES_REQUESTED: {
    label: "Нужны файлы",
    icon: FileUp,
    tone: "bg-warning/10 text-warning",
  },
  RESULTS_PUBLISHED: {
    label: "Результаты",
    icon: Trophy,
    tone: "bg-primary/10 text-primary",
  },
};

const FALLBACK: NotificationPresentation = {
  label: "Уведомление",
  icon: Bell,
  tone: "bg-muted text-muted-foreground",
};

/**
 * Presentation for a notification kind.
 *
 * A kind the frontend has never heard of still renders — as a plain notice rather
 * than disappearing. The backend adds kinds ahead of a frontend deploy, and a
 * silently dropped row is a person not being told something.
 */
export function notificationPresentation(
  kind: NotificationKindEnum | string,
): NotificationPresentation {
  return PRESENTATION[kind] ?? FALLBACK;
}

/** "5 минут назад" / "вчера" / "12 марта" — as close as the reader needs. */
export function formatNotificationTime(iso: string): string {
  const at = new Date(iso);
  const minutes = Math.round((Date.now() - at.getTime()) / 60_000);
  if (minutes < 1) return "только что";
  if (minutes < 60) return `${minutes} мин назад`;
  const hours = Math.round(minutes / 60);
  if (hours < 24) return `${hours} ч назад`;
  if (hours < 48) return "вчера";
  return at.toLocaleDateString("ru-RU", { day: "2-digit", month: "long" });
}
