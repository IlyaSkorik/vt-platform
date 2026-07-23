import {
  DEFAULT_FIELD_STYLE,
  type TemplateField,
  type TemplateFieldTypeId,
} from "@/features/diplomas";
import { createUuidV7 } from "@/shared/lib";

/** Default normalised size of a freshly-added field. */
const DEFAULT_WIDTH = 0.5;
const DEFAULT_HEIGHT = 0.07;

/**
 * Minimum normalised size a field may be resized to — the equivalent of roughly
 * 40×20 px on a typical page, but resolution-independent.
 */
export const MIN_WIDTH = 0.05;
export const MIN_HEIGHT = 0.025;

/** Normalised offset a duplicate is nudged by so it doesn't hide the original. */
export const DUPLICATE_OFFSET = 0.03;

/**
 * Sample text shown for each field kind until real data binding lands. Only
 * `participant_name` is placeable for now; the rest are the type foundation.
 */
export const FIELD_PLACEHOLDERS: Record<TemplateFieldTypeId, string> = {
  participant_name: "Иванов Иван Иванович",
  nomination: "Номинация",
  work: "Произведение",
  age_category: "Возрастная категория",
  teacher: "Педагог",
  organization: "Организация",
  date: "01.01.2026",
  diploma_number: "№ 000",
  qr: "QR",
  free_text: "Текст",
};

/** Create a new field centred on the given page. */
export function createField(type: TemplateFieldTypeId, page: number): TemplateField {
  return {
    id: createUuidV7(),
    page,
    type,
    x: (1 - DEFAULT_WIDTH) / 2,
    y: (1 - DEFAULT_HEIGHT) / 2,
    width: DEFAULT_WIDTH,
    height: DEFAULT_HEIGHT,
    style: { ...DEFAULT_FIELD_STYLE },
  };
}
