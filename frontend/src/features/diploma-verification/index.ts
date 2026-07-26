/**
 * Public API of the `diploma-verification` feature.
 *
 * Data access (TanStack Query over the public verification endpoint) and
 * framework-free presentation logic (which facts a diploma shows, and how a
 * not-yet-awarded degree reads) for the page a printed diploma's QR code opens.
 * Widgets compose these; nothing reaches past this barrel.
 */
export { diplomaVerificationKeys, useVerifyDiploma } from "./api";
export {
  DEGREE_PENDING_LABEL,
  type DiplomaFactRow,
  diplomaFactRows,
  type VerifiedDiploma,
} from "./lib";
