import { env } from "@/shared/config";

/**
 * Resolve a stored `/media/…` file reference into an absolute URL the browser
 * can load. Absolute `http(s)` references are returned unchanged. Media lives at
 * the API origin (not under the `/api/v1` prefix), so we take the origin only.
 */
export function resolveMediaUrl(reference: string | null | undefined): string | null {
  const value = reference?.trim();
  if (!value) {
    return null;
  }
  if (/^https?:\/\//i.test(value)) {
    return value;
  }
  const origin = new URL(env.apiBaseUrl).origin;
  return `${origin}${value.startsWith("/") ? value : `/${value}`}`;
}
