/**
 * Re-exported from `shared/lib`, where the rule lives.
 *
 * This used to be a second copy, and it drifted: it carried its own `new URL()`
 * that threw on a relative API base, and it lacked the `blob:`/`data:`
 * passthrough the shared one had grown. One rule, one place — a stored reference
 * resolves the same way whether it is a font, a gallery image or a diploma PDF.
 */
export { resolveMediaUrl } from "@/shared/lib";
