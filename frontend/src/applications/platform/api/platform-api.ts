/**
 * The platform operator's console API.
 *
 * Thin TanStack Query wrappers over `apiClient`, the same way the organizer
 * workspace talks to its own endpoints: these routes are operator-only and are
 * not part of the participant-facing generated SDK.
 *
 * Money arrives as decimal strings and is kept that way — it is only ever
 * displayed, and turning it into a JavaScript number would round the fees the
 * operator invoices against.
 */
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { apiClient } from "@/shared/api";

export type OrganizationStatus = "ACTIVE" | "SUSPENDED";

/** Which of the two commercial terms an organization is connected under. */
export type BillingModel = "COMMISSION_PERCENT" | "PER_PERFORMANCE_FEE";

/**
 * One band of a per-performance fee schedule: "2–5 participants cost 4.00".
 *
 * `maxParticipants` of `null` is the open-ended top band ("6 and up"), which every
 * schedule ends with. The amount stays a decimal string, like all money here.
 */
export type PerformanceFeeTier = {
  minParticipants: number;
  maxParticipants: number | null;
  amount: string;
};

export type PlatformOrganization = {
  id: string;
  name: string;
  slug: string;
  status: OrganizationStatus;
  /** Which of the two terms below is live; the other one is what was last agreed. */
  billingModel: BillingModel;
  commissionPercent: string;
  feeTiers: PerformanceFeeTier[];
  createdAt: string;
};

export type OrganizationBreakdown = {
  organizationId: string | null;
  name: string;
  status: string;
  billingModel: BillingModel;
  commissionPercent: string;
  feeTiers: PerformanceFeeTier[];
  competitions: number;
  applications: number;
  statusCounts: Record<string, number>;
  expectedFees: string;
  settledFees: string;
  expectedCommission: string;
  settledCommission: string;
};

export type CompetitionOption = {
  id: string;
  title: string;
  organizationId: string | null;
  organizationName: string;
};

export type PlatformDashboard = {
  statusCounts: Record<string, number>;
  applications: number;
  expectedFees: string;
  settledFees: string;
  expectedCommission: string;
  settledCommission: string;
  organizations: OrganizationBreakdown[];
  competitions: CompetitionOption[];
};

export type ConnectOrganizationInput = {
  name: string;
  slug?: string;
  ownerEmail: string;
  billingModel: BillingModel;
  commissionPercent?: string;
  feeTiers?: PerformanceFeeTier[];
};

/** One generation job inside a load-test run. */
export type LoadTestJob = {
  jobId: string;
  status: "PENDING" | "RUNNING" | "COMPLETED" | "FAILED";
  created: number;
  skipped: number;
  zipUrl: string | null;
  error: string | null;
};

export type LoadTestRun = {
  competitionId: string;
  title: string;
  createdAt: string;
  entries: number;
  nominations: number;
  diplomas: number;
  rendered: number;
  status: "PENDING" | "RUNNING" | "COMPLETED" | "FAILED";
  /** Wall clock from the first enqueue; still climbing while a job runs. */
  elapsedSeconds: number | null;
  msPerDiploma: number | null;
  jobs: LoadTestJob[];
};

export type LoadTestOverview = {
  runs: LoadTestRun[];
  templates: { id: string; name: string }[];
  totals: { runs: number; entries: number; diplomas: number };
  maxCount: number;
};

export type StartLoadTestInput = {
  count: number;
  nominations: number;
  templateId?: string;
  split: boolean;
  force: boolean;
};

export const platformKeys = {
  dashboard: (organizationId: string, competitionId: string) =>
    ["platform", "dashboard", organizationId, competitionId] as const,
  organizations: ["platform", "organizations"] as const,
  loadTest: ["platform", "loadtest", "diplomas"] as const,
};

/**
 * The load-test bench: what has been run, and what a new run can print over.
 *
 * Polled while anything is still in flight — generation is a background job, so
 * the only way the page learns it finished is by asking. Once everything is
 * terminal the polling stops rather than tapping the API forever.
 */
export function useLoadTestOverview() {
  return useQuery({
    queryKey: platformKeys.loadTest,
    queryFn: async (): Promise<LoadTestOverview> =>
      unwrap<LoadTestOverview>(await apiClient.get("platform/loadtest/diplomas")),
    refetchInterval: (query) => {
      const runs = query.state.data?.runs ?? [];
      return runs.some((run) => run.status === "PENDING" || run.status === "RUNNING")
        ? 3000
        : false;
    },
  });
}

/** Seed a synthetic festival and send it down the real generation path. */
export function useStartLoadTest() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (input: StartLoadTestInput): Promise<LoadTestRun> =>
      unwrap<LoadTestRun>(await apiClient.post("platform/loadtest/diplomas", { json: input })),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: platformKeys.loadTest });
    },
  });
}

/** Remove one run, or every run when `competitionId` is omitted. */
export function useCleanupLoadTest() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (
      competitionId?: string,
    ): Promise<{ runs: number; files: number; diplomas: number; entries: number }> => {
      const query = competitionId ? `?competitionId=${encodeURIComponent(competitionId)}` : "";
      return unwrap(await apiClient.delete(`platform/loadtest/diplomas${query}`));
    },
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: platformKeys.loadTest });
    },
  });
}

async function unwrap<T>(response: Response): Promise<T> {
  const body = (await response.json()) as { data: T };
  return body.data;
}

/** The pipeline and the money behind it, across every connected organization. */
export function usePlatformDashboard(organizationId: string, competitionId: string) {
  return useQuery({
    queryKey: platformKeys.dashboard(organizationId, competitionId),
    queryFn: async (): Promise<PlatformDashboard> => {
      const search = new URLSearchParams();
      if (organizationId) search.set("organizationId", organizationId);
      if (competitionId) search.set("competitionId", competitionId);
      const query = search.toString();
      return unwrap<PlatformDashboard>(
        await apiClient.get(`platform/dashboard${query ? `?${query}` : ""}`),
      );
    },
  });
}

export function usePlatformOrganizations() {
  return useQuery({
    queryKey: platformKeys.organizations,
    queryFn: async (): Promise<PlatformOrganization[]> =>
      unwrap<PlatformOrganization[]>(await apiClient.get("platform/organizations")),
  });
}

/** Connect an organization and send its owner the invitation that hands them the keys. */
export function useConnectOrganization() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (input: ConnectOrganizationInput): Promise<PlatformOrganization> =>
      unwrap<PlatformOrganization>(await apiClient.post("platform/organizations", { json: input })),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: platformKeys.organizations });
      void queryClient.invalidateQueries({ queryKey: ["platform", "dashboard"] });
    },
  });
}

/** Change what an organization owes the platform, or suspend/reactivate it. */
export function useUpdateOrganization() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (input: {
      id: string;
      billingModel?: BillingModel;
      commissionPercent?: string;
      feeTiers?: PerformanceFeeTier[];
      status?: OrganizationStatus;
    }): Promise<PlatformOrganization> => {
      const { id, ...payload } = input;
      return unwrap<PlatformOrganization>(
        await apiClient.patch(`platform/organizations/${id}`, { json: payload }),
      );
    },
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: platformKeys.organizations });
      void queryClient.invalidateQueries({ queryKey: ["platform", "dashboard"] });
    },
  });
}

/** The problem detail a refused platform call carries, in the operator's language. */
export async function refusalMessage(error: unknown, fallback: string): Promise<string> {
  const response = (error as { response?: Response })?.response;
  if (!response) {
    return fallback;
  }
  const body = (await response.json().catch(() => null)) as {
    detail?: string;
    title?: string;
  } | null;
  return body?.detail ?? body?.title ?? fallback;
}
