import { apiClient, toApiError } from "./client";
import { DOWNLOAD_TIMEOUT_MS } from "./config";

/**
 * Fetching an authenticated download and handing it to the browser.
 *
 * A plain `<a href>` cannot do this: these endpoints need the same auth as every
 * other request, and the link would arrive without it. So the body is fetched
 * through the shared pipeline, turned into an object URL, and clicked — which is
 * also why the archive endpoints assemble per request rather than publishing a
 * public file nobody could invalidate.
 *
 * Lives in `shared/api` rather than in a feature because two of them already need
 * it (the programme's ZIPs and the cabinet's diploma bundle) and neither should own
 * the other's copy.
 */

/** Read the server's chosen filename out of a Content-Disposition header. */
export function filenameFromDisposition(disposition: string | null): string | null {
  if (!disposition) {
    return null;
  }
  const encoded = /filename\*=UTF-8''([^;]+)/i.exec(disposition);
  if (encoded?.[1]) {
    try {
      return decodeURIComponent(encoded[1]);
    } catch {
      // A malformed header is not worth failing a download over.
    }
  }
  return /filename="([^"]+)"/i.exec(disposition)?.[1] ?? null;
}

/**
 * Download `path` under the name the server chose, falling back to `fallbackName`.
 *
 * The server's own filename wins when it sends one — it knows the festival's real,
 * Cyrillic name, which the client would have to reconstruct.
 */
export async function saveAuthenticatedDownload(path: string, fallbackName: string): Promise<void> {
  let blob: Blob;
  let disposition: string | null;
  try {
    // Not the shared policy: a download waits out a server that is still assembling the
    // file, and it is never retried. `retry: 0` matters as much as the timeout — GET is
    // retryable by default, so a ZIP that timed out was re-requested twice more, and the
    // server rebuilt the whole archive each time while the organizer saw one spinner.
    const response = await apiClient(path, { timeout: DOWNLOAD_TIMEOUT_MS, retry: 0 });
    blob = await response.blob();
    disposition = response.headers.get("Content-Disposition");
  } catch (error) {
    throw await toApiError(error);
  }
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = filenameFromDisposition(disposition) ?? fallbackName;
  document.body.append(link);
  link.click();
  link.remove();
  // Revoking immediately can cancel the download in some browsers; a tick is enough.
  setTimeout(() => URL.revokeObjectURL(url), 1_000);
}
