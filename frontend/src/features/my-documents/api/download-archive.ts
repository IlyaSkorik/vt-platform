import { saveAuthenticatedDownload } from "@/shared/api";

/**
 * Download one entry's individual diplomas as a single ZIP.
 *
 * An ensemble of twelve produces twelve diplomas, and clicking twelve links is not
 * how anybody hands them out. The archive is assembled by the server per request, so
 * it always carries what the cabinet is currently showing — a corrected protocol
 * re-renders the diplomas, and the next download simply has the corrected ones.
 *
 * Fetched rather than linked because the endpoint is authenticated; the server's own
 * filename (with the festival's name in it) wins over the fallback.
 */
export async function downloadIndividualDiplomas(submissionId: string): Promise<void> {
  await saveAuthenticatedDownload(
    `me/documents/archive?submissionId=${encodeURIComponent(submissionId)}`,
    "Дипломы участников.zip",
  );
}
