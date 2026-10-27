import { QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import type React from "react";
import { afterEach, describe, expect, it, vi } from "vitest";

import type { Protocol, PublicationJob } from "@/features/jury-protocols";
import { createQueryClient } from "@/shared/api/query-client";

import { PublicationStatus } from "./publication-status";

/**
 * Публикация отвечает, как только итоги публичны, а дипломы выпускает воркер — значит,
 * единственное место, где эта работа вообще видна организатору, это экран. Здесь
 * закреплено то, что в нём может сломаться тихо: что идущий прогон виден, что о
 * законченном сообщают ровно один раз (опрос идёт каждые 2.5 секунды, и наивный эффект
 * повторял бы тост на каждом ответе), и что упавший прогон не выглядит успешным.
 */

const toasts = vi.hoisted(() => ({
  success: vi.fn(),
  warning: vi.fn(),
  error: vi.fn(),
}));

vi.mock("@/shared/ui", async (importOriginal) => ({
  ...(await importOriginal<Record<string, unknown>>()),
  toast: toasts,
}));

const PROTOCOL_ID = "11111111-1111-1111-1111-111111111111";

function protocol(): Protocol {
  return {
    id: PROTOCOL_ID,
    competitionId: "22222222-2222-2222-2222-222222222222",
    nominationId: "33333333-3333-3333-3333-333333333333",
    nomination: "Вокал",
    competitionTitle: "Взлёт талантов",
    name: "Вокал",
    status: "PUBLISHED",
    rows: [],
    availableColumns: [],
    publicColumns: [],
    awardOptions: [],
    // Больше нуля: протокол публиковали, значит доводка у него может быть.
    revision: 1,
    slug: "Vokas2345",
    path: "/protocol/Vokas2345",
    publishedAt: "2026-10-27T10:00:00Z",
    hasUnpublishedChanges: false,
    seededFromProgramId: null,
    createdAt: "2026-10-27T09:00:00Z",
    updatedAt: "2026-10-27T10:00:00Z",
    version: 3,
  };
}

function job(overrides: Partial<PublicationJob> = {}): PublicationJob {
  return {
    jobId: "44444444-4444-4444-4444-444444444444",
    protocolId: PROTOCOL_ID,
    revision: 1,
    notify: true,
    status: "RUNNING",
    result: null,
    error: null,
    createdAt: "2026-10-27T10:00:00Z",
    updatedAt: "2026-10-27T10:00:00Z",
    ...overrides,
  };
}

function json(body: PublicationJob | null): Response {
  return new Response(JSON.stringify({ data: body }), {
    status: 200,
    headers: { "Content-Type": "application/json" },
  });
}

function wrapper(): ({ children }: { children: React.ReactNode }) => React.JSX.Element {
  const client = createQueryClient();
  return ({ children }) => <QueryClientProvider client={client}>{children}</QueryClientProvider>;
}

afterEach(() => {
  vi.unstubAllGlobals();
  toasts.success.mockClear();
  toasts.warning.mockClear();
  toasts.error.mockClear();
});

describe("доводка публикации на экране протокола", () => {
  it("показывает идущий выпуск и докладывает о нём ровно один раз", async () => {
    const answers = [job(), job(), job({ status: "COMPLETED", result: results() })];
    const fetchMock = vi.fn(async () =>
      json(answers.shift() ?? job({ status: "COMPLETED", result: results() })),
    );
    vi.stubGlobal("fetch", fetchMock);

    render(<PublicationStatus protocol={protocol()} />, { wrapper: wrapper() });

    expect(await screen.findByText(/Выпускаем дипломы и письма/)).toBeInTheDocument();

    await waitFor(() => expect(toasts.success).toHaveBeenCalledTimes(1), { timeout: 15000 });

    // Дойдя до конца, опрос останавливается — иначе экран ходил бы на сервер каждые 2.5
    // секунды до конца фестиваля и повторял бы тост на каждом ответе.
    const settled = fetchMock.mock.calls.length;
    await new Promise((resolve) => setTimeout(resolve, 3000));
    expect(fetchMock.mock.calls.length).toBe(settled);
    expect(toasts.success).toHaveBeenCalledTimes(1);
    expect(toasts.error).not.toHaveBeenCalled();
  }, 30000);

  it("о номерах без диплома предупреждает отдельно", async () => {
    const answers = [job(), job({ status: "COMPLETED", result: results({ diplomasMissing: 12 }) })];
    vi.stubGlobal(
      "fetch",
      vi.fn(async () =>
        json(
          answers.shift() ?? job({ status: "COMPLETED", result: results({ diplomasMissing: 12 }) }),
        ),
      ),
    );

    render(<PublicationStatus protocol={protocol()} />, { wrapper: wrapper() });

    await waitFor(() => expect(toasts.warning).toHaveBeenCalledTimes(1), { timeout: 15000 });
    expect(String(toasts.warning.mock.calls[0]?.[0])).toContain("Без диплома осталось 12");
    // Публикация при этом прошла: красным это не называется.
    expect(toasts.error).not.toHaveBeenCalled();
  }, 30000);

  it("упавший прогон виден на экране и не выдаётся за успех", async () => {
    const answers = [job(), job({ status: "FAILED", error: "Шаблон диплома повреждён" })];
    vi.stubGlobal(
      "fetch",
      vi.fn(async () =>
        json(answers.shift() ?? job({ status: "FAILED", error: "Шаблон диплома повреждён" })),
      ),
    );

    render(<PublicationStatus protocol={protocol()} />, { wrapper: wrapper() });

    expect(
      await screen.findByText(/выпущены не до конца/, undefined, { timeout: 15000 }),
    ).toBeInTheDocument();
    await waitFor(() => expect(toasts.error).toHaveBeenCalledTimes(1), { timeout: 15000 });
    expect(toasts.success).not.toHaveBeenCalled();
  }, 30000);

  it("непубликовавшийся протокол не опрашивает вовсе", async () => {
    const fetchMock = vi.fn(async () => json(null));
    vi.stubGlobal("fetch", fetchMock);

    render(<PublicationStatus protocol={{ ...protocol(), revision: 0, status: "DRAFT" }} />, {
      wrapper: wrapper(),
    });

    await new Promise((resolve) => setTimeout(resolve, 100));
    expect(fetchMock).not.toHaveBeenCalled();
  });
});

function results(
  overrides: Partial<PublicationJob["result"] & object> = {},
): NonNullable<PublicationJob["result"]> {
  return {
    diplomasAwarded: 144,
    diplomasCreated: 144,
    diplomasMissing: 0,
    lettersSent: 90,
    lettersSkipped: 0,
    ...overrides,
  };
}
