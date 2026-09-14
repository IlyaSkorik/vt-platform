import { apiClient, toApiError } from "./client";
import { uploadTimeoutMs } from "./config";

/**
 * Custom request mutator used by the Orval-generated SDK.
 *
 * Orval emits typed operations that delegate every network call to this
 * function, so the generated client inherits the shared Ky pipeline — auth,
 * correlation ids, retry/timeout policy — and every failure is normalized into
 * the platform's typed `ApiError` (RFC 9457, API-000 §8).
 *
 * Return shape matches Orval's `fetch` httpClient contract: each operation is
 * typed as `{ status; data }`, so the mutator resolves to that envelope rather
 * than the bare body. A `204`/empty response yields `data: undefined`.
 *
 * The one thing decided here rather than on the instance is the timeout: a
 * multipart body has to *travel* within it, so the ceiling follows the file's
 * size (see `uploadTimeoutMs`). Everything else keeps `API_TIMEOUT_MS`.
 */
export const customInstance = async <T>(url: string, options: RequestInit = {}): Promise<T> => {
  try {
    // Ky's `prefix` is already `…/api/v1`. Accept both `/competitions` and a
    // defensive `/api/v1/competitions` (e.g. stale generated clients).
    const path = url.replace(/^\/+/, "").replace(/^api\/v1\//, "");
    // Ky resolves the timeout per call, and hooks cannot change it — so it is set
    // here, where the body is still in hand.
    const response = await apiClient(path, { ...options, timeout: uploadTimeoutMs(options.body) });

    const isEmpty = response.status === 204 || response.headers.get("content-length") === "0";
    const contentType = response.headers.get("content-type") ?? "";
    const data = isEmpty
      ? undefined
      : contentType.includes("json")
        ? await response.json()
        : await response.text();

    return { status: response.status, data } as T;
  } catch (error) {
    throw await toApiError(error);
  }
};

export default customInstance;
