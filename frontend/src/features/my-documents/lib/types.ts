import type {
  DocumentTypeEnum,
  ParticipantDocument,
} from "@/shared/api/generated/model-my-documents";

/**
 * Domain types for the participant's documents ("Мои документы").
 *
 * The Orval-generated wire models are used directly as the working view models —
 * the page is read-only, so there is no reason to remap. These aliases give the
 * feature an intention-revealing vocabulary and a single place to evolve the shape
 * if the projection and the UI ever diverge.
 */
export type MyDocument = ParticipantDocument;

/** A kind of document the platform issues. */
export type DocumentType = DocumentTypeEnum;
