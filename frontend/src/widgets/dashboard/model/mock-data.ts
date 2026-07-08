/**
 * Deterministic mock fixtures for the dashboard.
 *
 * No backend exists for these widgets yet, so the query layer resolves against
 * these fixtures (see `../api/queries`). Timestamps are computed relative to a
 * fixed "now" captured at module load so relative-time rendering ("2 часа
 * назад") stays sensible without depending on wall-clock drift between renders.
 */

import type {
  ActivityEvent,
  ApplicationSummary,
  CompetitionSummary,
  NotificationItem,
  StatMetric,
  UpcomingEvent,
} from "./types";

const NOW = Date.now();
const MINUTE = 60_000;
const HOUR = 60 * MINUTE;
const DAY = 24 * HOUR;

/** ISO string `offsetMs` from the fixed baseline (negative = past). */
function at(offsetMs: number): string {
  return new Date(NOW + offsetMs).toISOString();
}

export const MOCK_STATS: readonly StatMetric[] = [
  { key: "participants", value: 1284, deltaPct: 12.5, trend: "up" },
  { key: "competitions", value: 18, deltaPct: 5.0, trend: "up" },
  { key: "applications", value: 3472, deltaPct: -3.2, trend: "down" },
  { key: "results", value: 946, deltaPct: 0, trend: "flat" },
  { key: "finance", value: 4_820_000, deltaPct: 8.4, trend: "up", currency: "BYN" },
];

export const MOCK_COMPETITIONS: readonly CompetitionSummary[] = [
  {
    id: "c-1",
    title: "Весенний вокальный конкурс",
    status: "submission",
    applicationCount: 214,
    closesAt: at(6 * DAY),
  },
  {
    id: "c-2",
    title: "Юные художники — 2026",
    status: "judging",
    applicationCount: 389,
    closesAt: at(-2 * DAY),
  },
  {
    id: "c-3",
    title: "Танцевальная весна",
    status: "open",
    applicationCount: 57,
    closesAt: at(19 * DAY),
  },
  {
    id: "c-4",
    title: "Кубок инструменталистов",
    status: "results",
    applicationCount: 502,
    closesAt: at(-11 * DAY),
  },
  {
    id: "c-5",
    title: "Фестиваль театральных студий",
    status: "published",
    applicationCount: 0,
    closesAt: at(33 * DAY),
  },
];

export const MOCK_APPLICATIONS: readonly ApplicationSummary[] = [
  {
    id: "a-1",
    participantAlias: "Участник #A19F",
    competitionTitle: "Весенний вокальный конкурс",
    nomination: "Эстрадный вокал",
    status: "under_review",
    submittedAt: at(-35 * MINUTE),
  },
  {
    id: "a-2",
    participantAlias: "Участник #7C2E",
    competitionTitle: "Юные художники — 2026",
    nomination: "Рисунок",
    status: "accepted",
    submittedAt: at(-3 * HOUR),
  },
  {
    id: "a-3",
    participantAlias: "Участник #D480",
    competitionTitle: "Танцевальная весна",
    nomination: "Современный танец",
    status: "submitted",
    submittedAt: at(-8 * HOUR),
  },
  {
    id: "a-4",
    participantAlias: "Участник #55B1",
    competitionTitle: "Кубок инструменталистов",
    nomination: "Фортепиано",
    status: "waitlisted",
    submittedAt: at(-1 * DAY),
  },
  {
    id: "a-5",
    participantAlias: "Участник #E3A7",
    competitionTitle: "Весенний вокальный конкурс",
    nomination: "Народный вокал",
    status: "rejected",
    submittedAt: at(-2 * DAY),
  },
];

export const MOCK_NOTIFICATIONS: readonly NotificationItem[] = [
  {
    id: "n-1",
    kind: "warning",
    title: "Судейство завершается завтра",
    body: "«Юные художники — 2026»: 12 работ ожидают оценки жюри.",
    createdAt: at(-25 * MINUTE),
    read: false,
  },
  {
    id: "n-2",
    kind: "success",
    title: "Результаты опубликованы",
    body: "«Кубок инструменталистов»: итоги доступны участникам.",
    createdAt: at(-2 * HOUR),
    read: false,
  },
  {
    id: "n-3",
    kind: "info",
    title: "Новая заявка",
    body: "«Танцевальная весна»: подана заявка в номинацию «Современный танец».",
    createdAt: at(-5 * HOUR),
    read: false,
  },
  {
    id: "n-4",
    kind: "danger",
    title: "Платёж не прошёл",
    body: "Заявка #55B1: оплата организационного взноса отклонена банком.",
    createdAt: at(-1 * DAY),
    read: true,
  },
];

export const MOCK_EVENTS: readonly UpcomingEvent[] = [
  {
    id: "e-1",
    kind: "submission_deadline",
    title: "Закрытие приёма заявок",
    competitionTitle: "Весенний вокальный конкурс",
    startsAt: at(6 * DAY),
  },
  {
    id: "e-2",
    kind: "judging_start",
    title: "Старт оценки жюри",
    competitionTitle: "Танцевальная весна",
    startsAt: at(2 * DAY),
  },
  {
    id: "e-3",
    kind: "results",
    title: "Публикация итогов",
    competitionTitle: "Юные художники — 2026",
    startsAt: at(4 * DAY),
  },
  {
    id: "e-4",
    kind: "live_slot",
    title: "Гала-концерт финалистов",
    competitionTitle: "Кубок инструменталистов",
    startsAt: at(9 * DAY),
  },
];

export const MOCK_ACTIVITY: readonly ActivityEvent[] = [
  {
    id: "t-1",
    kind: "application_submitted",
    subject: "Участник #A19F",
    occurredAt: at(-18 * MINUTE),
  },
  {
    id: "t-2",
    kind: "scorecard_submitted",
    subject: "«Юные художники — 2026»",
    occurredAt: at(-1 * HOUR),
  },
  {
    id: "t-3",
    kind: "result_published",
    subject: "«Кубок инструменталистов»",
    occurredAt: at(-4 * HOUR),
  },
  { id: "t-4", kind: "diploma_issued", subject: "Участник #7C2E", occurredAt: at(-7 * HOUR) },
  { id: "t-5", kind: "payment_captured", subject: "Заявка #D480", occurredAt: at(-1 * DAY) },
  {
    id: "t-6",
    kind: "competition_published",
    subject: "«Фестиваль театральных студий»",
    occurredAt: at(-2 * DAY),
  },
];
