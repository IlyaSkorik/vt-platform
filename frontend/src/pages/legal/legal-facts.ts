/**
 * The facts the published legal documents state about the operator, in one place.
 *
 * Both policies name the same operator, the same contact channel and the same
 * document versions, and a policy that contradicts itself between two pages is
 * worse than either page alone — so the values live here and the pages read them.
 *
 * The Markdown sources are `docs/legal/LEGAL-001-privacy-policy.md` and
 * `docs/legal/LEGAL-002-cookies-policy.md`. When a value here changes, the
 * corresponding clause there changes with it.
 */

import { SUPPORT_EMAIL } from "@/shared/config";

/**
 * Whom the policies name as оператор персональных данных (art. 1 of Law No. 99-З).
 *
 * `postalAddress` and `phone` are deliberately typed as nullable and ship empty:
 * a published policy must not carry a placeholder where a legal address belongs.
 * Until the operator supplies them, the pages omit those rows and omit the
 * postal channel from the "how to file a request" list — an email-only channel
 * that works beats a postal address that does not exist.
 *
 * `postalAddress` is the address a written request under art. 15 of Law No. 99-З is
 * sent to, so it is part of the published policy and changing it changes what the
 * document promises. `phone` remains unset: the operator offers no phone channel for
 * personal-data requests, and the pages therefore show none.
 */
export const LEGAL_OPERATOR = {
  name: "Скорик Илья Андреевич",
  status: "Плательщик налога на профессиональный доход",
  unp: "AE9395951",
  postalAddress: "220047, г. Минск, ул. Нестерова, 70-127" as string | null,
  phone: null as string | null,
  email: SUPPORT_EMAIL,
  siteHost: "vzlettalantov.by",
  noReplyEmail: "no-reply@vzlettalantov.by",
  bulkEmail: "news@vzlettalantov.by",
} as const;

/**
 * One published revision of a legal document.
 *
 * `version` is the identifier the platform stores in `consent_version` when a
 * user accepts the document, so a stored consent can be traced back to the exact
 * text that was in force. It is therefore append-only: a new wording gets a new
 * version, never an edit in place.
 *
 * `effectiveDate` is `null` until the operator approves the revision. While it is
 * null the page says so plainly rather than implying a legal force the document
 * does not yet have.
 */
export type LegalRevision = {
  readonly version: string;
  readonly consentVersion: string;
  readonly effectiveDate: string | null;
};

/** Approved by the operator and in force since 6 August 2026. */
export const PRIVACY_POLICY_REVISION: LegalRevision = {
  version: "1.0",
  consentVersion: "privacy-policy-1.0",
  effectiveDate: "2026-08-06",
};

/**
 * The user agreement — approved by the operator and in force since 11 August 2026.
 *
 * This is the contract art. 6 of the Law refers to: the account exists because the
 * person entered it, which is why the registration form asks them to accept it rather
 * than to consent to being processed.
 */
export const TERMS_OF_SERVICE_REVISION: LegalRevision = {
  version: "1.0",
  consentVersion: "terms-of-service-1.0",
  effectiveDate: "2026-08-11",
};

/** Approved by the operator and in force since 6 August 2026. */
export const COOKIES_POLICY_REVISION: LegalRevision = {
  version: "1.0",
  consentVersion: "cookies-policy-1.0",
  effectiveDate: "2026-08-06",
};
