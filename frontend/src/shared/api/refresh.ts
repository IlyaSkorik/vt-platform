import { env } from "@/shared/config";
import { tokenStore } from "./token-store";

/**
 * Single-flight access-token refresh.
 *
 * Exchanges the httpOnly rotating refresh cookie for a fresh access token
 * (`POST /auth/token/refresh`, API-001 §4.5) and writes it to the in-memory
 * {@link tokenStore}. Resolves `true` when a new token was stored, `false`
 * when the cookie is absent/expired/revoked or the response is unusable.
 *
 * The in-flight promise is shared across all callers — the 401 refresh hook and
 * the AuthProvider's proactive bootstrap alike — so concurrent callers trigger
 * exactly one network request (no refresh stampede). This is the single source
 * of the refresh operation; nothing else should POST to the refresh endpoint.
 */
let refreshInFlight: Promise<boolean> | null = null;

export function refreshAccessToken(): Promise<boolean> {
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
