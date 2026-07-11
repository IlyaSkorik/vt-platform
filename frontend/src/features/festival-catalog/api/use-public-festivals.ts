import { type UseQueryResult, useQuery } from "@tanstack/react-query";
import { type ApiError, toApiError } from "@/shared/api";
import type { PublicFestivalListEnvelope } from "@/shared/api/generated/model-public-catalog";
import { listPublicFestivals } from "@/shared/api/generated/public-catalog/public-catalog";
import type { Festival } from "../lib/types";
import { festivalCatalogKeys } from "./keys";

/** Unwrap the `{ data, meta }` envelope, tolerating an unexpected shape. */
function unwrapFestivals(body: unknown): Festival[] {
  if (body != null && typeof body === "object" && "data" in body) {
    const nested = (body as PublicFestivalListEnvelope).data;
    if (Array.isArray(nested)) {
      return nested;
    }
  }
  return [];
}

async function fetchPublicFestivals(signal?: AbortSignal): Promise<Festival[]> {
  try {
    const response = await listPublicFestivals(signal ? { signal } : {});
    return unwrapFestivals(response.data);
  } catch (error) {
    throw await toApiError(error);
  }
}

/**
 * Load the public festival catalog.
 *
 * A single cached read backs the whole screen; search, filtering and sorting run
 * client-side over the cached array, so those interactions never hit the network.
 * The list is cached for a minute — the catalog changes slowly and every
 * participant sees the same public data.
 */
export function usePublicFestivals(): UseQueryResult<Festival[], ApiError> {
  return useQuery<Festival[], ApiError>({
    queryKey: festivalCatalogKeys.list(),
    queryFn: ({ signal }) => fetchPublicFestivals(signal),
    staleTime: 60_000,
  });
}
