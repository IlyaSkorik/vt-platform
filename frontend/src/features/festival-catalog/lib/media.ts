/**
 * Re-exported from `shared/lib`, where the rule now lives: resolving a stored
 * `/media/…` reference against the API origin is platform-wide (a diploma's
 * official PDF needs it too), not specific to the festival catalog. Kept here so
 * the catalog's existing consumers keep their import path.
 */
export { resolveMediaUrl } from "@/shared/lib";
