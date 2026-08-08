/**
 * The organizer's operational overview, read from the applications workspace.
 *
 * No endpoint of its own: `staff/applications/workspace` already computes the queue
 * counts, the visible competitions and every application card the workspace screen
 * renders, so the dashboard asks the same question with no filters rather than
 * adding a second projection that could disagree with the screen it links to.
 *
 * A narrow read model on purpose — the dashboard needs a fraction of what the
 * workspace returns, and naming that fraction keeps the summary from quietly
 * growing into a second copy of the workspace page.
 */
import { useQuery } from "@tanstack/react-query";

import { apiClient } from "@/shared/api";

/** A work queue and how much is sitting in it right now. */
export type OverviewQueue = {
  key: string;
  label: string;
  count: number;
};

/** One application card, reduced to what a summary row shows. */
export type OverviewApplication = {
  id: string;
  applicationId?: string | null;
  applicationNumber: string;
  competition: string;
  organization?: string | null;
  status: string;
  queue: string;
  paymentStatus: string;
  performancesCount: number;
  participantsCount: number;
  submissionDate: string;
  lastActivity: string;
  badges?: { hasCorrections?: boolean; hasMissingFiles?: boolean };
};

export type StaffOverview = {
  queues: OverviewQueue[];
  competitions?: Array<{ id: string; title: string; status: string }>;
  applications: OverviewApplication[];
};

export const staffOverviewKeys = {
  all: ["staff", "overview"] as const,
};

async function fetchOverview(signal?: AbortSignal): Promise<StaffOverview> {
  // Deliberately unfiltered: the queue counts are computed over every visible
  // application, and the summary is about the whole desk rather than one queue.
  const response = await apiClient.get("staff/applications/workspace", signal ? { signal } : {});
  const body = (await response.json()) as { data: StaffOverview };
  return body.data;
}

/** The organizer's desk in one request. */
export function useStaffOverview() {
  return useQuery<StaffOverview>({
    queryKey: staffOverviewKeys.all,
    queryFn: ({ signal }) => fetchOverview(signal),
    // Slower than the workspace screen's ten seconds: nobody works from the summary,
    // they pass through it, and it is mounted on the first screen after every login.
    staleTime: 60_000,
    refetchInterval: 120_000,
    refetchIntervalInBackground: false,
  });
}
