/**
 * Dashboard view models.
 *
 * These are read-only, screen-shaped DTOs the dashboard renders — deliberately
 * flatter than the domain aggregates (DATA-001). They live in the widget slice
 * because they exist to compose *this* screen; a real feature would source
 * equivalent shapes from `entities/*` via the API. Money is kept in minor units
 * + currency (never a float) per API-000, and every date is an ISO-8601 string.
 */

/** Async lifecycle every dashboard widget renders explicitly. */
export type WidgetStatus = "loading" | "error" | "empty" | "success";

/** Semantic accent for a stat tile — resolves to status-surface tokens. */
export type StatTone = "primary" | "success" | "warning" | "info" | "neutral";

/** The five headline metrics on the dashboard (mission scope). */
export type StatKey = "participants" | "competitions" | "applications" | "results" | "finance";

/** Direction of a period-over-period delta, for the trend affordance. */
export type TrendDirection = "up" | "down" | "flat";

export interface StatMetric {
  readonly key: StatKey;
  /** Raw numeric value. For `finance` this is an amount in minor units. */
  readonly value: number;
  /** Signed percentage change vs. the previous period (e.g. 12.5, -4). */
  readonly deltaPct: number;
  readonly trend: TrendDirection;
  /** ISO currency code — only meaningful for the `finance` metric. */
  readonly currency?: string;
}

/** Competition lifecycle (DATA-004 §competition), narrowed to display needs. */
export type CompetitionStatus =
  | "draft"
  | "published"
  | "open"
  | "submission"
  | "judging"
  | "results"
  | "archived"
  | "cancelled";

export interface CompetitionSummary {
  readonly id: string;
  readonly title: string;
  readonly status: CompetitionStatus;
  /** Number of applications received so far. */
  readonly applicationCount: number;
  /** ISO date the submission window closes. */
  readonly closesAt: string;
}

/** Application lifecycle (DATA-004 §application). */
export type ApplicationStatus =
  | "draft"
  | "submitted"
  | "under_review"
  | "accepted"
  | "rejected"
  | "waitlisted"
  | "withdrawn";

export interface ApplicationSummary {
  readonly id: string;
  /** Pseudonymized participant alias — never real PII (API-000 §10.3). */
  readonly participantAlias: string;
  readonly competitionTitle: string;
  readonly nomination: string;
  readonly status: ApplicationStatus;
  /** ISO timestamp the application was submitted. */
  readonly submittedAt: string;
}

/** Notification severity (Уведомление), maps to alert/badge tones. */
export type NotificationKind = "info" | "success" | "warning" | "danger";

export interface NotificationItem {
  readonly id: string;
  readonly kind: NotificationKind;
  readonly title: string;
  readonly body: string;
  /** ISO timestamp the notification was created. */
  readonly createdAt: string;
  readonly read: boolean;
}

/** What a scheduled dashboard event refers to (DATA-004 schedule/round/slot). */
export type EventKind =
  | "submission_deadline"
  | "judging_start"
  | "results"
  | "live_slot"
  | "reminder";

export interface UpcomingEvent {
  readonly id: string;
  readonly kind: EventKind;
  readonly title: string;
  /** Competition this event belongs to. */
  readonly competitionTitle: string;
  /** ISO timestamp the event occurs. */
  readonly startsAt: string;
}

/** Domain-event vocabulary for the activity feed (DATA-001 §10.4, past-tense). */
export type ActivityKind =
  | "application_submitted"
  | "application_accepted"
  | "performance_uploaded"
  | "scorecard_submitted"
  | "result_published"
  | "diploma_issued"
  | "payment_captured"
  | "competition_published";

export interface ActivityEvent {
  readonly id: string;
  readonly kind: ActivityKind;
  /** Human-readable subject (alias, competition title, etc.). */
  readonly subject: string;
  /** ISO timestamp the event occurred. */
  readonly occurredAt: string;
}
