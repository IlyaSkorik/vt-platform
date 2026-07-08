import type { AfterResponseHook } from "ky";
import { HEADER } from "../config";
import { refreshAccessToken } from "../refresh";
import { emitSessionEvent } from "../session-events";
import { tokenStore } from "../token-store";

/**
 * Automatic-refresh hook (response).
 *
 * When a protected request comes back `401` because the short-lived access
 * token expired, transparently refresh and replay the original request exactly
 * once (API-001 §4.5):
 *
 *   1. Refresh is delegated to the shared single-flight {@link refreshAccessToken},
 *      so a burst of concurrent 401s — and the AuthProvider's bootstrap — all
 *      share one in-flight `POST /auth/token/refresh` (no refresh stampede).
 *   2. The web client's rotating refresh token travels as an httpOnly cookie,
 *      so no token material is read or written here; the server rotates it and
 *      returns a fresh access token, which the shared refresh places in memory.
 *   3. On success the original request is replayed with the new bearer token
 *      via a bare `fetch` that bypasses this Ky hook pipeline, so the replay can
 *      never re-enter this hook → no refresh loop. Nothing is added to the
 *      replayed request beyond the refreshed `Authorization` header (a custom
 *      marker header would trip a CORS preflight the server does not allow).
 *   4. On failure (expired/absent refresh cookie, or reuse detection → family
 *      revoked, `403`), the session is cleared and `session-expired` is emitted
 *      for the AuthProvider to handle; the `401` propagates to the caller.
 *
 * Auth endpoints are exempt: a `401` from login/refresh is a real credential
 * failure, not an expired access token, and must surface unchanged.
 */

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

export const refreshOnUnauthorized: AfterResponseHook = async ({ request, response }) => {
  if (response.status !== UNAUTHORIZED) {
    return response;
  }
  // Never refresh for the auth endpoints themselves.
  if (isAuthPath(request.url)) {
    return response;
  }

  const refreshed = await refreshAccessToken();
  if (!refreshed) {
    tokenStore.clear();
    emitSessionEvent("session-expired");
    return response;
  }

  // Replay the original request with the new token. A bare `fetch` bypasses the
  // Ky hook pipeline, so this replay never re-enters this hook — no refresh loop
  // is possible and no retry marker header is needed. (Adding a non-safelisted
  // header here would force a CORS preflight the server does not allow.)
  const retried = new Request(request);
  retried.headers.set(HEADER.authorization, `Bearer ${tokenStore.get() ?? ""}`);
  return fetch(retried);
};
