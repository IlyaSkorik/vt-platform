/**
 * Public API of the `diploma-verification` feature.
 *
 * Data access (TanStack Query over the public verification endpoint) and
 * framework-free presentation logic (which facts a registry entry shows, how a
 * not-yet-awarded degree reads, how dates are set) for the page a printed
 * diploma's QR code opens. Widgets compose these; nothing reaches past this
 * barrel.
 */
export { diplomaVerificationKeys, useVerifyDiploma } from "./api";
export {
  DEGREE_PENDING_LABEL,
  type DiplomaFactKind,
  type DiplomaFactRow,
  diplomaFactRows,
  formatCheckedAt,
  formatCompetitionDate,
  type VerifiedDiploma,
} from "./lib";
