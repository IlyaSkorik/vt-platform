import { HTTPError, TimeoutError } from "ky";
import { takeProblem } from "./problem-cache";

/**
 * RFC 9457 Problem Details — the platform's single error contract
 * (API-000 §8). Every non-2xx response is `application/problem+json`.
 */
export interface ProblemDetails {
  /** Stable URI identifying the problem class. */
  type: string;
  /** Short, human-readable summary (stable per `type`). */
  title: string;
  /** HTTP status code. */
  status: number;
  /** Request-specific explanation. */
  detail?: string;
  /** The request path. */
  instance?: string;
  /** Machine-readable code — for rule violations, the DATA-002 rule id. */
  code?: string;
  /** Correlation id for support/audit (API-000 §6). */
  requestId?: string;
  /** Field/rule-level details. */
  errors?: ProblemFieldError[];
  /** Extension members are permitted by RFC 9457. */
  [key: string]: unknown;
}

export interface ProblemFieldError {
  /** JSON Pointer to the offending field. */
  pointer?: string;
  /** Rule/validation id. */
  code?: string;
  /** Human-readable detail. */
  detail?: string;
}

/**
 * Normalized application error. All network failures — HTTP errors, timeouts,
 * and connectivity problems — are mapped to this single type so UI and
 * TanStack Query error boundaries have one shape to reason about.
 */
export class ApiError extends Error {
  readonly status: number;
  readonly code: string | undefined;
  readonly requestId: string | undefined;
  readonly problem: ProblemDetails | undefined;
  readonly fieldErrors: ProblemFieldError[];

  constructor(
    message: string,
    options: {
      status: number;
      code?: string | undefined;
      requestId?: string | undefined;
      problem?: ProblemDetails | undefined;
      cause?: unknown;
    },
  ) {
    super(message, { cause: options.cause });
    this.name = "ApiError";
    this.status = options.status;
    this.code = options.code;
    this.requestId = options.requestId;
    this.problem = options.problem;
    this.fieldErrors = options.problem?.errors ?? [];
  }

  /** Authentication missing/expired — the client should (re)authenticate. */
  get isUnauthorized(): boolean {
    return this.status === 401;
  }

  /** Authenticated but not permitted (RBAC/scoping). */
  get isForbidden(): boolean {
    return this.status === 403;
  }

  /** Business-rule violation (422) — `code` carries the DATA-002 rule id. */
  get isBusinessRuleViolation(): boolean {
    return this.status === 422;
  }

  /** State/version conflict (409) — retry after refetch may succeed. */
  get isConflict(): boolean {
    return this.status === 409;
  }
}

const STATUS_ZERO = 0;

/** Cyrillic anywhere in a message is the sign it was written for a person to read. */
const CYRILLIC = /[\u0400-\u04FF]/;

/**
 * What to show when the server's own wording cannot be shown.
 *
 * The API guarantees a Russian `detail` on every problem document, so this is for
 * what falls outside that contract: a proxy's plain `502`, a Django error page, a
 * dropped connection. `statusText` and a thrown `Error.message` are English by
 * construction (they come from the platform, not from us), so they are never shown —
 * the status alone tells the reader as much as they can act on.
 */
function fallbackMessage(status: number): string {
  if (status === 0) {
    return "Нет связи с сервером. Проверьте интернет и попробуйте ещё раз.";
  }
  if (status === 401) {
    return "Сессия истекла — войдите заново.";
  }
  if (status === 403) {
    return "Нет доступа к этому действию.";
  }
  if (status === 404) {
    return "Не найдено — возможно, запись была удалена.";
  }
  if (status === 409) {
    return "Данные изменились — обновите страницу и повторите.";
  }
  if (status === 413) {
    return "Файл слишком большой.";
  }
  if (status === 429) {
    return "Слишком много запросов. Подождите немного и повторите.";
  }
  if (status === 422) {
    return "Действие сейчас недоступно: не выполнены условия.";
  }
  if (status >= 500) {
    return "Сервер не ответил. Мы уже знаем о проблеме — попробуйте ещё раз позже.";
  }
  return "Не удалось выполнить действие. Попробуйте ещё раз.";
}

/**
 * A server message is shown only if it is addressed to a person — that is, in Russian.
 *
 * Exported because the same judgement is needed wherever a response body is read
 * outside the Ky pipeline (the platform console, the staff bulk actions): whatever
 * the server said, the reader gets Russian.
 */
export function humanMessage(candidate: string | undefined, status: number): string {
  return candidate && CYRILLIC.test(candidate) ? candidate : fallbackMessage(status);
}

/**
 * Convert any thrown Ky error into a typed {@link ApiError}. Used by the
 * client's `beforeError` hook and the Orval mutator so no raw `HTTPError`
 * leaks into feature code.
 */
export async function toApiError(error: unknown): Promise<ApiError> {
  if (error instanceof ApiError) {
    return error;
  }

  if (error instanceof HTTPError) {
    const { response, request } = error;
    // The correlation id is set on the request by our hook and echoed by the
    // server on the response; read the request first (always present) and fall
    // back to the response header.
    const requestId =
      request?.headers.get("x-request-id") ?? response.headers.get("x-request-id") ?? undefined;
    // Prefer the body captured (intact) by the afterResponse hook; Ky consumes
    // the response body when it builds the HTTPError, so a direct re-read here
    // would fail. Fall back to a best-effort parse for non-Ky call sites.
    const problem =
      (requestId ? takeProblem(requestId) : undefined) ?? (await parseProblemDetails(response));
    const message = humanMessage(problem?.detail ?? problem?.title, response.status);
    return new ApiError(message, {
      status: response.status,
      code: problem?.code,
      requestId: problem?.requestId ?? requestId,
      problem,
      cause: error,
    });
  }

  if (error instanceof TimeoutError) {
    return new ApiError("Сервер долго не отвечает. Попробуйте ещё раз.", {
      status: STATUS_ZERO,
      cause: error,
    });
  }

  return new ApiError(fallbackMessage(STATUS_ZERO), { status: STATUS_ZERO, cause: error });
}

async function parseProblemDetails(response: Response): Promise<ProblemDetails | undefined> {
  const contentType = response.headers.get("content-type") ?? "";
  if (!contentType.includes("json")) {
    return undefined;
  }
  try {
    const body = (await response.clone().json()) as Partial<ProblemDetails>;
    if (body && typeof body === "object") {
      return {
        type: body.type ?? "about:blank",
        title: body.title ?? response.statusText,
        status: body.status ?? response.status,
        ...body,
      } as ProblemDetails;
    }
  } catch {
    /* Body was not valid JSON — fall through to undefined. */
  }
  return undefined;
}
