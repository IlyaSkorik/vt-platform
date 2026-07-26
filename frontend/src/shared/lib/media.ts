import { env } from "@/shared/config";

/**
 * Resolve a stored media/file reference into a browser-loadable URL.
 *
 * Absolute (`http(s):`), `blob:` and `data:` URLs pass through untouched; a
 * relative storage path is joined to the API origin. Returns `null` for empty
 * input so callers render a placeholder.
 *
 * Every backend payload that carries a stored file (competition documents, gallery
 * images, a diploma's official PDF) reports a `/media/…` path rather than a full
 * URL, so this lives in `shared/lib` — it is the platform-wide rule for turning
 * one into a link, not any single feature's concern.
 */
export function resolveMediaUrl(reference: string | null | undefined): string | null {
  const value = reference?.trim();
  if (!value) {
    return null;
  }
  if (/^(https?:|blob:|data:)/i.test(value)) {
    return value;
  }
  const origin = new URL(env.apiBaseUrl).origin;
  return `${origin}${value.startsWith("/") ? value : `/${value}`}`;
}
