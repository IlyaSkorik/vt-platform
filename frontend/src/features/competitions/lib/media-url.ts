import { env } from "@/shared/config";

/** Resolve a stored media/file reference into a browser-loadable URL. */
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
