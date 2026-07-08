import type { BeforeRequestHook } from "ky";
import { DEFAULT_LOCALE, HEADER } from "../config";

/**
 * Request-context hook (request).
 *
 * - Generates a client `X-Request-ID` correlation id when the caller has not
 *   supplied one, so a single request can be traced end-to-end through logs
 *   (ARCH-001 §19.1, API-000 §6.1).
 * - Sets the primary locale via `Accept-Language` (ARCH-001 §8.6).
 */
export const attachRequestContext: BeforeRequestHook = ({ request }) => {
  if (!request.headers.has(HEADER.requestId)) {
    request.headers.set(HEADER.requestId, crypto.randomUUID());
  }
  if (!request.headers.has(HEADER.acceptLanguage)) {
    request.headers.set(HEADER.acceptLanguage, DEFAULT_LOCALE);
  }
};
