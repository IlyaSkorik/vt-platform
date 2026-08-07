/**
 * Re-exported from `shared/lib`, where the rule lives.
 *
 * This used to be a third copy of the same function, carrying the same `new URL()`
 * that throws on a relative API base. Kept as a module so the feature's existing
 * import paths keep working.
 */
export { resolveMediaUrl } from "@/shared/lib";
