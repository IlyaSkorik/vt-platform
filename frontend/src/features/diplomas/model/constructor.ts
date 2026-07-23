import {
  Baby,
  Building2,
  Calendar,
  GraduationCap,
  Hash,
  type LucideIcon,
  Music,
  QrCode,
  Tag,
  Type,
  Users,
} from "lucide-react";
import type { TemplateFieldBinding } from "./binding";

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
  | "nomination"
  | "work"
  | "age_category"
  | "teacher"
  | "organization"
  | "date"
  | "diploma_number"
  | "qr"
  | "free_text";

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
  icon: LucideIcon;
}

export const FIELD_TYPES: readonly TemplateFieldType[] = [
  { id: "participant_name", label: "ФИО / Коллектив", binding: "data", icon: Users },
  { id: "nomination", label: "Номинация", binding: "data", icon: Tag },
  { id: "work", label: "Произведение", binding: "data", icon: Music },
  { id: "age_category", label: "Возрастная категория", binding: "data", icon: Baby },
  { id: "teacher", label: "Педагог", binding: "data", icon: GraduationCap },
  { id: "organization", label: "Организация", binding: "data", icon: Building2 },
  { id: "date", label: "Дата", binding: "data", icon: Calendar },
  { id: "diploma_number", label: "Номер диплома", binding: "data", icon: Hash },
  { id: "qr", label: "QR", binding: "data", icon: QrCode },
  { id: "free_text", label: "Свободный текст", binding: "free", icon: Type },
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
