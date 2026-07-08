/**
 * Dashboard data layer — mocked TanStack Query hooks.
 *
 * The dashboard's backend endpoints are not implemented yet, so each hook
 * resolves against the in-repo fixtures (`../model/mock-data`) through a small
 * abortable delay that mimics a network round-trip. Swapping these `queryFn`s
 * for the generated SDK later is a one-line change per hook; the widgets, keys
 * and cache semantics stay identical.
 *
 * Query keys are namespaced under `["dashboard", …]` so the whole screen can be
 * invalidated at once, and each hook carries its own key so widgets refetch
 * independently.
 */

import { type UseQueryResult, useQuery } from "@tanstack/react-query";
import type {
  ActivityEvent,
  ApplicationSummary,
  CompetitionSummary,
  NotificationItem,
  StatMetric,
  UpcomingEvent,
} from "../model";
import {
  MOCK_ACTIVITY,
  MOCK_APPLICATIONS,
  MOCK_COMPETITIONS,
  MOCK_EVENTS,
  MOCK_NOTIFICATIONS,
  MOCK_STATS,
} from "../model/mock-data";

/** Simulated latency (ms) — long enough to show a skeleton, short enough for tests. */
const MOCK_LATENCY = 400;

/** Query keys for every dashboard resource. */
export const dashboardKeys = {
  all: ["dashboard"] as const,
  stats: ["dashboard", "stats"] as const,
  competitions: ["dashboard", "competitions"] as const,
  applications: ["dashboard", "applications"] as const,
  notifications: ["dashboard", "notifications"] as const,
  events: ["dashboard", "events"] as const,
  activity: ["dashboard", "activity"] as const,
} as const;

/**
 * Resolve `value` after a short delay, rejecting early if the query is aborted.
 * Mirrors the cancellation contract real `queryFn`s honour via `signal`.
 */
function mockRequest<T>(value: T, signal?: AbortSignal): Promise<T> {
  return new Promise<T>((resolve, reject) => {
    if (signal?.aborted) {
      reject(new DOMException("Aborted", "AbortError"));
      return;
    }
    const timer = setTimeout(() => resolve(value), MOCK_LATENCY);
    signal?.addEventListener(
      "abort",
      () => {
        clearTimeout(timer);
        reject(new DOMException("Aborted", "AbortError"));
      },
      { once: true },
    );
  });
}

export function useDashboardStats(): UseQueryResult<readonly StatMetric[]> {
  return useQuery({
    queryKey: dashboardKeys.stats,
    queryFn: ({ signal }) => mockRequest(MOCK_STATS, signal),
  });
}

export function useRecentCompetitions(): UseQueryResult<readonly CompetitionSummary[]> {
  return useQuery({
    queryKey: dashboardKeys.competitions,
    queryFn: ({ signal }) => mockRequest(MOCK_COMPETITIONS, signal),
  });
}

export function useRecentApplications(): UseQueryResult<readonly ApplicationSummary[]> {
  return useQuery({
    queryKey: dashboardKeys.applications,
    queryFn: ({ signal }) => mockRequest(MOCK_APPLICATIONS, signal),
  });
}

export function useNotifications(): UseQueryResult<readonly NotificationItem[]> {
  return useQuery({
    queryKey: dashboardKeys.notifications,
    queryFn: ({ signal }) => mockRequest(MOCK_NOTIFICATIONS, signal),
  });
}

export function useUpcomingEvents(): UseQueryResult<readonly UpcomingEvent[]> {
  return useQuery({
    queryKey: dashboardKeys.events,
    queryFn: ({ signal }) => mockRequest(MOCK_EVENTS, signal),
  });
}

export function useActivityFeed(): UseQueryResult<readonly ActivityEvent[]> {
  return useQuery({
    queryKey: dashboardKeys.activity,
    queryFn: ({ signal }) => mockRequest(MOCK_ACTIVITY, signal),
  });
}
