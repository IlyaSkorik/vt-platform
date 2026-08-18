import { Award, FileText, HeartHandshake, type LucideIcon, UserRound } from "lucide-react";

import type { DocumentType, MyDocument } from "./types";

/** How one kind of document presents itself in the cabinet. */
export interface DocumentKindConfig {
  /** Row heading, e.g. "Диплом". */
  label: string;
  /**
   * The row's marker.
   *
   * A drawn icon, not an emoji: emoji are rendered by the operating system, so
   * the same two documents looked like a gold trophy and folded hands on one
   * machine and like flat grey glyphs on another, at whatever weight and colour
   * the font felt like. These follow the interface — one stroke weight, the
   * theme's colours, and the same shape everywhere.
   */
  icon: LucideIcon;
  /** The tint the marker is drawn in, distinguishing the kinds at a glance. */
  tone: "diploma" | "gratitude" | "neutral";
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
    // A rosette: what is actually printed on the document, and what the degree
    // badge beside it is a result of.
    icon: Award,
    tone: "diploma",
    showsNumber: true,
    showsDegree: true,
  },
  INDIVIDUAL_DIPLOMA: {
    label: "Индивидуальный диплом",
    // A single figure, not the rosette: the same award as the collective's diploma,
    // but this one is addressed to one person inside it.
    icon: UserRound,
    tone: "diploma",
    showsNumber: true,
    showsDegree: true,
  },
  THANK_YOU: {
    label: "Благодарность",
    // Two hands, not one trophy: a letter of thanks ranks nobody. It says the
    // teacher's work was seen, which is a different thing from winning.
    icon: HeartHandshake,
    tone: "gratitude",
    showsNumber: false,
    showsDegree: false,
  },
};

/** Fallback for a kind this client build does not know yet. */
const UNKNOWN_KIND: DocumentKindConfig = {
  label: "Документ",
  icon: FileText,
  tone: "neutral",
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

/**
 * Who the document is addressed to, when that is what distinguishes it.
 *
 * A thank-you letter is issued per teacher and an individual diploma per member of a
 * collective, so one entry can produce several rows that are otherwise identical — the
 * recipient is the only thing telling them apart, and the download would be a coin toss
 * without it. Empty for a document that belongs to the performance itself, like the
 * collective's own diploma.
 */
export function documentRecipient(document: MyDocument): string | null {
  return document.recipient?.trim() || null;
}
