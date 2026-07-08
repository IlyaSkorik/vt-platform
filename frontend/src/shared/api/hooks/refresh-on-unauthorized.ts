import type { AfterResponseHook } from "ky";

/**
 * Automatic-refresh hook (response) — PLACEHOLDER.
 *
 * When an access token expires the API returns 401. The production behaviour
 * (implemented once the Auth feature lands) will be:
 *
 *   1. On the first 401, call `POST /auth/token/refresh` exactly once. The web
 *      client's rotating refresh token travels as an httpOnly cookie
 *      (API-001 §4.5), so no token material is handled here.
 *   2. On success, update the in-memory access token and transparently retry
 *      the original request.
 *   3. On failure (or refresh-reuse detection → family revoked), clear the
 *      session and surface the 401 to the caller.
 *
 * Concurrent 401s must share a single in-flight refresh (a de-duplicated
 * promise) to avoid a refresh stampede.
 *
 * During bootstrap this hook is a no-op: it performs no refresh and no retry,
 * letting the 401 propagate to be mapped into an `ApiError`.
 */
export const refreshOnUnauthorized: AfterResponseHook = ({ response }) => {
  // Intentionally no-op. See the module docblock for the target behaviour.
  return response;
};
