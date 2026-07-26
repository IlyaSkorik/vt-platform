import type { DocumentType, MyDocument } from "./types";

/** How one kind of document presents itself in the cabinet. */
export interface DocumentKindConfig {
  /** Row heading, e.g. "Диплом". */
  label: string;
  /** Emoji marker — the cabinet's own visual shorthand, per the design. */
  icon: string;
  /** Whether this kind carries a registry number worth showing. */
  showsNumber: boolean;
  /** Whether this kind can bear a jury result. */
  showsDegree: boolean;
}

/**
 * The per-kind display table — the frontend half of the extension point.
 *
 * Adding a document kind means adding one entry here and nothing else: the page
 * iterates whatever the API returns and looks each kind up. A kind the client does
 * not yet know about still renders (see {@link documentKind}) rather than
 * disappearing, so a backend deploy ahead of a frontend deploy degrades gracefully.
 */
export const DOCUMENT_KINDS: Record<string, DocumentKindConfig> = {
  DIPLOMA: {
    label: "Диплом",
    icon: "🏆",
    showsNumber: true,
    showsDegree: true,
  },
  THANK_YOU: {
    label: "Благодарность",
    icon: "🙏",
    showsNumber: false,
    showsDegree: false,
  },
};

/** Fallback for a kind this client build does not know yet. */
const UNKNOWN_KIND: DocumentKindConfig = {
  label: "Документ",
  icon: "📄",
  showsNumber: false,
  showsDegree: false,
};

/** How to present this document's kind, never throwing on an unknown one. */
export function documentKind(type: DocumentType | string): DocumentKindConfig {
  return DOCUMENT_KINDS[type] ?? UNKNOWN_KIND;
}

/**
 * The document's subtitle: the competition, then the nomination.
 *
 * Absent parts are dropped rather than shown blank — the same rule the printed
 * document follows.
 */
export function documentSubtitle(document: MyDocument): string | null {
  const parts = [document.competitionTitle, document.nomination]
    .map((part) => part?.trim())
    .filter((part): part is string => Boolean(part));
  return parts.length > 0 ? parts.join(" · ") : null;
}
