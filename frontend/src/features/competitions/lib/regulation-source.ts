import { isExternalDocLink } from "@/shared/lib";

/**
 * How a regulation's `fileReference` was supplied:
 * - `file` — an uploaded PDF, stored as a relative media path.
 * - `link` — an external document URL (e.g. a Google Docs share link) that the
 *   organizer keeps editing while the reference stays stable.
 */
export type RegulationSourceType = "file" | "link";

/** Infer the source kind from the stored reference (absolute URL ⇒ link). */
export function detectRegulationSource(
  fileReference: string | null | undefined,
): RegulationSourceType {
  return isExternalDocLink(fileReference) ? "link" : "file";
}
