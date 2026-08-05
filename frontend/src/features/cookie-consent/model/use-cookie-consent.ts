import { useSyncExternalStore } from "react";
import { type CookieConsent, getCookieConsent, subscribeToCookieConsent } from "./consent-store";

/** The visitor's decision, or `null` while they have not made one. */
export function useCookieConsent(): CookieConsent | null {
  // Server snapshot is `null`: rendered without a browser there is no decision to
  // report, and "no decision" is the state that withholds analytics.
  return useSyncExternalStore(subscribeToCookieConsent, getCookieConsent, () => null);
}

/**
 * Whether analytics counters may run.
 *
 * This is the flag a counter hangs on. Gate the *loading* of the script on it, not
 * just the sending of events — LEGAL-002 §2.2 promises nothing analytic loads
 * before consent, and a script fetched from `mc.yandex.ru` has already told that
 * host who the visitor is.
 */
export function useAnalyticsConsent(): boolean {
  return useCookieConsent()?.analytics === true;
}
