/**
 * Public API of the cookie-consent feature.
 *
 * Owns one fact: whether the visitor allowed analytics cookies. Anything that would
 * send data to Yandex Metrica or Google Analytics must ask first —
 * `useAnalyticsConsent()` in a component, `analyticsAllowed()` outside React — and
 * must gate the *loading* of the counter script, not merely its events.
 *
 * The published text these guarantees come from is
 * `docs/legal/LEGAL-002-cookies-policy.md` §2.
 */

export { analyticsAllowed, type CookieConsent, resetCookieConsent } from "./model/consent-store";
export { useAnalyticsConsent, useCookieConsent } from "./model/use-cookie-consent";
export { CookieBanner } from "./ui/cookie-banner";
export { CookieSettingsButton } from "./ui/cookie-settings-button";
