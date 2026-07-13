/**
 * Participant Registry data access — the single query layer over the
 * `participants/registry*` REST endpoints, shared by the registry pages and the
 * wizard's participant picker. The query-key namespace is shared so both surfaces
 * read (and invalidate) the same cache.
 */

import { type UseQueryResult, useQuery } from "@tanstack/react-query";
import { type ApiError, apiClient, toApiError } from "@/shared/api";

import type { Organization, Participant } from "./model";

interface Envelope<T> {
  data: T;
}

export const participantRegistryKeys = {
  participants: (params: URLSearchParams) =>
    ["participant-registry", "participants", params.toString()] as const,
  participant: (participantId: string) =>
    ["participant-registry", "participant", participantId] as const,
  organizations: ["participant-registry", "organizations"] as const,
};

export async function fetchParticipants(params: URLSearchParams): Promise<Participant[]> {
  try {
    const response = await apiClient.get(`participants/registry?${params.toString()}`);
    const payload = (await response.json()) as Envelope<Participant[]>;
    return payload.data;
  } catch (error) {
    throw await toApiError(error);
  }
}

export async function fetchParticipant(participantId: string): Promise<Participant> {
  try {
    const response = await apiClient.get(`participants/registry/${participantId}`);
    const payload = (await response.json()) as Envelope<Participant>;
    return payload.data;
  } catch (error) {
    throw await toApiError(error);
  }
}

export async function fetchOrganizations(includeArchived = false): Promise<Organization[]> {
  try {
    const suffix = includeArchived ? "?includeArchived=true" : "";
    const response = await apiClient.get(`participants/organizations${suffix}`);
    const payload = (await response.json()) as Envelope<Organization[]>;
    return payload.data;
  } catch (error) {
    throw await toApiError(error);
  }
}

/**
 * Read the current user's registry participants (optionally filtered by a search
 * query). Used by the wizard participant picker; shares the registry cache.
 */
export function useParticipants(search = ""): UseQueryResult<Participant[], ApiError> {
  const params = new URLSearchParams();
  const trimmed = search.trim();
  if (trimmed) {
    params.set("q", trimmed);
  }
  return useQuery({
    queryKey: participantRegistryKeys.participants(params),
    queryFn: () => fetchParticipants(params),
  });
}
