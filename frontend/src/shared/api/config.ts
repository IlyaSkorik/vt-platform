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

/**
 * Насколько медленной может оказаться отдача файла, чтобы загрузку всё ещё имело
 * смысл ждать: 32 КБ/с — это плохой мобильный аплинк, но живой.
 */
const UPLOAD_MIN_BYTES_PER_SECOND = 32 * 1024;

/** Нижняя граница: маленький файл всё равно не должен упираться в общий таймаут. */
const UPLOAD_TIMEOUT_FLOOR_MS = 60_000;

/** Верхняя граница: полчаса — уже не «медленно», а «не доедет». */
const UPLOAD_TIMEOUT_CEILING_MS = 30 * 60_000;

/**
 * Сколько ждать этот конкретный запрос.
 *
 * `API_TIMEOUT_MS` описывает обычный JSON-вызов: ответа, которого нет через 15
 * секунд, уже не будет. Для multipart это неверно в самом основании — там за
 * отведённое время должно уехать *тело*, и 124 МБ видео с телефона не уедут за 15
 * секунд ни на одной мобильной сети. Ky обрывает запрос по AbortController, то
 * есть загрузка не «не начиналась», а рвалась на середине: ровно то, на что
 * жаловались как «видео не грузится» и «не могу загрузить фонограмму».
 *
 * Поэтому срок считается от размера тела, а не берётся общим: столько, сколько
 * файл едет на заведомо плохом канале, с полом и потолком. Запрос без файлов
 * возвращает прежний `API_TIMEOUT_MS` — политика для них не менялась.
 */
export function uploadTimeoutMs(body: BodyInit | null | undefined): number {
  const bytes = uploadBytes(body);
  if (bytes === null) {
    return API_TIMEOUT_MS;
  }
  const needed = (bytes / UPLOAD_MIN_BYTES_PER_SECOND) * 1000;
  return Math.min(Math.max(needed, UPLOAD_TIMEOUT_FLOOR_MS), UPLOAD_TIMEOUT_CEILING_MS);
}

/**
 * Сколько байт файлов в теле запроса, или `null`, если это не выгрузка файла.
 *
 * `FormData` не знает своего размера, но знает свои части; всё, что не `Blob`
 * (текстовые поля вроде `attachmentType`), на фоне видео не считается.
 */
function uploadBytes(body: BodyInit | null | undefined): number | null {
  if (typeof FormData !== "undefined" && body instanceof FormData) {
    let total = 0;
    // `forEach`, а не итератор: он есть в lib.dom без `dom.iterable`.
    body.forEach((value) => {
      if (typeof Blob !== "undefined" && value instanceof Blob) {
        total += value.size;
      }
    });
    return total;
  }
  if (typeof Blob !== "undefined" && body instanceof Blob) {
    return body.size;
  }
  return null;
}
