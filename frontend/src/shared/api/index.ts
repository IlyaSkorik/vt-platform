/**
 * Public API of the `shared/api` segment.
 *
 * Feature and entity code imports from here — never from deep paths — so the
 * transport internals (Ky instance, hooks, mutator) remain private.
 */
export { type ActingOrganization, actingOrganizationStore } from "./acting-organization";
export { apiClient, toApiError } from "./client";
export {
  DEFAULT_LOCALE,
  DOWNLOAD_TIMEOUT_MS,
  GENERATION_TIMEOUT_MS,
  HEADER,
  uploadTimeoutMs,
} from "./config";
export { filenameFromDisposition, saveAuthenticatedDownload } from "./download";
export {
  ApiError,
  humanMessage,
  type ProblemDetails,
  type ProblemFieldError,
} from "./error";
export { type ApiRequestOptions, withTimeout } from "./orval-mutator";
export { createQueryClient } from "./query-client";
export { refreshAccessToken } from "./refresh";
export {
  emitSessionEvent,
  onSessionEvent,
  type SessionEvent,
} from "./session-events";
export { type TokenStore, tokenStore } from "./token-store";
