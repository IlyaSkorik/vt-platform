import type { ProblemDetails } from "./error";

/**
 * Short-lived cache of parsed Problem Details, keyed by `X-Request-ID`.
 *
 * Ky consumes a failed response's body when it builds the `HTTPError` message,
 * so by the time `toApiError` runs the body is gone and cannot be re-read. The
 * `captureProblemDetails` hook parses the body earlier (in `afterResponse`,
 * while it is still intact) and stashes it here; `toApiError` then reads it back
 * by the correlation id that travels on both the response and the thrown error.
 *
 * Entries are one-shot (removed on read) and the map is bounded, so a failed
 * read (no matching error) cannot leak memory unboundedly.
 */
const MAX_ENTRIES = 100;
const cache = new Map<string, ProblemDetails>();

export function storeProblem(requestId: string, problem: ProblemDetails): void {
  if (cache.size >= MAX_ENTRIES) {
    const oldest = cache.keys().next().value;
    if (oldest !== undefined) {
      cache.delete(oldest);
    }
  }
  cache.set(requestId, problem);
}

/** Read and remove the cached problem for a request id. */
export function takeProblem(requestId: string): ProblemDetails | undefined {
  const problem = cache.get(requestId);
  if (problem) {
    cache.delete(requestId);
  }
  return problem;
}
