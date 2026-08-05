/**
 * Public API of the legal pages segment.
 *
 * The router lazy-loads both documents from this module by name
 * (`lazyPage(() => import("@/pages/legal"), "PrivacyPolicyPage")`), so the two
 * pages share one chunk — which is what we want: they cross-link to each other
 * and are read together.
 *
 * The published text is mirrored from `docs/legal/`; see that directory's README
 * for the rule about which copy is edited first.
 */

export { CookiesPolicyPage } from "./cookies-policy";
export { PrivacyPolicyPage } from "./privacy-policy";
