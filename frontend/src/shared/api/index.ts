/**
 * Public API of the `shared/api` segment.
 *
 * Feature and entity code imports from here — never from deep paths — so the
 * transport internals (Ky instance, hooks, mutator) remain private.
 */
export { apiClient, toApiError } from "./client";
export { DEFAULT_LOCALE, HEADER } from "./config";
export { filenameFromDisposition, saveAuthenticatedDownload } from "./download";
export {
  ApiError,
  type ProblemDetails,
  type ProblemFieldError,
} from "./error";
export { createQueryClient } from "./query-client";
export { refreshAccessToken } from "./refresh";
export {
  emitSessionEvent,
  onSessionEvent,
  type SessionEvent,
} from "./session-events";
export { type TokenStore, tokenStore } from "./token-store";
