import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes } from "react-router";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import {
  type PublicProgram,
  useHostReorder,
  usePublicProgram,
  useSetRowProgress,
} from "@/features/public-program";

import { PublicProgramPage } from "./index";

vi.mock("@/features/public-program", async (importOriginal) => ({
  ...(await importOriginal<typeof import("@/features/public-program")>()),
  usePublicProgram: vi.fn(),
  useSetRowProgress: vi.fn(),
  useHostReorder: vi.fn(),
}));

const setProgress = vi.fn();
const hostReorder = vi.fn();

/** The sound engineer's cut: time, act, length, notes — and nothing else. */
function anEngineerProgram(): PublicProgram {
  return {
    name: "Программа звукорежиссёра",
    slug: "AbX82Kmn",
    competitionTitle: "Весенний фестиваль",
    nomination: "Вокал",
    startsAt: "2026-08-01T10:00:00Z",
    totalSeconds: 460,
    controlsRunningOrder: false,
    columns: [
      { key: "TIME", label: "Время", custom: false },
      { key: "TITLE", label: "Номер", custom: false },
      { key: "DURATION", label: "Длительность", custom: false },
      { key: "COMMENT", label: "Комментарий", custom: false },
    ],
    rows: [
      {
        kind: "PERFORMANCE",
        cells: ["10:00", "Катюша", "3:20", "Выход с точки 3"],
        progress: "PENDING",
        id: null,
      },
      { kind: "BREAK", cells: ["10:04", "Перерыв", "15:00", ""], progress: "PENDING", id: null },
    ],
  };
}

/** The host's edition: the same table, plus row handles and the right to drive the day. */
function aHostProgram(): PublicProgram {
  const base = anEngineerProgram();
  return {
    ...base,
    name: "Программа ведущего",
    controlsRunningOrder: true,
    rows: base.rows.map((row, index) => ({
      ...row,
      id: `item-${index + 1}`,
      progress: index === 0 ? "ON_STAGE" : "PENDING",
    })),
  };
}

function stub(program: PublicProgram | null, options: { isError?: boolean } = {}): void {
  vi.mocked(usePublicProgram).mockReturnValue({
    data: program ?? undefined,
    isLoading: false,
    isError: options.isError ?? false,
  } as never);
  const idle = { mutate: setProgress, mutateAsync: setProgress, isPending: false };
  vi.mocked(useSetRowProgress).mockReturnValue(idle as never);
  vi.mocked(useHostReorder).mockReturnValue({
    mutate: hostReorder,
    mutateAsync: hostReorder,
    isPending: false,
  } as never);
}

function renderPage(): void {
  render(
    <MemoryRouter initialEntries={["/program/AbX82Kmn"]}>
      <Routes>
        <Route path="/program/:slug" element={<PublicProgramPage />} />
      </Routes>
    </MemoryRouter>,
  );
}

beforeEach(() => {
  setProgress.mockReset();
  hostReorder.mockReset();
});

afterEach(() => {
  vi.clearAllMocks();
});

describe("PublicProgramPage", () => {
  it("renders exactly the columns the organizer published", () => {
    stub(anEngineerProgram());
    renderPage();

    const headers = screen.getAllByRole("columnheader").map((header) => header.textContent);
    expect(headers).toEqual(["Время", "Номер", "Длительность", "Комментарий"]);
    // Columns the organizer left out are simply not part of the page.
    expect(screen.queryByRole("columnheader", { name: "Участник" })).toBeNull();
  });

  it("lays each row out against those columns", () => {
    stub(anEngineerProgram());
    renderPage();

    const rows = screen.getAllByRole("row").slice(1);
    expect(within(rows[0] as HTMLElement).getByText("10:00")).toBeInTheDocument();
    expect(within(rows[0] as HTMLElement).getByText("Катюша")).toBeInTheDocument();
    expect(within(rows[0] as HTMLElement).getByText("Выход с точки 3")).toBeInTheDocument();
  });

  it("renders a blank cell as a dash rather than an empty gap", () => {
    stub(anEngineerProgram());
    renderPage();

    const rows = screen.getAllByRole("row").slice(1);
    const breakCells = within(rows[1] as HTMLElement).getAllByRole("cell");
    expect(breakCells[3]).toHaveTextContent("—");
  });

  it("names the festival and the nomination above the table", () => {
    stub(anEngineerProgram());
    renderPage();

    expect(screen.getByText("Весенний фестиваль · Вокал")).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Программа звукорежиссёра" })).toBeInTheDocument();
  });

  it("says the link is dead rather than showing an empty table", () => {
    stub(null, { isError: true });
    renderPage();

    expect(screen.getByText("Программа не найдена")).toBeInTheDocument();
    expect(screen.queryByRole("table")).toBeNull();
  });

  it("handles a published programme with no rows yet", () => {
    stub({ ...anEngineerProgram(), rows: [], totalSeconds: 0 });
    renderPage();

    expect(screen.getByText("Программа пуста")).toBeInTheDocument();
  });
});

describe("PublicProgramPage — what every screen shows live", () => {
  it("highlights the act on stage and strikes through the ones behind us", () => {
    const base = anEngineerProgram();
    stub({
      ...base,
      rows: base.rows.map((row, index) => ({
        ...row,
        progress: index === 0 ? "PERFORMED" : "ON_STAGE",
      })),
    });
    renderPage();

    const rows = screen.getAllByTestId("program-row");
    expect(rows[0]).toHaveAttribute("data-progress", "PERFORMED");
    expect(rows[1]).toHaveAttribute("data-progress", "ON_STAGE");
    expect(within(rows[1] as HTMLElement).getByText("Сейчас")).toBeInTheDocument();
  });

  it("offers no controls on a read-only link", () => {
    stub(anEngineerProgram());
    renderPage();

    expect(screen.queryByRole("button", { name: /На сцене/ })).toBeNull();
    expect(screen.queryByText("Управление программой")).toBeNull();
  });
});

describe("PublicProgramPage — the host's edition", () => {
  it("says it may control the day and offers controls per row", () => {
    stub(aHostProgram());
    renderPage();

    expect(screen.getByText("Управление программой")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "На сцене: 10:00" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Выступил: 10:00" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Пропустить: 10:00" })).toBeInTheDocument();
  });

  it("marks an act as on stage", async () => {
    stub(aHostProgram());
    renderPage();

    await userEvent.click(screen.getByRole("button", { name: "На сцене: 10:04" }));

    expect(setProgress).toHaveBeenCalledTimes(1);
    expect(setProgress.mock.calls[0]?.[0]).toEqual({ itemId: "item-2", progress: "ON_STAGE" });
  });

  it("marks an act as performed", async () => {
    stub(aHostProgram());
    renderPage();

    await userEvent.click(screen.getByRole("button", { name: "Выступил: 10:00" }));

    expect(setProgress.mock.calls[0]?.[0]).toEqual({ itemId: "item-1", progress: "PERFORMED" });
  });

  it("skips an act that did not appear", async () => {
    stub(aHostProgram());
    renderPage();

    await userEvent.click(screen.getByRole("button", { name: "Пропустить: 10:04" }));

    expect(setProgress.mock.calls[0]?.[0]).toEqual({ itemId: "item-2", progress: "SKIPPED" });
  });

  it("sends the whole new order when the host moves a row", async () => {
    stub(aHostProgram());
    renderPage();

    await userEvent.click(screen.getByRole("button", { name: "Вниз: 10:00" }));

    expect(hostReorder).toHaveBeenCalledTimes(1);
    expect(hostReorder.mock.calls[0]?.[0]).toEqual(["item-2", "item-1"]);
  });

  it("cannot move the first row up or the last row down", () => {
    stub(aHostProgram());
    renderPage();

    expect(screen.getByRole("button", { name: "Вверх: 10:00" })).toBeDisabled();
    expect(screen.getByRole("button", { name: "Вниз: 10:04" })).toBeDisabled();
  });
});
