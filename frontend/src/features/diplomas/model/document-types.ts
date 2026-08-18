import type { DocumentTypeEnum } from "@/shared/api/generated/model-diplomas";
import type { TemplateFieldTypeId } from "./constructor";

/** A kind of document a template produces. */
export type DocumentType = DocumentTypeEnum;

/**
 * Element kinds a thank-you letter may carry — mirrors the backend policy, which
 * rejects a layout carrying anything else.
 *
 * A courtesy letter names who is being thanked, who taught them, and which event it
 * was for. It ranks nothing (no degree), is not registered (no number, issue date
 * or QR) and does not itemise the entry (no age, organization, nomination or work).
 * Free text carries whatever wording the organizer wants.
 */
const THANK_YOU_FIELD_TYPES: ReadonlySet<TemplateFieldTypeId> = new Set([
  "participant_name",
  "teacher",
  "competition_name",
  "competition_date",
  "competition_city",
  "free_text",
]);

/**
 * The one element only an individual diploma may place — mirrors the backend policy,
 * which rejects it on any other layout.
 *
 * The collective's own sheet has no single member to name, so a field bound to one
 * would print nothing there and mislead whoever placed it. Everything else is shared:
 * an individual diploma is the collective's diploma with this one line added.
 */
const MEMBER_ONLY_FIELD_TYPES: ReadonlySet<TemplateFieldTypeId> = new Set(["member_name"]);

/** How one kind presents itself in the organizer workspace. */
export interface DocumentTypeConfig {
  /** Singular noun for the document, e.g. "Диплом". */
  label: string;
  /** Label for the nomination slot this kind fills, e.g. "Шаблон диплома". */
  slotLabel: string;
  /** Badge tone on a template card. */
  tone: "primary" | "info";
  /** One line explaining what the kind is for, shown when choosing. */
  hint: string;
  /**
   * Whether a teacher field prints the role alongside the name ("Педагог: ФИО").
   *
   * Mirrors the backend policy of the same name, which is what generation actually
   * applies — so the editor's sample values show what will print rather than a
   * label the letter drops.
   */
  teacherRoles: boolean;
}

/**
 * The per-kind display table — the workspace half of the extension point.
 *
 * Adding a document kind means adding one entry here; the template library, the
 * type selector and the assignment slots all read from it, so none of them needs
 * to know the kinds by name.
 */
export const DOCUMENT_TYPES: Record<string, DocumentTypeConfig> = {
  DIPLOMA: {
    label: "Диплом",
    slotLabel: "Шаблон диплома",
    tone: "primary",
    hint: "Награда участника: со степенью, номером и QR-кодом для проверки подлинности.",
    // A diploma credits a teacher in a stated capacity.
    teacherRoles: true,
  },
  INDIVIDUAL_DIPLOMA: {
    label: "Индивидуальный диплом",
    slotLabel: "Шаблон индивидуального диплома",
    tone: "primary",
    hint: "Диплом участнику коллектива: всё то же, плюс поле «ФИО участника». Выпускается каждому названному участнику при публикации протокола.",
    // The same award as the collective's diploma, so a teacher is credited the same way.
    teacherRoles: true,
  },
  THANK_YOU: {
    label: "Благодарность",
    slotLabel: "Шаблон благодарности",
    tone: "info",
    hint: "Знак признательности: без степени, без номера и без проверки подлинности.",
    // A letter thanks a person by name; the letter itself already says what it is.
    teacherRoles: false,
  },
};

/** Kinds in the order the workspace offers them. */
export const DOCUMENT_TYPE_ORDER: DocumentType[] = ["DIPLOMA", "INDIVIDUAL_DIPLOMA", "THANK_YOU"];

/** Fallback for a kind this client build does not know yet. */
const UNKNOWN: DocumentTypeConfig = {
  label: "Документ",
  slotLabel: "Шаблон документа",
  tone: "info",
  hint: "",
  // Unrestricted, like `allowsFieldType` — a client running behind the backend
  // shows the fuller form rather than silently dropping information.
  teacherRoles: true,
};

/** How to present this kind, never throwing on an unknown one. */
export function documentTypeConfig(type: DocumentType | string): DocumentTypeConfig {
  return DOCUMENT_TYPES[type] ?? UNKNOWN;
}

/** Options for the type selector, in workspace order. */
export const DOCUMENT_TYPE_OPTIONS = DOCUMENT_TYPE_ORDER.map((value) => ({
  value,
  label: documentTypeConfig(value).label,
}));

/**
 * Whether a template of this kind may place that element.
 *
 * An individual diploma may carry the whole catalogue; a diploma all of it but the
 * member's name; a thank-you letter only its own short list. An unknown kind is treated
 * as unrestricted rather than empty, so a client running behind the backend still shows
 * a usable palette.
 */
export function allowsFieldType(
  documentType: DocumentType | string,
  fieldType: TemplateFieldTypeId,
): boolean {
  if (documentType === "THANK_YOU") {
    return THANK_YOU_FIELD_TYPES.has(fieldType);
  }
  if (documentType === "DIPLOMA") {
    return !MEMBER_ONLY_FIELD_TYPES.has(fieldType);
  }
  return true;
}
