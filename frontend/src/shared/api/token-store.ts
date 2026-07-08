/**
 * In-memory access-token store (PLACEHOLDER).
 *
 * The web client keeps the short-lived JWT access token in memory only; the
 * rotating refresh token lives in an httpOnly cookie managed by the server and
 * is never readable by JS (ARCH-001 §11.1, API-001 §3). No persistence to
 * localStorage — that would expose tokens to XSS.
 *
 * This module is a seam: the real AuthProvider will own the token lifecycle
 * (login/refresh/logout). For bootstrap it holds no token and implements no
 * auth logic — it merely provides the injection point the API client reads.
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
