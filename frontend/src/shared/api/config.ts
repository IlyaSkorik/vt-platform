import { env } from "@/shared/config";

/**
 * Transport policies for the HTTP client, aligned with the API standard.
 *
 * - Timeout: bounded per request (API-000 §19.2).
 * - Retry: only safe/idempotent methods, only on transient statuses
 *   (429, 502, 503, 504), with exponential backoff + jitter (API-000 §19.2).
 *   Non-idempotent writes are never auto-retried by the transport — that is the
 *   caller's responsibility using an `Idempotency-Key` (API-000 §19.1).
 */
export const API_TIMEOUT_MS = env.apiTimeout;

export const RETRYABLE_STATUS_CODES = [429, 502, 503, 504] as const;

export const RETRYABLE_METHODS = ["get", "head", "options", "put", "delete"] as const;

export const RETRY_LIMIT = 2;

/** Standard header names used across request/response hooks (API-000 §6). */
export const HEADER = {
  authorization: "Authorization",
  requestId: "X-Request-ID",
  idempotencyKey: "Idempotency-Key",
  ifMatch: "If-Match",
  acceptLanguage: "Accept-Language",
} as const;

/** Primary locale (ARCH-001 §8.6 — ru-RU primary, i18n-ready). */
export const DEFAULT_LOCALE = "ru-RU";
