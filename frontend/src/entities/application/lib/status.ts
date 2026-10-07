/**
 * Presentation helpers for the application (order) lifecycle status.
 *
 * The backend owns the lifecycle; the frontend only renders it. This maps each
 * status to a Russian label and a Badge variant so status is shown consistently.
 */
type BadgeVariant =
  | "primary"
  | "secondary"
  | "success"
  | "warning"
  | "danger"
  | "info"
  | "outline"
  | "neutral";

type StatusPresentation = {
  label: string;
  variant: BadgeVariant;
};

const APPLICATION_STATUS: Record<string, StatusPresentation> = {
  DRAFT: { label: "Черновик", variant: "neutral" },
  SUBMITTED: { label: "Подана", variant: "info" },
  WAITING_PAYMENT: { label: "Ожидает оплаты", variant: "warning" },
  PAID: { label: "Оплачена", variant: "success" },
  COMPLETED: { label: "Завершена", variant: "success" },
  CANCELLED: { label: "Отменена", variant: "danger" },
};

const SUBMISSION_STATUS: Record<string, StatusPresentation> = {
  DRAFT: { label: "Черновик", variant: "neutral" },
  WAITLISTED: { label: "Лист ожидания", variant: "secondary" },
  SUBMITTED: { label: "Подана", variant: "info" },
  UNDER_REVIEW: { label: "На проверке", variant: "info" },
  REQUIRES_CORRECTION: { label: "Требует правок", variant: "warning" },
  APPROVED: { label: "Одобрена", variant: "success" },
  WAITING_PAYMENT: { label: "Ожидает оплаты", variant: "warning" },
  PAID: { label: "Оплачена", variant: "success" },
  ACCEPTED: { label: "Принята", variant: "success" },
  SCHEDULED: { label: "В расписании", variant: "info" },
  COMPLETED: { label: "Завершена", variant: "success" },
  CANCELLED: { label: "Отменена", variant: "danger" },
};

const FALLBACK: StatusPresentation = { label: "—", variant: "neutral" };

export function applicationStatusPresentation(status: string): StatusPresentation {
  return APPLICATION_STATUS[status] ?? FALLBACK;
}

export function submissionStatusPresentation(status: string): StatusPresentation {
  return SUBMISSION_STATUS[status] ?? FALLBACK;
}
