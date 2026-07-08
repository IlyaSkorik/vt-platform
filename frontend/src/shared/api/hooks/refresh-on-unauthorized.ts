import type { AfterResponseHook } from "ky";
import { env } from "@/shared/config";
import { HEADER } from "../config";
import { emitSessionEvent } from "../session-events";
import { tokenStore } from "../token-store";

/**
 * Automatic-refresh hook (response).
 *
 * When a protected request comes back `401` because the short-lived access
 * token expired, transparently refresh and replay the original request exactly
 * once (API-001 §4.5):
 *
 *   1. A single in-flight refresh is shared across concurrent 401s (a
 *      de-duplicated promise) so a burst of expired requests triggers exactly
 *      one `POST /auth/token/refresh` — no refresh stampede.
 *   2. The web client's rotating refresh token travels as an httpOnly cookie,
 *      so no token material is read or written here; the server rotates it and
 *      returns a fresh access token, which we place in the in-memory store.
 *   3. On success the original request is replayed with the new bearer token
 *      (marked so it can never trigger a second refresh → no loop).
 *   4. On failure (expired/absent refresh cookie, or reuse detection → family
 *      revoked, `403`), the session is cleared and `session-expired` is emitted
 *      for the AuthProvider to handle; the `401` propagates to the caller.
 *
 * Auth endpoints are exempt: a `401` from login/refresh is a real credential
 * failure, not an expired access token, and must surface unchanged.
 */

const RETRY_MARKER = "X-VT-Refresh-Retry";
const UNAUTHORIZED = 401;

/** Paths where a 401 means "bad credentials", not "expired token". */
const AUTH_PATHS = [
  "/auth/sessions",
  "/auth/token/refresh",
  "/auth/registration",
  "/auth/password-reset/",
  "/auth/email-verification/",
];

function isAuthPath(url: string): boolean {
  return AUTH_PATHS.some((path) => url.includes(path));
}

let refreshInFlight: Promise<boolean> | null = null;

/** Perform the token refresh exactly once, sharing the promise across callers. */
function refreshOnce(): Promise<boolean> {
  refreshInFlight ??= (async () => {
    try {
      const response = await fetch(`${env.apiBaseUrl}/auth/token/refresh`, {
        method: "POST",
        credentials: "include",
        headers: { Accept: "application/json" },
      });
      if (!response.ok) {
        return false;
      }
      const body = (await response.json()) as { data?: { accessToken?: string } };
      const accessToken = body.data?.accessToken;
      if (!accessToken) {
        return false;
      }
      tokenStore.set(accessToken);
      return true;
    } catch {
      return false;
    } finally {
      refreshInFlight = null;
    }
  })();
  return refreshInFlight;
}

export const refreshOnUnauthorized: AfterResponseHook = async ({ request, response }) => {
  if (response.status !== UNAUTHORIZED) {
    return response;
  }
  // Never refresh for the auth endpoints themselves, and never twice.
  if (isAuthPath(request.url) || request.headers.has(RETRY_MARKER)) {
    return response;
  }

  const refreshed = await refreshOnce();
  if (!refreshed) {
    tokenStore.clear();
    emitSessionEvent("session-expired");
    return response;
  }

  // Replay the original request with the new token, marked so a subsequent
  // 401 cannot start another refresh. A bare `fetch` bypasses the Ky hook
  // pipeline, so this replay never re-enters this hook.
  const retried = new Request(request);
  retried.headers.set(HEADER.authorization, `Bearer ${tokenStore.get() ?? ""}`);
  retried.headers.set(RETRY_MARKER, "1");
  return fetch(retried);
};
