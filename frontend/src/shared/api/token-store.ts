/**
 * In-memory access-token store.
 *
 * The web client keeps the short-lived JWT access token in memory only; the
 * rotating refresh token lives in an httpOnly cookie managed by the server and
 * is never readable by JS (ARCH-001 §11.1, API-001 §3). No persistence of
 * tokens to localStorage — that would expose them to XSS.
 *
 * The one persisted bit is the **remember-me preference**: a non-secret flag
 * that tells the AuthProvider whether to attempt a silent refresh on cold app
 * start. Its presence is not proof of a session (the httpOnly refresh cookie
 * is authoritative) — it only gates whether we *try* to restore one.
 */
const REMEMBER_ME_KEY = "vt-remember-session";

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
  /** Whether the user opted to be remembered across browser sessions. */
  getRememberMe(): boolean {
    if (typeof window === "undefined") {
      return false;
    }
    return window.localStorage.getItem(REMEMBER_ME_KEY) === "true";
  },
  /** Persist (or clear) the remember-me preference. */
  setRememberMe(remember: boolean): void {
    if (typeof window === "undefined") {
      return;
    }
    if (remember) {
      window.localStorage.setItem(REMEMBER_ME_KEY, "true");
    } else {
      window.localStorage.removeItem(REMEMBER_ME_KEY);
    }
  },
};

export type TokenStore = typeof tokenStore;
