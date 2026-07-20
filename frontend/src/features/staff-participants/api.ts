import { type UseQueryResult, useQuery } from "@tanstack/react-query";
import { type ApiError, apiClient, toApiError } from "@/shared/api";
import type { RegistryFilters, RegistryList, RegistryParticipantDetail } from "./model";

interface ListEnvelope {
  data: RegistryList["rows"];
  meta?: {
    total?: number;
    facets?: RegistryList["facets"];
    competitions?: RegistryList["competitions"];
    requestId?: string;
  };
}

interface DetailEnvelope {
  data: RegistryParticipantDetail;
}

const EMPTY_FACETS: RegistryList["facets"] = {
  total: 0,
  solo: 0,
  collective: 0,
  withDocuments: 0,
  female: 0,
  male: 0,
};

/** Serialize filters into a stable query string (used both to fetch and to key). */
export function toSearchParams(filters: RegistryFilters): URLSearchParams {
  const params = new URLSearchParams();
  if (filters.q?.trim()) {
    params.set("q", filters.q.trim());
  }
  if (filters.gender) {
    params.set("gender", filters.gender);
  }
  if (filters.ageMin?.trim()) {
    params.set("ageMin", filters.ageMin.trim());
  }
  if (filters.ageMax?.trim()) {
    params.set("ageMax", filters.ageMax.trim());
  }
  if (filters.competitionId) {
    params.set("competitionId", filters.competitionId);
  }
  if (filters.organization?.trim()) {
    params.set("organization", filters.organization.trim());
  }
  if (filters.participantType) {
    params.set("participantType", filters.participantType);
  }
  if (filters.hasDocuments) {
    params.set("hasDocuments", "true");
  }
  return params;
}

async function request<T>(path: string, options?: Parameters<typeof apiClient>[1]): Promise<T> {
  try {
    return await apiClient(path, options).json<T>();
  } catch (error) {
    throw await toApiError(error);
  }
}

export const staffParticipantsKeys = {
  all: ["staff-participants"] as const,
  list: (query: string) => [...staffParticipantsKeys.all, "list", query] as const,
  detail: (key: string) => [...staffParticipantsKeys.all, "detail", key] as const,
};

export async function fetchStaffParticipants(filters: RegistryFilters): Promise<RegistryList> {
  const query = toSearchParams(filters).toString();
  const body = await request<ListEnvelope>(`staff/participants${query ? `?${query}` : ""}`);
  const rows = body.data;
  return {
    rows,
    total: body.meta?.total ?? rows.length,
    facets: body.meta?.facets ?? EMPTY_FACETS,
    competitions: body.meta?.competitions ?? [],
  };
}

export async function fetchStaffParticipant(key: string): Promise<RegistryParticipantDetail> {
  const body = await request<DetailEnvelope>(`staff/participants/${encodeURIComponent(key)}`);
  return body.data;
}

/** Fetch the CSV export as text (the caller triggers the browser download). */
export async function fetchStaffParticipantsCsv(filters: RegistryFilters): Promise<string> {
  const query = toSearchParams(filters).toString();
  try {
    return await apiClient(`staff/participants/export${query ? `?${query}` : ""}`).text();
  } catch (error) {
    throw await toApiError(error);
  }
}

export function useStaffParticipants(
  filters: RegistryFilters,
): UseQueryResult<RegistryList, ApiError> {
  const query = toSearchParams(filters).toString();
  return useQuery<RegistryList, ApiError>({
    queryKey: staffParticipantsKeys.list(query),
    queryFn: () => fetchStaffParticipants(filters),
    placeholderData: (previous) => previous,
    staleTime: 15_000,
  });
}

export function useStaffParticipant(
  key: string | null,
): UseQueryResult<RegistryParticipantDetail, ApiError> {
  return useQuery<RegistryParticipantDetail, ApiError>({
    enabled: key != null,
    queryKey: staffParticipantsKeys.detail(key ?? ""),
    queryFn: () => fetchStaffParticipant(key ?? ""),
  });
}
