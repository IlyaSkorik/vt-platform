import {
  DEFAULT_FIELD_STYLE,
  defaultBindingForType,
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

/** Create a new field centred on the given page, bound to its type's data source. */
export function createField(type: TemplateFieldTypeId, page: number): TemplateField {
  return {
    id: createUuidV7(),
    page,
    type,
    binding: defaultBindingForType(type),
    x: (1 - DEFAULT_WIDTH) / 2,
    y: (1 - DEFAULT_HEIGHT) / 2,
    width: DEFAULT_WIDTH,
    height: DEFAULT_HEIGHT,
    style: { ...DEFAULT_FIELD_STYLE },
  };
}
