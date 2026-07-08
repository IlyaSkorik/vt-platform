/**
 * In-memory access-token store.
 *
 * The web client keeps the short-lived JWT access token in memory only; the
 * rotating refresh token lives in an httpOnly cookie managed by the server and
 * is never readable by JS (ARCH-001 §11.1, API-001 §3). No persistence of
 * tokens to localStorage — that would expose them to XSS.
 *
 * There is no client-side session flag: the httpOnly refresh cookie is the
 * single source of truth for whether a session exists. On cold start the client
 * always attempts a silent refresh and lets the server decide.
 */
let accessToken: string | null = null;

export const tokenStore = {
  get(): string | null {
    return accessToken;
  },
  set(token: string | null): void {
    accessToken = token;
  },
  clear(): void {
    accessToken = null;
  },
};

export type TokenStore = typeof tokenStore;
