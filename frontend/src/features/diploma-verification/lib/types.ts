import type { DiplomaVerification } from "@/shared/api/generated/model-diploma-verification";

/**
 * Domain types for the public diploma authenticity page.
 *
 * The Orval-generated wire model is used directly as the working view model — the
 * page is read-only, so there is no reason to remap. This alias gives the feature
 * an intention-revealing vocabulary and a single place to evolve the shape if the
 * projection and the UI ever diverge.
 */
export type VerifiedDiploma = DiplomaVerification;
