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

/** What the eraser can be pointed at. Mirrors `TARGETS` on the server. */
export type PurgeKind =
  | "festival"
  | "program"
  | "application"
  | "organization"
  | "template"
  | "account"
  | "participant"
  | "teacher";

/** One erasable thing, as the console names it in a list and in the dialog. */
export type PurgeTarget = {
  kind: PurgeKind;
  id: string;
  /** What the operator has to retype to confirm — a title, a name, an email. */
  label: string;
  /** The second line that tells two similarly named rows apart. */
  hint: string;
};

/** One table's contribution to the plan: the machine name, and the human one. */
export type PurgeRow = {
  table: string;
  label: string;
  count: number;
};

/**
 * Everything the deletion would take — or, coming back from a `DELETE`, took.
 *
 * The same shape both ways on purpose: the numbers the operator agreed to are the
 * numbers reported back, and a report assembled after the fact could only read zero.
 */
export type PurgePlan = {
  target: PurgeTarget;
  rows: PurgeRow[];
  total: number;
  files: number;
  warnings: string[];
};

export const platformKeys = {
  dashboard: (organizationId: string, competitionId: string) =>
    ["platform", "dashboard", organizationId, competitionId] as const,
  organizations: ["platform", "organizations"] as const,
  loadTest: ["platform", "loadtest", "diplomas"] as const,
  purgeSearch: (kind: PurgeKind, query: string) =>
    ["platform", "purge", "search", kind, query] as const,
  purgePlan: (kind: PurgeKind, id: string) => ["platform", "purge", "plan", kind, id] as const,
};

/** How short a query may get before it stops being a search for one known thing. */
export const PURGE_MIN_QUERY = 2;

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

/**
 * Candidates for the eraser, by name, email or id.
 *
 * Idle until the query is long enough to mean something: a one-letter search over
 * every account on the platform is a listing, and this screen must not offer one.
 */
export function usePurgeSearch(kind: PurgeKind, query: string) {
  const trimmed = query.trim();
  return useQuery({
    queryKey: platformKeys.purgeSearch(kind, trimmed),
    enabled: trimmed.length >= PURGE_MIN_QUERY,
    queryFn: async (): Promise<PurgeTarget[]> => {
      const search = new URLSearchParams({ target: kind, query: trimmed });
      return unwrap<PurgeTarget[]>(
        await apiClient.get(`platform/purge/search?${search.toString()}`),
      );
    },
  });
}

/**
 * What erasing this object would delete. A read — nothing happens until the
 * mutation below runs, and the dialog shows this before it offers the button.
 */
export function usePurgePlan(kind: PurgeKind, id: string | null) {
  return useQuery({
    queryKey: platformKeys.purgePlan(kind, id ?? ""),
    enabled: id !== null,
    queryFn: async (): Promise<PurgePlan> =>
      unwrap<PurgePlan>(await apiClient.get(`platform/purge/${kind}/${id}`)),
  });
}

/**
 * Erase the object. Irreversible — the rows go from the database and the files go
 * from storage. `confirm` carries the object's own name back, which the server
 * checks again on its side.
 */
export function usePurge() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (input: {
      kind: PurgeKind;
      id: string;
      confirm: string;
    }): Promise<PurgePlan> => {
      const search = new URLSearchParams({ confirm: input.confirm });
      return unwrap<PurgePlan>(
        await apiClient.delete(`platform/purge/${input.kind}/${input.id}?${search.toString()}`),
      );
    },
    onSuccess: () => {
      // Everything the console shows is a projection over what just went.
      void queryClient.invalidateQueries({ queryKey: ["platform"] });
    },
  });
}
