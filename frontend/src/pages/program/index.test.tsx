import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes } from "react-router";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import {
  type PublicProgram,
  type PublicProgramRow,
  useHostReorder,
  usePublicProgram,
  useSetRowBackstage,
  useSetRowNote,
  useSetRowProgress,
} from "@/features/public-program";

import { toast } from "@/shared/ui";

import { PublicProgramPage } from "./index";

// The mover reports an unknown number through the toaster, which is worth asserting.
vi.mock("@/shared/ui", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/shared/ui")>();
  return { ...actual, toast: { ...actual.toast, error: vi.fn(), success: vi.fn() } };
});

vi.mock("@/features/public-program", async (importOriginal) => ({
  ...(await importOriginal<typeof import("@/features/public-program")>()),
  usePublicProgram: vi.fn(),
  useSetRowProgress: vi.fn(),
  useSetRowBackstage: vi.fn(),
  useSetRowNote: vi.fn(),
  useHostReorder: vi.fn(),
}));

const setProgress = vi.fn();
const setBackstage = vi.fn();
const setNote = vi.fn();
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
      { key: "TIME", label: "Время", custom: false, sensitive: false },
      { key: "TITLE", label: "Номер", custom: false, sensitive: false },
      { key: "DURATION", label: "Длительность", custom: false, sensitive: false },
      { key: "COMMENT", label: "Комментарий", custom: false, sensitive: false },
    ],
    rows: [
      {
        kind: "PERFORMANCE",
        cells: ["10:00", "Катюша", "3:20", "Выход с точки 3"],
        progress: "PENDING",
        id: null,
        backstage: null,
        note: null,
      },
      {
        kind: "BREAK",
        cells: ["10:04", "Перерыв", "15:00", ""],
        progress: "PENDING",
        id: null,
        backstage: null,
        note: null,
      },
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
      // The host's edition is the one the two private marks exist on at all.
      backstage: false,
      note: "",
    })),
  };
}

function stub(program: PublicProgram | null, options: { isError?: boolean } = {}): void {
  vi.mocked(usePublicProgram).mockReturnValue({
    data: program ?? undefined,
    isLoading: false,
    isError: options.isError ?? false,
  } as never);
  vi.mocked(useSetRowProgress).mockReturnValue({
    mutate: setProgress,
    mutateAsync: setProgress,
    isPending: false,
  } as never);
  vi.mocked(useSetRowBackstage).mockReturnValue({
    mutate: setBackstage,
    mutateAsync: setBackstage,
    isPending: false,
  } as never);
  vi.mocked(useSetRowNote).mockReturnValue({
    mutate: setNote,
    mutateAsync: setNote,
    isPending: false,
  } as never);
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
  setBackstage.mockReset();
  setNote.mockReset();
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
    const base = anEngineerProgram();
    stub({
      ...base,
      rows: [{ ...base.rows[0], cells: ["10:00", "Катюша", "3:20", ""] } as PublicProgramRow],
    });
    renderPage();

    const cells = within(screen.getAllByRole("row")[1] as HTMLElement).getAllByRole("cell");
    expect(cells[3]).toHaveTextContent("—");
  });

  it("draws a break as one line instead of a row of blank cells", () => {
    // The sound desk's table is cut wide for the acts; «Перерыв» must not sit two screens
    // to the right of the clock because the columns around it have nothing to say.
    stub(anEngineerProgram());
    renderPage();

    const rows = screen.getAllByTestId("program-row");
    const cells = within(rows[1] as HTMLElement).getAllByRole("cell");
    expect(cells).toHaveLength(1);
    expect(cells[0]).toHaveAttribute("colspan", "4");
    expect(cells[0]).toHaveTextContent("10:04");
    expect(cells[0]).toHaveTextContent("Перерыв");
    expect(cells[0]).toHaveTextContent("15:00");
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

  /**
   * The move the arrows cannot make: an act at the bottom of a long programme announced
   * next. The host names where it goes instead of walking it up a row at a time, and the
   * name is the printed number — which on a published programme is not the row's index.
   */
  function aNumberedHostProgram(): PublicProgram {
    const base = aHostProgram();
    return {
      ...base,
      columns: [{ key: "POSITION", label: "№", custom: false, sensitive: false }, ...base.columns],
      rows: [
        {
          kind: "PERFORMANCE",
          cells: ["4", "10:00", "Катюша", "3:20", ""],
          progress: "PENDING",
          id: "item-1",
          backstage: false,
          note: "",
        },
        {
          kind: "PERFORMANCE",
          cells: ["9", "10:04", "Калинка", "3:20", ""],
          progress: "PENDING",
          id: "item-2",
          backstage: false,
          note: "",
        },
        {
          kind: "PERFORMANCE",
          cells: ["7", "10:08", "Барыня", "3:20", ""],
          progress: "PENDING",
          id: "item-3",
          backstage: false,
          note: "",
        },
      ],
    };
  }

  it("throws a row from the end to the top of the running order in one move", async () => {
    stub(aNumberedHostProgram());
    renderPage();

    await userEvent.click(screen.getByRole("button", { name: "Перенести: 7" }));
    await userEvent.click(await screen.findByRole("button", { name: "В начало" }));

    expect(hostReorder.mock.calls[0]?.[0]).toEqual(["item-3", "item-1", "item-2"]);
  });

  it("puts a row next to the printed number rather than the row that many down", async () => {
    stub(aNumberedHostProgram());
    renderPage();

    // №7 is the last row; a row-index reading would have landed this after «Калинка».
    await userEvent.click(screen.getByRole("button", { name: "Перенести: 4" }));
    await userEvent.type(await screen.findByLabelText("Рядом с номером"), "7");
    await userEvent.click(screen.getByRole("button", { name: "После" }));

    expect(hostReorder.mock.calls[0]?.[0]).toEqual(["item-2", "item-3", "item-1"]);
  });

  it("counts rows when the organizer did not publish the «№» column", async () => {
    // Nothing on screen numbers the acts, so the host counts down the page — and that is
    // what the form then means by a number.
    stub(aHostProgram());
    renderPage();

    await userEvent.click(screen.getByRole("button", { name: "Перенести: 10:04" }));
    await userEvent.type(await screen.findByLabelText("Рядом с номером"), "1");
    await userEvent.click(screen.getByRole("button", { name: "Перед" }));

    expect(hostReorder.mock.calls[0]?.[0]).toEqual(["item-2", "item-1"]);
  });

  it("says so instead of rearranging when no such number is in the programme", async () => {
    stub(aNumberedHostProgram());
    renderPage();

    await userEvent.click(screen.getByRole("button", { name: "Перенести: 4" }));
    await userEvent.type(await screen.findByLabelText("Рядом с номером"), "5");
    await userEvent.click(screen.getByRole("button", { name: "После" }));

    expect(hostReorder).not.toHaveBeenCalled();
    expect(toast.error).toHaveBeenCalledWith("В программе нет №5");
    // Still open: a typo made while the hall waits costs a keystroke, not the whole move.
    expect(screen.getByLabelText("Рядом с номером")).toBeInTheDocument();
  });

  it("cannot move the first row up or the last row down", () => {
    stub(aHostProgram());
    renderPage();

    expect(screen.getByRole("button", { name: "Вверх: 10:00" })).toBeDisabled();
    expect(screen.getByRole("button", { name: "Вниз: 10:04" })).toBeDisabled();
  });
});

describe("PublicProgramPage — an act that is not happening", () => {
  it("cancels a number, and says so in words on every screen", async () => {
    stub(aHostProgram());
    renderPage();

    await userEvent.click(screen.getByRole("button", { name: "Отменить номер: 10:04" }));

    expect(setProgress.mock.calls[0]?.[0]).toEqual({ itemId: "item-2", progress: "CANCELLED" });
  });

  it("writes «Номер отменён» rather than leaving it to a strikethrough", () => {
    // Somebody is ill and the hall has to be told. A line through the name reads the
    // same as an act that merely has not happened yet.
    const base = anEngineerProgram();
    stub({
      ...base,
      rows: [{ ...base.rows[0], progress: "CANCELLED" } as PublicProgramRow],
    });
    renderPage();

    const row = screen.getAllByTestId("program-row")[0] as HTMLElement;
    expect(row).toHaveAttribute("data-progress", "CANCELLED");
    expect(within(row).getByText("Номер отменён")).toBeInTheDocument();
  });

  it("puts a cancelled act back when it turns out to be coming after all", async () => {
    const base = aHostProgram();
    stub({
      ...base,
      rows: base.rows.map((row) => ({ ...row, progress: "CANCELLED" }) as PublicProgramRow),
    });
    renderPage();

    await userEvent.click(screen.getByRole("button", { name: "Вернуть в программу: 10:00" }));

    expect(setProgress.mock.calls[0]?.[0]).toEqual({ itemId: "item-1", progress: "PENDING" });
  });
});

describe("PublicProgramPage — what only the host sees", () => {
  it("marks who is standing behind the stage", async () => {
    stub(aHostProgram());
    renderPage();

    await userEvent.click(screen.getByRole("button", { name: "За сценой: 10:00" }));

    expect(setBackstage.mock.calls[0]?.[0]).toEqual({ itemId: "item-1", backstage: true });
  });

  it("shows the mark on the row it belongs to, and takes it back off", async () => {
    const base = aHostProgram();
    stub({
      ...base,
      rows: base.rows.map((row, index) => ({ ...row, backstage: index === 0 })),
    });
    renderPage();

    const rows = screen.getAllByTestId("program-row");
    expect(within(rows[0] as HTMLElement).getByText("За сценой")).toBeInTheDocument();
    expect(within(rows[1] as HTMLElement).queryByText("За сценой")).toBeNull();

    await userEvent.click(screen.getByRole("button", { name: "Снять «за сценой»: 10:00" }));
    expect(setBackstage.mock.calls[0]?.[0]).toEqual({ itemId: "item-1", backstage: false });
  });

  it("offers nothing of the kind on a read-only link", () => {
    stub(anEngineerProgram());
    renderPage();

    expect(screen.queryByRole("button", { name: /За сценой/ })).toBeNull();
    expect(screen.queryByRole("button", { name: /Пометка/ })).toBeNull();
  });

  it("writes a note against one act, and reads it back under the row", async () => {
    stub(aHostProgram());
    renderPage();

    await userEvent.click(screen.getByRole("button", { name: "Пометка: 10:00" }));
    await userEvent.type(await screen.findByLabelText("Пометка для себя"), "Зовут Алиса");
    await userEvent.click(screen.getByRole("button", { name: "Сохранить" }));

    expect(setNote.mock.calls[0]?.[0]).toEqual({ itemId: "item-1", note: "Зовут Алиса" });
  });

  it("draws an existing note on its own line rather than inside a narrow cell", () => {
    const base = aHostProgram();
    stub({
      ...base,
      rows: base.rows.map((row, index) => ({ ...row, note: index === 0 ? "Поёт вторым" : "" })),
    });
    renderPage();

    const notes = screen.getAllByTestId("program-note");
    expect(notes).toHaveLength(1);
    expect(notes[0]).toHaveTextContent("Поёт вторым");
  });

  it("clears a note it already has", async () => {
    const base = aHostProgram();
    stub({ ...base, rows: base.rows.map((row) => ({ ...row, note: "Папа подойдёт" })) });
    renderPage();

    await userEvent.click(screen.getByRole("button", { name: "Изменить пометку: 10:00" }));
    await userEvent.click(await screen.findByRole("button", { name: "Очистить" }));

    expect(setNote.mock.calls[0]?.[0]).toEqual({ itemId: "item-1", note: "" });
  });

  it("keeps a column about somebody off the stage covered until it is asked for", async () => {
    // Backstage is a corridor. The organizer published «Комментарий» to the host because
    // she needs it; the people behind her in the queue are not who it was published to.
    const base = aHostProgram();
    stub({
      ...base,
      columns: base.columns.map((column) =>
        column.key === "COMMENT" ? { ...column, sensitive: true } : column,
      ),
    });
    renderPage();

    expect(screen.queryByText("Выход с точки 3")).toBeNull();

    await userEvent.click(screen.getByRole("button", { name: "Показать «Комментарий»" }));
    expect(screen.getByText("Выход с точки 3")).toBeInTheDocument();
  });

  it("leaves the same column alone on a screen nobody taps", () => {
    // A display beside the stage has no fingers on it: covering a cell there would hide
    // it for the rest of the festival.
    const base = anEngineerProgram();
    stub({
      ...base,
      columns: base.columns.map((column) =>
        column.key === "COMMENT" ? { ...column, sensitive: true } : column,
      ),
    });
    renderPage();

    expect(screen.getByText("Выход с точки 3")).toBeInTheDocument();
  });
});

describe("PublicProgramPage — the columns that do not scroll away", () => {
  it("pins the first column and the controls on the host's edition", () => {
    // A programme cut for backstage is wider than any phone. Scrolled two columns to the
    // right, an unpinned row is one the host can neither name nor act on.
    stub(aHostProgram());
    renderPage();

    const cells = within(screen.getAllByTestId("program-row")[0] as HTMLElement).getAllByRole(
      "cell",
    );
    expect(cells[0]).toHaveClass("sticky");
    expect(cells.at(-1)).toHaveClass("sticky");
  });

  it("leaves a read-only table as it was", () => {
    stub(anEngineerProgram());
    renderPage();

    const cells = within(screen.getAllByTestId("program-row")[0] as HTMLElement).getAllByRole(
      "cell",
    );
    expect(cells[0]).not.toHaveClass("sticky");
  });
});
