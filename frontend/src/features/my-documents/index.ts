/**
 * Public API of the `my-documents` feature.
 *
 * Data access (TanStack Query over the participant's document list) and
 * framework-free presentation logic (how each document kind labels itself) for the
 * cabinet's "Мои документы" page. Widgets compose these; nothing reaches past this
 * barrel.
 */
export { myDocumentsKeys, useMyDocuments } from "./api";
export {
  DOCUMENT_KINDS,
  type DocumentKindConfig,
  type DocumentType,
  documentKind,
  documentRecipient,
  documentSubtitle,
  type MyDocument,
} from "./lib";
