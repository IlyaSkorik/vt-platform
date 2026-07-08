import { QueryClient } from "@tanstack/react-query";
import { ApiError } from "./error";

/**
 * TanStack Query is the single source of truth for server state (ARCH-001
 * §8.2) — no server data is duplicated into a global client store.
 *
 * Defaults encode platform-wide policy:
 * - `staleTime` — a small window of freshness to deduplicate bursts of reads.
 * - `retry` — never retry client errors (4xx except 429); the transport already
 *   retries transient statuses (API-000 §19.2), so query-level retries only
 *   help genuine transient/unknown failures.
 */
export function createQueryClient(): QueryClient {
  return new QueryClient({
    defaultOptions: {
      queries: {
        staleTime: 30_000,
        gcTime: 5 * 60_000,
        refetchOnWindowFocus: false,
        retry: (failureCount, error) => {
          if (error instanceof ApiError) {
            if (error.status === 429) {
              return failureCount < 2;
            }
            if (error.status >= 400 && error.status < 500) {
              return false;
            }
          }
          return failureCount < 2;
        },
      },
      mutations: {
        // Writes are never auto-retried; idempotency is the caller's contract.
        retry: false,
      },
    },
  });
}
