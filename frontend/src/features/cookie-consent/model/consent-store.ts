/**
 * The visitor's cookie decision — one small store outside React.
 *
 * It lives outside React because the thing that needs to read it most is not a
 * component: an analytics loader asks "may I run?" once, early, and must get the
 * same answer the banner is showing. A module-level store with
 * `useSyncExternalStore` on top gives both callers one source of truth.
 *
 * What is stored is only the decision, never an identifier: `{ analytics, decidedAt }`
 * under one localStorage key. That is deliberate — a consent record must not itself
 * become a tracking cookie.
 *
 * Documented in `docs/legal/LEGAL-002-cookies-policy.md` §5 (the key and its
 * lifetime) and §2 (that nothing analytic loads before a decision).
 */

import { COOKIE_CONSENT_STORAGE_KEY } from "@/shared/constants";

/** Current shape version. A bump re-asks rather than guessing at old data. */
const CONSENT_VERSION = 1;

/**
 * How long a decision stands before we ask again.
 *
 * A year is the ceiling common practice settles on, and it matches what
 * LEGAL-002 §5 tells visitors. Re-asking is not a nag: consent that was given
 * once and never revisited stops being informed.
 */
const CONSENT_TTL_DAYS = 365;

export type CookieConsent = {
  /** Whether analytics counters (Yandex Metrica, Google Analytics) may load. */
  readonly analytics: boolean;
  /** When the visitor decided, ISO-8601. */
  readonly decidedAt: string;
};

type StoredConsent = CookieConsent & { readonly version: number };

/** `null` means "not decided yet" — which is what makes the banner appear. */
let current: CookieConsent | null = null;
let hydrated = false;
const listeners = new Set<() => void>();

function isExpired(decidedAt: string): boolean {
  const decided = new Date(decidedAt).getTime();
  if (Number.isNaN(decided)) {
    return true;
  }
  return Date.now() - decided > CONSENT_TTL_DAYS * 24 * 60 * 60 * 1000;
}

function read(): CookieConsent | null {
  if (typeof window === "undefined") {
    return null;
  }
  try {
    const raw = window.localStorage.getItem(COOKIE_CONSENT_STORAGE_KEY);
    if (raw == null) {
      return null;
    }
    const parsed = JSON.parse(raw) as Partial<StoredConsent>;
    if (
      parsed.version !== CONSENT_VERSION ||
      typeof parsed.analytics !== "boolean" ||
      typeof parsed.decidedAt !== "string" ||
      isExpired(parsed.decidedAt)
    ) {
      return null;
    }
    return { analytics: parsed.analytics, decidedAt: parsed.decidedAt };
  } catch {
    // Unreadable storage (private mode, quota, hand-edited value) is the same
    // situation as no decision at all: ask, and default to no analytics.
    return null;
  }
}

function hydrate(): void {
  if (!hydrated) {
    current = read();
    hydrated = true;
  }
}

function emit(): void {
  for (const listener of listeners) {
    listener();
  }
}

if (typeof window !== "undefined") {
  // Consent is about the person, not the tab. Withdraw it in one tab and every other
  // open tab must stop analytics too — otherwise a visitor who just refused is still
  // being counted by the tab they left open. `key === null` is a `clear()`.
  window.addEventListener("storage", (event: StorageEvent) => {
    if (event.key === null || event.key === COOKIE_CONSENT_STORAGE_KEY) {
      current = read();
      hydrated = true;
      emit();
    }
  });
}

/** Subscribe to decision changes (the `useSyncExternalStore` contract). */
export function subscribeToCookieConsent(listener: () => void): () => void {
  listeners.add(listener);
  return () => {
    listeners.delete(listener);
  };
}

/** The current decision, or `null` while the visitor has not decided. */
export function getCookieConsent(): CookieConsent | null {
  hydrate();
  return current;
}

/** Record a decision and persist it. */
export function setCookieConsent(analytics: boolean): void {
  const decision: CookieConsent = { analytics, decidedAt: new Date().toISOString() };
  current = decision;
  hydrated = true;
  try {
    window.localStorage.setItem(
      COOKIE_CONSENT_STORAGE_KEY,
      JSON.stringify({ ...decision, version: CONSENT_VERSION } satisfies StoredConsent),
    );
  } catch {
    // Storage refused (private mode). The decision still holds for this page,
    // and the banner will simply ask again next visit — the safe failure.
  }
  emit();
}

/**
 * Forget the decision so the banner asks again.
 *
 * This is what "Настройки cookie" does: LEGAL-002 §2.4 promises the choice can be
 * changed at any time, and re-asking is the honest way to offer both directions.
 * Analytics is off again the moment this runs.
 */
export function resetCookieConsent(): void {
  current = null;
  hydrated = true;
  try {
    window.localStorage.removeItem(COOKIE_CONSENT_STORAGE_KEY);
  } catch {
    // Nothing to undo if storage is unavailable.
  }
  emit();
}

/**
 * Whether analytics may load right now.
 *
 * Non-React callers (an analytics bootstrap) use this; components use
 * `useAnalyticsConsent()`. Absent a decision the answer is `false` — consent is
 * something the visitor gives, never something absence implies.
 */
export function analyticsAllowed(): boolean {
  return getCookieConsent()?.analytics === true;
}
