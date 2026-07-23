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

/** Styling of a placed field. Reserved for the properties panel — not yet edited. */
export interface TemplateFieldStyle {
  fontFamily: string;
  fontSize: number;
  color: string;
  align: TemplateTextAlign;
  /** Wrap long text onto multiple lines. */
  wrap: boolean;
  /** Shrink the font to fit the box. */
  autoShrink: boolean;
}

/**
 * A field placed on the template canvas. Coordinates are normalised (0..1) to
 * the page so they survive zoom and DPI changes. Not created anywhere yet.
 */
export interface TemplateField {
  id: string;
  templateId: string;
  type: TemplateFieldTypeId;
  page: number;
  /** Normalised box on the page. */
  x: number;
  y: number;
  width: number;
  height: number;
  style: TemplateFieldStyle;
  /** Static content for free-text fields; data fields resolve at generation. */
  text?: string;
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
