/**
 * Public API of the consent catalogue.
 *
 * Every checkbox that asks for a consent, and every call that records one, reads from
 * here: the wording shown and the `(code, version)` stored are the same entry, so the
 * journal always identifies the text the person actually saw (LEGAL-001 §13.3).
 */

export {
  ACCOUNT_CONSENTS,
  APPLICATION_CONSENTS,
  applicationConsent,
  type ConsentDefinition,
  PARTICIPANT_CONSENT,
  TEACHER_CONSENT,
} from "./definitions";
export { ConsentCheckbox } from "./ui/consent-checkbox";
