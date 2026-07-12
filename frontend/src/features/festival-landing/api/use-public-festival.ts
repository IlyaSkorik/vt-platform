import { type UseQueryResult, useQuery } from "@tanstack/react-query";
import { type ApiError, toApiError } from "@/shared/api";
import type { PublicFestivalDetailEnvelope } from "@/shared/api/generated/model-public-catalog";
import { getPublicFestival } from "@/shared/api/generated/public-catalog/public-catalog";
import type { FestivalDetail } from "../lib/types";
import { festivalLandingKeys } from "./keys";

/** Unwrap the `{ data, meta }` envelope into the festival detail view model. */
function unwrapFestival(body: unknown): FestivalDetail {
  if (body != null && typeof body === "object" && "data" in body) {
    const nested = (body as PublicFestivalDetailEnvelope).data;
    if (nested != null && typeof nested === "object") {
      return nested;
    }
  }
  throw new Error("Unexpected public festival response shape.");
}

async function fetchPublicFestival(
  festivalId: string,
  signal?: AbortSignal,
): Promise<FestivalDetail> {
  try {
    const response = await getPublicFestival(festivalId, signal ? { signal } : {});
    return unwrapFestival(response.data);
  } catch (error) {
    throw await toApiError(error);
  }
}

/**
 * Load one public competition's full landing view.
 *
 * A single cached read backs the whole page (hero facts, landing blocks and the
 * reused Competition Contacts). Cached for a minute — public data changes slowly
 * and every visitor sees the same projection. A 404 (the competition is missing
 * or not publicly visible) is terminal, so it is never retried; the page renders
 * a dedicated not-found state instead.
 */
export function usePublicFestival(
  festivalId: string | undefined,
): UseQueryResult<FestivalDetail, ApiError> {
  return useQuery<FestivalDetail, ApiError>({
    queryKey: festivalLandingKeys.detail(festivalId ?? ""),
    queryFn: ({ signal }) => fetchPublicFestival(festivalId as string, signal),
    enabled: Boolean(festivalId),
    staleTime: 60_000,
    retry: (failureCount, error) => error.status !== 404 && failureCount < 2,
  });
}
