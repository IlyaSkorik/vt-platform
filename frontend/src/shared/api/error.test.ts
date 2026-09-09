import { HTTPError, TimeoutError } from "ky";
import { describe, expect, it } from "vitest";

import { toApiError } from "./error";

/** A Ky HTTPError over a synthetic response, as the client would produce. */
function httpError(status: number, body?: unknown, statusText = "Conflict"): HTTPError {
  const response = new Response(body == null ? null : JSON.stringify(body), {
    status,
    statusText,
    headers: body == null ? {} : { "content-type": "application/problem+json" },
  });
  return new HTTPError(response, new Request("https://api.test/x"), {} as never);
}

describe("toApiError — what the reader is shown", () => {
  it("shows the server's own wording when it is addressed to a person", async () => {
    const error = await toApiError(
      httpError(409, {
        type: "conflict",
        title: "Conflict",
        status: 409,
        detail: "Эта почта уже занята.",
      }),
    );

    expect(error.message).toBe("Эта почта уже занята.");
  });

  it("never shows English prose, however the server phrased it", async () => {
    // `title` is English by design (stable per problem type), and a `detail` may come
    // from an edge outside the API's contract — a proxy, a framework error page.
    const error = await toApiError(
      httpError(409, {
        type: "conflict",
        title: "Conflict",
        status: 409,
        detail: "The submission is already approved.",
      }),
    );

    expect(error.message).toBe("Данные изменились — обновите страницу и повторите.");
  });

  it("answers a bodyless failure by its status rather than by statusText", async () => {
    const error = await toApiError(httpError(502, undefined, "Bad Gateway"));

    expect(error.message).toBe(
      "Сервер не ответил. Мы уже знаем о проблеме — попробуйте ещё раз позже.",
    );
    expect(error.status).toBe(502);
  });

  it("says the connection failed, in Russian, when there is no response at all", async () => {
    const error = await toApiError(new TypeError("Failed to fetch"));

    expect(error.message).toBe("Нет связи с сервером. Проверьте интернет и попробуйте ещё раз.");
    expect(error.status).toBe(0);
  });

  it("says the server is slow rather than surfacing the timeout's own words", async () => {
    const error = await toApiError(new TimeoutError(new Request("https://api.test/x")));

    expect(error.message).toBe("Сервер долго не отвечает. Попробуйте ещё раз.");
  });
});
