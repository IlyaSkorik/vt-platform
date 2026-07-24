import {
  Building2,
  Cake,
  Calendar,
  CalendarCheck,
  GraduationCap,
  Hash,
  type LucideIcon,
  MapPin,
  Medal,
  Music,
  QrCode,
  Tag,
  Trophy,
  Type,
  Users,
} from "lucide-react";
import {
  NOMINATION_AGE_CATEGORY,
  NOMINATION_DISCIPLINE,
  NOMINATION_PARTICIPANT_GROUP,
  NOMINATION_TITLE,
  type TemplateFieldBinding,
} from "./binding";

/**
 * Domain model of the future diploma template constructor.
 *
 * These types intentionally describe the *whole* editor even though the current
 * milestone only ships the page skeleton. They stake out the shape the next
 * stages (PDF upload, visual field placement, versioning) will fill in, so
 * adding drag & drop and data binding later is additive — no restructuring.
 *
 * Planned entities (mirror the backend models to come):
 *   Template          — the library item (already exists: DiplomaTemplate)
 *   TemplateDocument  — the backing PDF a template is marked up over
 *   TemplateField     — a field placed on the canvas (position + style + binding)
 *   TemplateFieldType — the catalogue of placeable element kinds (below)
 *   TemplateVersion   — a saved snapshot of a template's layout (future)
 */

/** Identifier for a kind of placeable element. */
export type TemplateFieldTypeId =
  // Соло-участник (ФИО) и коллектив — это одно поле «имя участника».
  | "participant_name"
  | "participant_age"
  | "teacher"
  | "organization"
  // Номинация, дисциплина, группа и возрастная категория — один составной блок.
  | "nomination_block"
  | "work"
  | "competition_name"
  | "competition_date"
  | "competition_city"
  | "award_degree"
  | "diploma_number"
  | "diploma_issue_date"
  | "qr"
  | "free_text";

/** A part the nomination block can include. */
export type NominationPartKey = "title" | "discipline" | "participant_group" | "age_category";

/** One selectable part of the nomination block: its label and data source. */
export interface NominationPart {
  key: NominationPartKey;
  label: string;
  binding: TemplateFieldBinding;
}

/**
 * The parts a nomination block can show, in canonical display order. Selecting
 * parts in the inspector never reorders them — the block always reads
 * номинация → дисциплина → группа → возрастная категория.
 */
export const NOMINATION_PARTS: readonly NominationPart[] = [
  { key: "title", label: "Номинация", binding: NOMINATION_TITLE },
  { key: "discipline", label: "Дисциплина", binding: NOMINATION_DISCIPLINE },
  { key: "participant_group", label: "Группа участников", binding: NOMINATION_PARTICIPANT_GROUP },
  { key: "age_category", label: "Возрастная категория", binding: NOMINATION_AGE_CATEGORY },
];

/** Default leading label of a nomination block. */
export const DEFAULT_NOMINATION_PREFIX = "Номинация:";

/**
 * Per-field configuration beyond geometry and style. Only composite fields use
 * it (currently the nomination block); simple fields carry `null`.
 */
export interface TemplateFieldConfig {
  /** Nomination block: part keys to include (rendered in canonical order). */
  parts?: NominationPartKey[];
  /** Nomination block: leading label, e.g. "Номинация:". */
  prefix?: string;
}

/** The default config for a field kind, or null for a simple field. */
export function defaultConfigForType(type: TemplateFieldTypeId): TemplateFieldConfig | null {
  if (type === "nomination_block") {
    return {
      parts: NOMINATION_PARTS.map((part) => part.key),
      prefix: DEFAULT_NOMINATION_PREFIX,
    };
  }
  return null;
}

/** A palette section — fields are grouped by the entity they draw from. */
export type TemplateFieldGroup =
  | "Участник"
  | "Педагог"
  | "Организация"
  | "Номинация"
  | "Произведение"
  | "Конкурс"
  | "Результат"
  | "Диплом"
  | "Прочее";

/** The order palette sections render in. */
export const FIELD_GROUPS: readonly TemplateFieldGroup[] = [
  "Участник",
  "Педагог",
  "Организация",
  "Номинация",
  "Произведение",
  "Конкурс",
  "Результат",
  "Диплом",
  "Прочее",
];

/**
 * A kind of element that can live on a template. The left palette renders from
 * this catalogue; once drag & drop lands, dragging an entry will create a
 * {@link TemplateField} — the palette UI stays exactly the same.
 */
export interface TemplateFieldType {
  id: TemplateFieldTypeId;
  label: string;
  /** Whether the value is bound to competition data or free-form. */
  binding: "data" | "free";
  /** Palette section this element lives under. */
  group: TemplateFieldGroup;
  icon: LucideIcon;
}

export const FIELD_TYPES: readonly TemplateFieldType[] = [
  {
    id: "participant_name",
    label: "ФИО / Коллектив",
    binding: "data",
    group: "Участник",
    icon: Users,
  },
  { id: "participant_age", label: "Возраст", binding: "data", group: "Участник", icon: Cake },
  { id: "teacher", label: "ФИО педагога", binding: "data", group: "Педагог", icon: GraduationCap },
  {
    id: "organization",
    label: "Организация",
    binding: "data",
    group: "Организация",
    icon: Building2,
  },
  { id: "nomination_block", label: "Номинация", binding: "data", group: "Номинация", icon: Tag },
  { id: "work", label: "Произведение", binding: "data", group: "Произведение", icon: Music },
  {
    id: "competition_name",
    label: "Название конкурса",
    binding: "data",
    group: "Конкурс",
    icon: Trophy,
  },
  {
    id: "competition_date",
    label: "Дата конкурса",
    binding: "data",
    group: "Конкурс",
    icon: Calendar,
  },
  { id: "competition_city", label: "Город", binding: "data", group: "Конкурс", icon: MapPin },
  { id: "award_degree", label: "Степень", binding: "data", group: "Результат", icon: Medal },
  { id: "diploma_number", label: "Номер диплома", binding: "data", group: "Диплом", icon: Hash },
  {
    id: "diploma_issue_date",
    label: "Дата выдачи",
    binding: "data",
    group: "Диплом",
    icon: CalendarCheck,
  },
  { id: "qr", label: "QR", binding: "data", group: "Прочее", icon: QrCode },
  { id: "free_text", label: "Свободный текст", binding: "free", group: "Прочее", icon: Type },
];

/** Horizontal anchor for a field's text (future property panel). */
export type TemplateTextAlign = "left" | "center" | "right";
export type TemplateFontWeight = "normal" | "bold";
export type TemplateFontStyle = "normal" | "italic";

/**
 * The appearance of a placed field — its single source of truth. Kept as one
 * object (not scattered `fontSize`/`fontWeight`/… across components) so the
 * inspector, renderer and persistence all speak the same model. `fontSize` and
 * `letterSpacing` are in PDF points; `lineHeight` is a unitless multiplier.
 */
export interface TemplateFieldStyle {
  fontFamily: string;
  fontSize: number;
  fontWeight: TemplateFontWeight;
  fontStyle: TemplateFontStyle;
  underline: boolean;
  textAlign: TemplateTextAlign;
  color: string;
  lineHeight: number;
  letterSpacing: number;
  /** Shrink the font so the text fits its box. */
  autoShrink: boolean;
  /** Wrap long text onto multiple lines (otherwise it stays on one line). */
  wrapText: boolean;
}

/** Initial text of a newly-added free-text field. */
export const DEFAULT_FREE_TEXT = "Новый текст";

/** Appearance applied to every newly-added field. */
export const DEFAULT_FIELD_STYLE: TemplateFieldStyle = {
  fontFamily: "Montserrat",
  fontSize: 24,
  fontWeight: "normal",
  fontStyle: "normal",
  underline: false,
  textAlign: "center",
  color: "#000000",
  lineHeight: 1.2,
  letterSpacing: 0,
  autoShrink: true,
  wrapText: false,
};

/**
 * A field placed on the template overlay. The single source of truth for a
 * placed element — pure data, no view concerns (rendering lives in
 * `FieldRenderer`, interaction in `FieldInteraction`).
 *
 * Coordinates are **normalised** (0..1) relative to the page: `x`/`y` are the
 * box's top-left, `width`/`height` its size. Normalised units survive zoom,
 * Fit Width/Page and different resolutions — never store pixels. `width`/`height`
 * are auto-computed defaults for now (no resize yet).
 */
export interface TemplateField {
  id: string;
  /** 1-based page the field lives on. */
  page: number;
  type: TemplateFieldTypeId;
  /**
   * A field is either **data-bound** or **free**:
   * - bound: `binding` set (e.g. `participant.display_name`), `value` is null;
   * - free: `value` holds its own text, `binding` is null.
   */
  binding: TemplateFieldBinding | null;
  value: string | null;
  x: number;
  y: number;
  width: number;
  height: number;
  /** Appearance (font, colour, alignment, …). */
  style: TemplateFieldStyle;
  /** Composite-field configuration (nomination block); null for simple fields. */
  config: TemplateFieldConfig | null;
}

/**
 * A single rendered page of the template's PDF and its coordinate system.
 *
 * `width`/`height` are the PDF's native (scale-1) dimensions in points; `scale`
 * is the current display zoom. A future field at normalised (nx, ny) in [0..1]
 * renders on the overlay at `nx * width * scale` / `ny * height * scale` — so
 * positions survive zoom. The transparent overlay lives above the page canvas;
 * the PDF itself is never drawn on.
 */
export interface TemplatePage {
  /** 1-based page number. */
  pageNumber: number;
  /** Native page width in PDF points (scale 1). */
  width: number;
  /** Native page height in PDF points (scale 1). */
  height: number;
  /** Current display scale (zoom). */
  scale: number;
}

/** The PDF a template is marked up over. Uploaded in a later milestone. */
export interface TemplateDocument {
  id: string;
  templateId: string;
  /** Storage reference used to fetch the file for viewing. */
  fileReference: string;
  /** Resolved URL for the viewer, when available. */
  url?: string;
  pageCount: number;
  uploadedAt: string;
}

/** A saved snapshot of a template's document + fields. Future. */
export interface TemplateVersion {
  id: string;
  templateId: string;
  version: number;
  createdAt: string;
}
