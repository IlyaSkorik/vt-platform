import ky, { type KyInstance } from "ky";
import { env } from "@/shared/config";
import { API_TIMEOUT_MS, RETRY_LIMIT, RETRYABLE_METHODS, RETRYABLE_STATUS_CODES } from "./config";
import { toApiError } from "./error";
import {
  attachActingOrganization,
  attachAuth,
  attachRequestContext,
  captureProblemDetails,
  refreshOnUnauthorized,
} from "./hooks";

/**
 * The single HTTP client for the entire SPA (Ky — never Axios, ARCH-001 §8.5).
 *
 * All network traffic — hand-written and Orval-generated alike — flows through
 * this instance so cross-cutting concerns live in exactly one place:
 *
 * - `prefix`     — every path is joined onto the versioned API base (leading
 *   slashes on the input are tolerated and normalized).
 * - `credentials: "include"` — sends the httpOnly refresh cookie (API-001 §3).
 * - Timeout policy — bounded per request (API-000 §19.2).
 * - Retry policy — safe/idempotent methods only, transient statuses only, with
 *   exponential backoff + jitter (Ky's built-in retry, API-000 §19.2).
 * - Hooks — authorization, request-context/correlation, refresh placeholder.
 * - `beforeError` — normalizes every failure into a typed `ApiError`.
 */
export const apiClient: KyInstance = ky.create({
  prefix: env.apiBaseUrl,
  credentials: "include",
  timeout: API_TIMEOUT_MS,
  retry: {
    limit: RETRY_LIMIT,
    methods: [...RETRYABLE_METHODS],
    statusCodes: [...RETRYABLE_STATUS_CODES],
    backoffLimit: 10_000,
  },
  headers: {
    Accept: "application/json",
  },
  hooks: {
    beforeRequest: [attachAuth, attachRequestContext, attachActingOrganization],
    afterResponse: [captureProblemDetails, refreshOnUnauthorized],
    beforeError: [
      // Passthrough seam. Full Problem Details parsing (async) happens in
      // `toApiError` at call sites via the Orval mutator, which turns every
      // failure into a typed `ApiError`; this hook keeps the raw error intact
      // for that mapping while providing a single place to add crash reporting.
      (state) => state.error,
    ],
  },
});

/** Re-map a caught client error into the platform's typed error. */
export { toApiError };
