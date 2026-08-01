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

export type PlatformOrganization = {
  id: string;
  name: string;
  slug: string;
  status: OrganizationStatus;
  commissionPercent: string;
  createdAt: string;
};

export type OrganizationBreakdown = {
  organizationId: string | null;
  name: string;
  status: string;
  commissionPercent: string;
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
  commissionPercent: string;
};

export const platformKeys = {
  dashboard: (organizationId: string, competitionId: string) =>
    ["platform", "dashboard", organizationId, competitionId] as const,
  organizations: ["platform", "organizations"] as const,
};

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
      commissionPercent?: string;
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
