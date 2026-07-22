import { type UseQueryResult, useQuery } from "@tanstack/react-query";
import { type ApiError, toApiError } from "@/shared/api";
import type {
  Registration,
  RegistrationEnvelope,
} from "@/shared/api/generated/model-public-catalog";
import { getRegistration } from "@/shared/api/generated/public-catalog/public-catalog";
import { festivalLandingKeys } from "./keys";

/** Unwrap the `{ data, meta }` envelope into the registration projection. */
function unwrapRegistration(body: unknown): Registration {
  if (body != null && typeof body === "object" && "data" in body) {
    const nested = (body as RegistrationEnvelope).data;
    if (nested != null && typeof nested === "object") {
      return nested;
    }
  }
  throw new Error("Unexpected public registration response shape.");
}

async function fetchPublicRegistration(
  festivalId: string,
  signal?: AbortSignal,
): Promise<Registration> {
  try {
    const response = await getRegistration(festivalId, signal ? { signal } : {});
    return unwrapRegistration(response.data);
  } catch (error) {
    throw await toApiError(error);
  }
}

/**
 * Load the public registration projection for a competition.
 *
 * Backs the landing's registration block: the per-nomination schedule (window +
 * open/stopped state) the visitor needs to see at a glance. Cached for a minute
 * like the detail read; a 404 (missing/unpublished competition) is terminal.
 */
export function usePublicRegistration(
  festivalId: string | undefined,
): UseQueryResult<Registration, ApiError> {
  return useQuery<Registration, ApiError>({
    queryKey: festivalLandingKeys.registration(festivalId ?? ""),
    queryFn: ({ signal }) => fetchPublicRegistration(festivalId as string, signal),
    enabled: Boolean(festivalId),
    staleTime: 60_000,
    retry: (failureCount, error) => error.status !== 404 && failureCount < 2,
  });
}
