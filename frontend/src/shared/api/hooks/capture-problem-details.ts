import type { AfterResponseHook } from "ky";
import { HEADER } from "../config";
import type { ProblemDetails } from "../error";
import { storeProblem } from "../problem-cache";

/**
 * Problem-capture hook (response).
 *
 * Runs before Ky turns a non-2xx response into an `HTTPError` (which consumes
 * the body). For a failed `application/*json` response it clones and parses the
 * RFC 9457 Problem Details (API-000 §8) while the body is still readable, then
 * stashes it keyed by the request's correlation id so `toApiError` can attach
 * it to the thrown `ApiError`. The clone leaves the original body intact for
 * every downstream consumer.
 */
export const captureProblemDetails: AfterResponseHook = async ({ request, response }) => {
  if (response.ok) {
    return response;
  }
  const contentType = response.headers.get("content-type") ?? "";
  if (!contentType.includes("json")) {
    return response;
  }
  const requestId = request.headers.get(HEADER.requestId);
  if (!requestId) {
    return response;
  }
  try {
    const body = (await response.clone().json()) as Partial<ProblemDetails>;
    if (body && typeof body === "object") {
      storeProblem(requestId, {
        type: body.type ?? "about:blank",
        title: body.title ?? response.statusText,
        status: body.status ?? response.status,
        ...body,
      } as ProblemDetails);
    }
  } catch {
    /* Not valid JSON — leave nothing cached; toApiError falls back gracefully. */
  }
  return response;
};
