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
  /** Costs recorded against this organization. Usually "0.00". */
  expenses: string;
  /** Commission actually paid, less those costs. Negative is an ordinary answer. */
  profit: string;
  /** The same subtraction against commission still expected. */
  potentialProfit: string;
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
  /** Every recorded cost in scope, attributed to a client or not. */
  expenses: string;
  /** The part of it carried for no particular client — hosting, an accountant. */
  unattributedExpenses: string;
  /** Commission in hand, less the costs. The screen's whole point. */
  profit: string;
  /** The same, against the commission still expected. */
  potentialProfit: string;
  /**
   * False under a competition filter. Expenses are recorded per organization and
   * never per festival, so the figures above are zeroed rather than guessed at and
   * the console hides the profit block instead of showing a number it invented.
   */
  expensesApply: boolean;
  organizations: OrganizationBreakdown[];
  competitions: CompetitionOption[];
};

/**
 * What kind of cost a row in the expense book is.
 *
 * Mirrors `ExpenseCategory` on the server. Spelled out rather than fetched, like
 * the module list above: the console has to label each one in Russian anyway, and
 * an article the interface cannot name is one it cannot usefully offer.
 */
export type ExpenseCategory =
  | "INFRASTRUCTURE"
  | "MARKETING"
  | "PAYROLL"
  | "CONTRACTORS"
  | "EQUIPMENT"
  | "EVENT"
  | "BANK"
  | "TAX"
  | "OTHER";

/** Every article, in the order the form offers them. */
export const EXPENSE_CATEGORIES: ExpenseCategory[] = [
  "INFRASTRUCTURE",
  "MARKETING",
  "PAYROLL",
  "CONTRACTORS",
  "EQUIPMENT",
  "EVENT",
  "BANK",
  "TAX",
  "OTHER",
];

/** What each article is called on the form and in the breakdown. */
export const EXPENSE_CATEGORY_LABELS: Record<ExpenseCategory, string> = {
  INFRASTRUCTURE: "Хостинг и инфраструктура",
  MARKETING: "Реклама и продвижение",
  PAYROLL: "Оплата труда",
  CONTRACTORS: "Услуги подрядчиков",
  EQUIPMENT: "Оборудование",
  EVENT: "Проведение мероприятий",
  BANK: "Банковские комиссии",
  TAX: "Налоги и сборы",
  OTHER: "Прочее",
};

/** One recorded cost, as the ledger reads it back. */
export type PlatformExpense = {
  id: string;
  amount: string;
  category: ExpenseCategory;
  /** What the money went on — the line the total is read back through. */
  purpose: string;
  /** The day the money went, not the day it was typed in (`YYYY-MM-DD`). */
  spentAt: string;
  note: string;
  /** `null` is a cost the platform carried itself, not a missing attribution. */
  organizationId: string | null;
  organizationName: string | null;
  createdAt: string;
  updatedAt: string;
};

export type ExpenseCategoryTotal = {
  category: ExpenseCategory;
  amount: string;
  count: number;
};

/** The expenses matching the operator's filters, with the totals of *those* rows. */
export type ExpenseLedger = {
  expenses: PlatformExpense[];
  total: string;
  byCategory: ExpenseCategoryTotal[];
  /** The list was cut short — a truncated total is a wrong total, so it says so. */
  truncated: boolean;
};

/** The filters on the ledger screen. Every one of them optional. */
export type ExpenseFilters = {
  organizationId?: string;
  category?: string;
  from?: string;
  to?: string;
};

export type RecordExpenseInput = {
  amount: string;
  category: ExpenseCategory;
  purpose: string;
  spentAt: string;
  /** Omitted means the platform carried this cost itself. */
  organizationId?: string;
  note?: string;
};

/**
 * The platform's head counts: cabinets, registry participants, teachers.
 *
 * Each figure carries the subset worth naming beside it rather than netted out —
 * archived participants are still in the registry, and a cabinet with an
 * unconfirmed address is still registered.
 *
 * Platform-wide, and not affected by the dashboard's organization/competition
 * filters: a cabinet belongs to a person, not to a festival. That is why it is a
 * separate read.
 */
export type PlatformAudience = {
  cabinets: { total: number; emailVerified: number };
  participants: { total: number; archived: number };
  teachers: { total: number; archived: number };
};

/**
 * One switchable part of the platform.
 *
 * Mirrors `OrganizationModule` on the server. The list is short and changes with a
 * release, so it is spelled out rather than fetched: the console has to label each
 * one in Russian anyway, and a module the interface cannot name is one it cannot
 * usefully offer.
 */
export type PlatformModule =
  | "COMPETITIONS"
  | "APPLICATIONS"
  | "PARTICIPANTS"
  | "JURY"
  | "PROGRAMS"
  | "DIPLOMAS"
  | "VOTING"
  | "FINANCE"
  | "ANALYTICS";

/** Every module, in the order the console shows them. */
export const PLATFORM_MODULES: PlatformModule[] = [
  "COMPETITIONS",
  "APPLICATIONS",
  "PARTICIPANTS",
  "JURY",
  "PROGRAMS",
  "DIPLOMAS",
  "VOTING",
  "FINANCE",
  "ANALYTICS",
];

/** What each module is called on the switchboard and in the organizer's own menu. */
export const MODULE_LABELS: Record<PlatformModule, string> = {
  COMPETITIONS: "Фестивали",
  APPLICATIONS: "Заявки",
  PARTICIPANTS: "Участники",
  JURY: "Жюри",
  PROGRAMS: "Программа",
  DIPLOMAS: "Дипломы",
  VOTING: "Зрительское голосование",
  FINANCE: "Финансы",
  ANALYTICS: "Аналитика",
};

/**
 * The ready-made sets an organization gets connected on.
 *
 * Presets live here and not on the server on purpose: "only the audience vote" is
 * a sales decision that will be re-cut more often than the code ships, and the API
 * stays a plain list of modules that means exactly what it says.
 */
export type ModulePreset = { id: string; label: string; modules: PlatformModule[] };

/** What an organization gets when nobody narrowed it — and the server's own default. */
export const FULL_ACCESS_PRESET: ModulePreset = {
  id: "full",
  label: "Полный доступ",
  modules: [...PLATFORM_MODULES],
};

export const MODULE_PRESETS: ModulePreset[] = [
  FULL_ACCESS_PRESET,
  { id: "voting", label: "Только голосование", modules: ["VOTING"] },
  {
    id: "festival",
    label: "Фестиваль без финансов",
    modules: ["COMPETITIONS", "APPLICATIONS", "PARTICIPANTS", "JURY", "PROGRAMS", "DIPLOMAS"],
  },
];

/** The preset with this id, falling back to full access for an unknown one. */
export function modulePreset(id: string): ModulePreset {
  return MODULE_PRESETS.find((preset) => preset.id === id) ?? FULL_ACCESS_PRESET;
}

/** One module as the switchboard shows it: its state, and when it last changed. */
export type OrganizationModuleRow = {
  module: PlatformModule;
  enabled: boolean;
  enabledAt: string | null;
  disabledAt: string | null;
};

export type OrganizationModules = {
  organizationId: string;
  modules: OrganizationModuleRow[];
};

export type ConnectOrganizationInput = {
  name: string;
  slug?: string;
  ownerEmail: string;
  billingModel: BillingModel;
  commissionPercent?: string;
  feeTiers?: PerformanceFeeTier[];
  /** Omitted means full access — the server's own default, not repeated here. */
  modules?: PlatformModule[];
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
  audience: ["platform", "audience"] as const,
  organizations: ["platform", "organizations"] as const,
  organizationModules: (organizationId: string) =>
    ["platform", "organizations", organizationId, "modules"] as const,
  loadTest: ["platform", "loadtest", "diplomas"] as const,
  expenses: (filters: ExpenseFilters) =>
    [
      "platform",
      "expenses",
      filters.organizationId ?? "",
      filters.category ?? "",
      filters.from ?? "",
      filters.to ?? "",
    ] as const,
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

/**
 * The platform's expense book, narrowed by whichever filters are set.
 *
 * The totals come back with the rows and are of *those* rows: they move with the
 * filters, which is what makes "how much did marketing cost this spring" a question
 * the screen answers without a second request.
 */
export function usePlatformExpenses(filters: ExpenseFilters) {
  return useQuery({
    queryKey: platformKeys.expenses(filters),
    queryFn: async (): Promise<ExpenseLedger> => {
      const search = new URLSearchParams();
      if (filters.organizationId) search.set("organizationId", filters.organizationId);
      if (filters.category) search.set("category", filters.category);
      if (filters.from) search.set("from", filters.from);
      if (filters.to) search.set("to", filters.to);
      const query = search.toString();
      return unwrap<ExpenseLedger>(
        await apiClient.get(`platform/expenses${query ? `?${query}` : ""}`),
      );
    },
  });
}

/**
 * Every write to the ledger invalidates the dashboard too.
 *
 * The profit on that screen is this table subtracted from the commission, so a cost
 * entered here and a summary that still shows yesterday's difference would be the
 * console disagreeing with itself.
 */
function useLedgerInvalidation() {
  const queryClient = useQueryClient();
  return () => {
    void queryClient.invalidateQueries({ queryKey: ["platform", "expenses"] });
    void queryClient.invalidateQueries({ queryKey: ["platform", "dashboard"] });
  };
}

/** Enter one cost into the platform's books. */
export function useRecordExpense() {
  const invalidate = useLedgerInvalidation();
  return useMutation({
    mutationFn: async (input: RecordExpenseInput): Promise<PlatformExpense> =>
      unwrap<PlatformExpense>(await apiClient.post("platform/expenses", { json: input })),
    onSuccess: invalidate,
  });
}

/**
 * Correct a recorded cost.
 *
 * `organizationId: null` sent explicitly moves it off the client and onto the
 * platform; leaving the key out entirely leaves the attribution as it was. The
 * server tells the two apart the same way.
 */
export function useAmendExpense() {
  const invalidate = useLedgerInvalidation();
  return useMutation({
    mutationFn: async (
      input: { id: string } & Partial<Omit<RecordExpenseInput, "organizationId">> & {
          organizationId?: string | null;
        },
    ): Promise<PlatformExpense> => {
      const { id, ...payload } = input;
      return unwrap<PlatformExpense>(
        await apiClient.patch(`platform/expenses/${id}`, { json: payload }),
      );
    },
    onSuccess: invalidate,
  });
}

/** Strike a cost from the books. The row stays; the totals stop counting it. */
export function useRemoveExpense() {
  const invalidate = useLedgerInvalidation();
  return useMutation({
    mutationFn: async (id: string): Promise<void> => {
      await apiClient.delete(`platform/expenses/${id}`);
    },
    onSuccess: invalidate,
  });
}

/** How many cabinets, registry participants and teachers the platform holds. */
export function usePlatformAudience() {
  return useQuery({
    queryKey: platformKeys.audience,
    queryFn: async (): Promise<PlatformAudience> =>
      unwrap<PlatformAudience>(await apiClient.get("platform/audience")),
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

/** Which parts of the platform one organization holds, and since when. */
export function useOrganizationModules(organizationId: string | null) {
  return useQuery({
    queryKey: platformKeys.organizationModules(organizationId ?? ""),
    enabled: organizationId !== null,
    queryFn: async (): Promise<OrganizationModules> =>
      unwrap<OrganizationModules>(
        await apiClient.get(`platform/organizations/${organizationId}/modules`),
      ),
  });
}

/**
 * Set an organization's modules to exactly this set.
 *
 * A PUT of the whole switchboard, matching the endpoint: everything listed is on
 * afterwards and everything else is off. Sending the set unchanged is a no-op on
 * the server and keeps the date each module was first connected.
 */
export function useSetOrganizationModules() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (input: {
      id: string;
      modules: PlatformModule[];
    }): Promise<OrganizationModules> =>
      unwrap<OrganizationModules>(
        await apiClient.put(`platform/organizations/${input.id}/modules`, {
          json: { modules: input.modules },
        }),
      ),
    onSuccess: (_data, input) => {
      void queryClient.invalidateQueries({
        queryKey: platformKeys.organizationModules(input.id),
      });
      // The organizer's own `/users/me` now answers differently; anything this
      // console caches about the organization is a projection over the same fact.
      void queryClient.invalidateQueries({ queryKey: platformKeys.organizations });
    },
  });
}

/** Cyrillic anywhere in a message is the sign it was written for a person to read. */
const CYRILLIC = /[\u0400-\u04FF]/;

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
  // `title` is English and stable per problem type; only a Russian `detail` is
  // wording meant for the operator, so anything else falls back to the caller's.
  const said = body?.detail ?? body?.title;
  return said && CYRILLIC.test(said) ? said : fallback;
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
