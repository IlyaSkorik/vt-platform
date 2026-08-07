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
  return `${apiOrigin()}${value.startsWith("/") ? value : `/${value}`}`;
}

/**
 * The origin the API — and therefore `/media/…` — is served from.
 *
 * `env.apiBaseUrl` is `/api/v1` whenever `VITE_API_BASE_URL` is left empty, which is
 * how this is deployed: nginx fronts the SPA and the API together, so the client
 * calls the origin it was served from. `new URL()` on a path with no base throws
 * ("Failed to construct 'URL': Invalid URL"), so passing the document's own origin
 * as the base is what makes the relative case work at all — and it is ignored
 * outright when the configured value is already absolute, which is the local shape.
 *
 * Only references that are *not* already absolute reach here, and with a bucket
 * configured the backend hands back absolute URLs — which is why this went
 * unnoticed: it fires on the paths a bucket does not cover, such as an uploaded
 * font, and takes the whole editor down with it.
 */
function apiOrigin(): string {
  const base = typeof window === "undefined" ? env.siteUrl : window.location.origin;
  return new URL(env.apiBaseUrl, base).origin;
}
