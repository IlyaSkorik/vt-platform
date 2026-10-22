/**
 * Where to send somebody once they have an account and a session.
 *
 * `?next=` carries this between screens, but registration breaks the chain: the account
 * is created, a verification letter goes out, and the person comes back through a link
 * in a *different* message — by which point the query parameter is three navigations
 * gone. Somebody invited onto a jury would land in the participant cabinet with no clue
 * the invitation was still waiting, which is exactly what used to happen.
 *
 * So the destination is also parked in `localStorage` for the length of that detour.
 * Deliberately not a cookie and not session storage: the verification link is routinely
 * opened in a new tab, and often minutes later.
 *
 * Only in-app absolute paths are ever stored or returned. A value that is not one is
 * dropped, because this feeds a redirect and an open redirect is how a sign-in page
 * becomes a phishing page.
 */

const STORAGE_KEY = "vt.post-auth-redirect";

/** `/jury/invite/abc` yes; `https://evil.test`, `//evil.test` and `../x` no. */
export function isSafeRedirect(value: string | null | undefined): value is string {
  return typeof value === "string" && value.startsWith("/") && !value.startsWith("//");
}

export function rememberPostAuthRedirect(path: string): void {
  if (!isSafeRedirect(path) || typeof window === "undefined") {
    return;
  }
  try {
    window.localStorage.setItem(STORAGE_KEY, path);
  } catch {
    // Private mode, a full quota, a browser with storage disabled. The `?next=`
    // parameter still works for everything that does not detour through e-mail.
  }
}

export function readPostAuthRedirect(): string | null {
  if (typeof window === "undefined") {
    return null;
  }
  try {
    const stored = window.localStorage.getItem(STORAGE_KEY);
    return isSafeRedirect(stored) ? stored : null;
  } catch {
    return null;
  }
}

export function clearPostAuthRedirect(): void {
  if (typeof window === "undefined") {
    return;
  }
  try {
    window.localStorage.removeItem(STORAGE_KEY);
  } catch {
    // Nothing to do: a stale entry only ever sends somebody to a page they have
    // already been to, and the next successful sign-in overwrites it.
  }
}

/**
 * `/login?next=…` — or the bare path when there is nowhere particular to go.
 *
 * Pure: building a link must not write anything. Parking the destination is a separate,
 * deliberate call, made where the chain actually breaks — see `rememberPostAuthRedirect`
 * and the registration screen.
 */
export function authPathWithNext(base: string, next: string | null | undefined): string {
  return isSafeRedirect(next) ? `${base}?next=${encodeURIComponent(next)}` : base;
}
