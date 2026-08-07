/**
 * The test bench page.
 *
 * The API layer is mocked rather than the network: `platform-api` talks through
 * the shared Ky instance, and Ky cannot construct a request under jsdom's undici
 * (its AbortSignal fails undici's instanceof check). Stubbing at the hook seam
 * keeps this suite about the page — what it shows, what it refuses, and what it
 * asks for — which is the part worth pinning down anyway.
 */
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import type { LoadTestOverview, LoadTestRun } from "@/applications/platform/api/platform-api";

const start = vi.fn();
const cleanup = vi.fn();
const overview = {
  data: undefined as LoadTestOverview | undefined,
  isLoading: false,
  isError: false,
};

vi.mock("@/applications/platform/api/platform-api", () => ({
  useLoadTestOverview: () => overview,
  useStartLoadTest: () => ({ mutate: start, isPending: false }),
  useCleanupLoadTest: () => ({ mutate: cleanup, isPending: false }),
  refusalMessage: async (_error: unknown, fallback: string) => fallback,
}));

const { PlatformTestingPage } = await import("./index");

const COMPLETED_RUN: LoadTestRun = {
  competitionId: "c1",
  title: "[НАГРУЗОЧНЫЙ ТЕСТ] Генерация дипломов",
  createdAt: "2026-08-07T09:00:00Z",
  entries: 500,
  nominations: 8,
  diplomas: 500,
  rendered: 500,
  status: "COMPLETED",
  elapsedSeconds: 42.5,
  msPerDiploma: 85,
  jobs: [
    {
      jobId: "j1",
      status: "COMPLETED",
      created: 500,
      skipped: 0,
      zipUrl: "/media/diplomas/print/c1/tok/Diplomas.zip",
      error: null,
    },
  ],
};

function overviewWith(runs: LoadTestRun[]): LoadTestOverview {
  return {
    runs,
    templates: [{ id: "t1", name: "Диплом А4" }],
    totals: {
      runs: runs.length,
      entries: runs.reduce((sum, run) => sum + run.entries, 0),
      diplomas: runs.reduce((sum, run) => sum + run.diplomas, 0),
    },
    maxCount: 2000,
  };
}

describe("PlatformTestingPage", () => {
  beforeEach(() => {
    start.mockReset();
    cleanup.mockReset();
    overview.data = overviewWith([COMPLETED_RUN]);
    overview.isLoading = false;
    overview.isError = false;
  });

  it("shows a finished run with the numbers the operator came for", () => {
    render(<PlatformTestingPage />);

    expect(screen.getByText("Завершён")).toBeInTheDocument();
    expect(screen.getByText("500 / 500")).toBeInTheDocument();
    expect(screen.getByText("85 мс")).toBeInTheDocument();
    expect(screen.getByText("42.5 с")).toBeInTheDocument();
    // The projection against the worker's hour-long limit is the point of the page.
    expect(screen.getByText(/1000 дипломов/)).toBeInTheDocument();
  });

  it("starts a run with the parameters on screen", async () => {
    const user = userEvent.setup();
    render(<PlatformTestingPage />);

    await user.click(screen.getByRole("button", { name: "Запустить прогон" }));

    expect(start).toHaveBeenCalledTimes(1);
    expect(start.mock.calls[0]?.[0]).toMatchObject({
      count: 500,
      nominations: 8,
      split: false,
      force: false,
    });
  });

  it("refuses a tirage above the server's ceiling without asking the server", async () => {
    const user = userEvent.setup();
    render(<PlatformTestingPage />);

    const count = screen.getByLabelText(/Заявок/);
    await user.clear(count);
    await user.type(count, "5000");

    expect(screen.getByRole("button", { name: "Запустить прогон" })).toBeDisabled();
    expect(start).not.toHaveBeenCalled();
  });

  it("refuses more nominations than entries — every nomination must get one", async () => {
    const user = userEvent.setup();
    render(<PlatformTestingPage />);

    const count = screen.getByLabelText(/Заявок/);
    await user.clear(count);
    await user.type(count, "3");

    expect(screen.getByRole("button", { name: "Запустить прогон" })).toBeDisabled();
  });

  it("removes every run when the operator asks for all of them", async () => {
    const user = userEvent.setup();
    render(<PlatformTestingPage />);

    await user.click(screen.getByRole("button", { name: /Удалить все прогоны/ }));

    // No competition id → all runs, which is what the button says.
    expect(cleanup).toHaveBeenCalledWith(undefined, expect.anything());
  });

  it("removes one run from its own card", async () => {
    const user = userEvent.setup();
    render(<PlatformTestingPage />);

    await user.click(screen.getByRole("button", { name: /Удалить прогон/ }));

    expect(cleanup).toHaveBeenCalledWith("c1", expect.anything());
  });

  it("surfaces a failed job's error rather than reporting a clean run", () => {
    overview.data = overviewWith([
      {
        ...COMPLETED_RUN,
        status: "FAILED",
        rendered: 12,
        msPerDiploma: null,
        jobs: [
          {
            jobId: "j1",
            status: "FAILED",
            created: 12,
            skipped: 0,
            zipUrl: null,
            error: "A selected template has no PDF to print over.",
          },
        ],
      },
    ]);
    render(<PlatformTestingPage />);

    expect(screen.getByText("Ошибка")).toBeInTheDocument();
    expect(screen.getByText(/no PDF to print over/)).toBeInTheDocument();
  });

  it("invites a first run when there is nothing to show", () => {
    overview.data = overviewWith([]);
    render(<PlatformTestingPage />);

    expect(screen.getByText("Прогонов пока не было")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /Удалить все прогоны/ })).not.toBeInTheDocument();
  });
});
