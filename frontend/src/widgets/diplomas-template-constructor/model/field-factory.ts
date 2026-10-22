import {
  allowsFieldType,
  DEFAULT_FIELD_STYLE,
  DEFAULT_FREE_TEXT,
  type DocumentType,
  defaultBindingForType,
  defaultConfigForType,
  requiresQrBlock,
  type TemplateField,
  type TemplateFieldTypeId,
} from "@/features/diplomas";
import { createUuidV7 } from "@/shared/lib";

/** Default normalised size of a freshly-added field. */
const DEFAULT_WIDTH = 0.5;
const DEFAULT_HEIGHT = 0.07;

/** A field's normalised box: where it lands and how big it starts. */
interface FieldBox {
  x: number;
  y: number;
  width: number;
  height: number;
}

/**
 * Where a kind of field lands instead of the middle of the page.
 *
 * Only the QR block so far: it is the diploma's footer mark, and centring it drops
 * a dashed square over the participant's name — never where anyone wants it. The
 * box is wide enough for the square plus its three-line caption.
 */
const BOX_BY_TYPE: Partial<Record<TemplateFieldTypeId, FieldBox>> = {
  qr_block: { x: 0.66, y: 0.83, width: 0.3, height: 0.11 },
};

function boxForType(type: TemplateFieldTypeId): FieldBox {
  return (
    BOX_BY_TYPE[type] ?? {
      x: (1 - DEFAULT_WIDTH) / 2,
      y: (1 - DEFAULT_HEIGHT) / 2,
      width: DEFAULT_WIDTH,
      height: DEFAULT_HEIGHT,
    }
  );
}

/**
 * Minimum normalised size a field may be resized to — the equivalent of roughly
 * 40×20 px on a typical page, but resolution-independent.
 */
export const MIN_WIDTH = 0.05;
export const MIN_HEIGHT = 0.025;

/** Normalised offset a duplicate is nudged by so it doesn't hide the original. */
export const DUPLICATE_OFFSET = 0.03;

/**
 * Create a new field centred on the given page. A field is either data-bound
 * (binding set, value null) or free (value set, binding null) — never both.
 */
export function createField(type: TemplateFieldTypeId, page: number): TemplateField {
  const binding = defaultBindingForType(type);
  const bound = binding !== "";
  return {
    id: createUuidV7(),
    page,
    type,
    binding: bound ? binding : null,
    value: bound ? null : DEFAULT_FREE_TEXT,
    ...boxForType(type),
    style: { ...DEFAULT_FIELD_STYLE },
    config: defaultConfigForType(type),
  };
}

/**
 * The element kinds a template of this document kind must carry.
 *
 * A diploma is a numbered, verifiable record: the QR block is where its number and
 * verification link are printed, so a diploma without one is a sheet nobody can
 * check. A courtesy letter is neither numbered nor verifiable and requires nothing.
 */
export function requiredFieldTypes(
  documentType: DocumentType | string,
): readonly TemplateFieldTypeId[] {
  return requiresQrBlock(documentType) ? ["qr_block"] : [];
}

/**
 * The saved layout brought in line with what its kind of document may print: every
 * element the kind requires added at its default spot, every element the kind may
 * not carry removed.
 *
 * Runs once as the editor mounts, so a template saved before a rule changed is
 * corrected on the next visit instead of printing wrongly — a diploma gains the QR
 * block it needs, and a thank-you letter loses a field the kind has since given up
 * (the participant's name, once letters became one-per-teacher). Removing it here
 * matters beyond tidiness: the backend refuses to save a layout carrying a field
 * its kind disallows, so a stale element left on the canvas would block every
 * further edit with an error about something the organizer cannot see is wrong.
 *
 * Returns the very same array when nothing changed — the caller uses that to tell
 * whether the layout now differs from what is stored.
 */
export function withRequiredFields(
  fields: TemplateField[],
  documentType: DocumentType | string,
): TemplateField[] {
  const allowed = fields.filter((field) => allowsFieldType(documentType, field.type));
  const missing = requiredFieldTypes(documentType).filter(
    (type) => !allowed.some((field) => field.type === type),
  );
  if (missing.length === 0) {
    return allowed.length === fields.length ? fields : allowed;
  }
  return [...allowed, ...missing.map((type) => createField(type, 1))];
}
