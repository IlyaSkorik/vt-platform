import { render, screen, within } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router";
import { afterEach, describe, expect, it, vi } from "vitest";

import { type PublicProgram, usePublicProgram } from "@/features/public-program";

import { PublicProgramPage } from "./index";

vi.mock("@/features/public-program", async (importOriginal) => ({
  ...(await importOriginal<typeof import("@/features/public-program")>()),
  usePublicProgram: vi.fn(),
}));

/** The sound engineer's cut: time, act, length, notes — and nothing else. */
function anEngineerProgram(): PublicProgram {
  return {
    name: "Программа звукорежиссёра",
    slug: "AbX82Kmn",
    competitionTitle: "Весенний фестиваль",
    nomination: "Вокал",
    startsAt: "2026-08-01T10:00:00Z",
    totalSeconds: 460,
    columns: [
      { key: "TIME", label: "Время" },
      { key: "TITLE", label: "Номер" },
      { key: "DURATION", label: "Длительность" },
      { key: "COMMENT", label: "Комментарий" },
    ],
    rows: [
      { kind: "PERFORMANCE", cells: ["10:00", "Катюша", "3:20", "Выход с точки 3"] },
      { kind: "BREAK", cells: ["10:04", "Перерыв", "15:00", ""] },
    ],
  };
}

function stub(program: PublicProgram | null, options: { isError?: boolean } = {}): void {
  vi.mocked(usePublicProgram).mockReturnValue({
    data: program ?? undefined,
    isLoading: false,
    isError: options.isError ?? false,
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
