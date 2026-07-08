import type { BeforeRequestHook } from "ky";
import { HEADER } from "../config";
import { tokenStore } from "../token-store";

/**
 * Authorization hook (request).
 *
 * Attaches the bearer access token (API-000 §17.1) when one is present. The
 * token is read from the in-memory {@link tokenStore}, which the AuthProvider
 * owns. Requests without a token proceed unauthenticated — public endpoints
 * are a documented allow-list (API-000 §17.4).
 */
export const attachAuth: BeforeRequestHook = ({ request }) => {
  const token = tokenStore.get();
  if (token && !request.headers.has(HEADER.authorization)) {
    request.headers.set(HEADER.authorization, `Bearer ${token}`);
  }
};
