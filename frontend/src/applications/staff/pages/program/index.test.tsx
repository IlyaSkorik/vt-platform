import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { useCompetitionDetail, useCompetitionsList } from "@/features/competitions";
import {
  type Program,
  type ProgramCandidate,
  type ProgramColumn,
  type ProgramItem,
  useAddBlock,
  useAddPerformance,
  useCreateProgram,
  useCreateShare,
  useEditItem,
  useFillProgram,
  useProgram,
  useProgramCandidates,
  usePrograms,
  useRemoveItem,
  useRemoveShare,
  useRenumberItems,
  useReorderItems,
  useUpdateProgram,
} from "@/features/program-builder";

import { StaffProgramPage } from "./index";

vi.mock("@/features/program-builder", async (importOriginal) => ({
  ...(await importOriginal<typeof import("@/features/program-builder")>()),
  usePrograms: vi.fn(),
  useProgram: vi.fn(),
  useProgramCandidates: vi.fn(),
  useCreateProgram: vi.fn(),
  useUpdateProgram: vi.fn(),
  useAddPerformance: vi.fn(),
  useAddBlock: vi.fn(),
  useEditItem: vi.fn(),
  useFillProgram: vi.fn(),
  useRemoveItem: vi.fn(),
  useReorderItems: vi.fn(),
  useRenumberItems: vi.fn(),
  useCreateShare: vi.fn(),
  useRemoveShare: vi.fn(),
}));

vi.mock("@/features/competitions", async (importOriginal) => ({
  ...(await importOriginal<typeof import("@/features/competitions")>()),
  useCompetitionsList: vi.fn(),
  useCompetitionDetail: vi.fn(),
}));

// Radix's Select relies on pointer-capture and scrollIntoView, which jsdom omits.
Element.prototype.hasPointerCapture = () => false;
Element.prototype.scrollIntoView = () => {};

const COMPETITION_ID = "01900000-0000-7000-8000-0000000000ff";

/** The column catalogue the backend sends with every programme. */
const ALL_COLUMNS: ProgramColumn[] = [
  { key: "POSITION", label: "№" },
  { key: "TIME", label: "Время" },
  { key: "PARTICIPANT", label: "Участник" },
  { key: "TITLE", label: "Номер" },
  { key: "DURATION", label: "Длительность" },
  { key: "NOMINATION", label: "Номинация" },
  { key: "DISCIPLINE", label: "Дисциплина" },
  { key: "PARTICIPANT_GROUP", label: "Состав участников" },
  { key: "AGE_CATEGORY", label: "Возрастная категория" },
  { key: "PARTICIPATION_FORMAT", label: "Формат участия" },
  { key: "TEACHERS", label: "Педагог" },
  { key: "ORGANIZATION", label: "Организация" },
  { key: "COMMENT", label: "Комментарий" },
];
const PROGRAM_ID = "01900000-0000-7000-8000-00000000000a";

const reorder = vi.fn();
const renumber = vi.fn();
const addBlock = vi.fn();
const updateProgram = vi.fn();
const createShare = vi.fn();
const addPerformance = vi.fn();
const fillProgram = vi.fn();
const removeItem = vi.fn();
const removeShare = vi.fn();
const editItem = vi.fn();
const createProgram = vi.fn();

function mutation(mutate: ReturnType<typeof vi.fn>) {
  return { mutate, mutateAsync: mutate, isPending: false } as never;
}

function anItem(overrides: Partial<ProgramItem> & { id: string; position: number }): ProgramItem {
  const { position, ...rest } = overrides;
  return {
    kind: "PERFORMANCE",
    title: "Катюша",
    // Unless a test says otherwise, a slot's number matches its row — the state a
    // programme is in until somebody is moved.
    number: position,
    durationSeconds: 200,
    submissionId: "01900000-0000-7000-8000-0000000000b1",
    leadParticipant: "Иванов Иван",
    participants: ["Иванов Иван"],
    teachers: [],
    nomination: "Вокал",
    discipline: "Эстрадный вокал",
    ageCategory: "10-12 лет",
    participantGroup: "Соло",
    participationFormat: "Очно",
    organization: "Школа №1",
    comment: null,
    missingPerformance: false,
    ...rest,
    schedule: {
      position,
      offsetSeconds: (position - 1) * 200,
      slotSeconds: 200,
      startsAt: `2026-08-01T${String(9 + position).padStart(2, "0")}:00:00Z`,
      endsAt: null,
      ...(rest.schedule ?? {}),
    },
  };
}

function aProgram(overrides: Partial<Program> = {}): Program {
  return {
    id: PROGRAM_ID,
    competitionId: COMPETITION_ID,
    nominationId: null,
    name: "Вокал, 1 отделение",
    bufferSeconds: 30,
    startsAt: "2026-08-01T10:00:00Z",
    items: [
      anItem({ id: "item-1", position: 1, title: "Катюша" }),
      anItem({ id: "item-2", position: 2, title: "Калинка" }),
    ],
    shares: [],
    availableColumns: ALL_COLUMNS,
    totalSeconds: 460,
    endsAt: "2026-08-01T10:07:40Z",
    createdAt: "2026-08-01T09:00:00Z",
    updatedAt: "2026-08-01T09:00:00Z",
    version: 3,
    ...overrides,
  };
}

function aCandidate(): ProgramCandidate {
  return {
    submissionId: "01900000-0000-7000-8000-0000000000c1",
    title: "Барыня",
    durationSeconds: 240,
    nomination: "Вокал",
    discipline: null,
    ageCategory: null,
    participantGroup: null,
    participationFormat: null,
    participants: ["Сидоров Сидор"],
    teachers: [],
    organization: null,
    comment: null,
  };
}

function stub(
  program: Program = aProgram(),
  candidates: ProgramCandidate[] = [aCandidate()],
): void {
  vi.mocked(useCompetitionsList).mockReturnValue({
    data: [{ id: COMPETITION_ID, title: "Весенний фестиваль", season: "2025/2026" }],
    isLoading: false,
  } as never);
  vi.mocked(useCompetitionDetail).mockReturnValue({
    data: { categories: [{ id: "cat-1", name: "Вокал", sortOrder: 1 }] },
    isLoading: false,
  } as never);
  vi.mocked(usePrograms).mockReturnValue({
    data: [
      {
        id: program.id,
        competitionId: COMPETITION_ID,
        nominationId: null,
        name: program.name,
        bufferSeconds: program.bufferSeconds,
        startsAt: program.startsAt,
        itemCount: program.items.length,
        performanceCount: program.items.length,
        totalSeconds: program.totalSeconds,
        shareCount: program.shares.length,
        createdAt: program.createdAt,
        updatedAt: program.updatedAt,
      },
    ],
    isLoading: false,
  } as never);
  vi.mocked(useProgram).mockReturnValue({ data: program, isLoading: false } as never);
  vi.mocked(useProgramCandidates).mockReturnValue({ data: candidates, isLoading: false } as never);
  vi.mocked(useCreateProgram).mockReturnValue(mutation(createProgram));
  vi.mocked(useUpdateProgram).mockReturnValue(mutation(updateProgram));
  vi.mocked(useAddPerformance).mockReturnValue(mutation(addPerformance));
  vi.mocked(useAddBlock).mockReturnValue(mutation(addBlock));
  vi.mocked(useEditItem).mockReturnValue(mutation(editItem));
  vi.mocked(useFillProgram).mockReturnValue(mutation(fillProgram));
  vi.mocked(useRemoveItem).mockReturnValue(mutation(removeItem));
  vi.mocked(useReorderItems).mockReturnValue(mutation(reorder));
  vi.mocked(useRenumberItems).mockReturnValue(mutation(renumber));
  vi.mocked(useCreateShare).mockReturnValue(mutation(createShare));
  vi.mocked(useRemoveShare).mockReturnValue(mutation(removeShare));
}

async function renderPage(): Promise<void> {
  render(
    <MemoryRouter>
      <StaffProgramPage />
    </MemoryRouter>,
  );
  // The competition is auto-selected on the first effect; the programme still has to
  // be picked from the list on the left, which is what opens the workspace.
  await userEvent.click(await screen.findByRole("button", { name: /Вокал, 1 отделение/ }));
  await screen.findByText("Программа");
}

beforeEach(() => {
  for (const spy of [
    reorder,
    renumber,
    addBlock,
    updateProgram,
    createShare,
    addPerformance,
    fillProgram,
    removeItem,
    removeShare,
    editItem,
    createProgram,
  ]) {
    spy.mockReset();
  }
});

afterEach(() => {
  vi.clearAllMocks();
});

describe("StaffProgramPage — the programme table", () => {
  it("renders a column header for every column the programme carries", async () => {
    stub();
    await renderPage();

    for (const column of ALL_COLUMNS) {
      expect(screen.getByRole("columnheader", { name: column.label })).toBeInTheDocument();
    }
  });

  it("puts each value in its own column", async () => {
    stub();
    await renderPage();

    const rows = screen.getAllByTestId("program-item");
    const cells = within(rows[0] as HTMLElement).getAllByRole("cell");
    // Aligned with ALL_COLUMNS: №, Время, Участник, Номер, Длительность, …
    expect(cells[0]).toHaveTextContent("1");
    expect(cells[2]).toHaveTextContent("Иванов Иван");
    expect(cells[3]).toHaveTextContent("Катюша");
    expect(cells[4]).toHaveTextContent("3:20");
    expect(cells[5]).toHaveTextContent("Вокал");
    expect(cells[7]).toHaveTextContent("Соло");
    expect(cells[8]).toHaveTextContent("10-12 лет");
    expect(cells[11]).toHaveTextContent("Школа №1");
  });

  it("shows the computed start time of every item", async () => {
    stub();
    await renderPage();

    const items = screen.getAllByTestId("program-item");
    expect(items).toHaveLength(2);
    expect(within(items[0] as HTMLElement).getByText("Катюша")).toBeInTheDocument();
    expect(within(items[1] as HTMLElement).getByText("Калинка")).toBeInTheDocument();
  });

  it("shows each participant's own number, not the row index", async () => {
    // A programme that has been rearranged: rows 1,2,3 carry numbers 2,3,5.
    stub(
      aProgram({
        items: [
          anItem({ id: "item-1", position: 1, number: 2, title: "Катюша" }),
          anItem({ id: "item-2", position: 2, number: 3, title: "Калинка" }),
          anItem({ id: "item-3", position: 3, number: 5, title: "Барыня" }),
        ],
      }),
    );
    await renderPage();

    const numbers = screen
      .getAllByTestId("program-item")
      .map((row) => within(row).getAllByRole("cell")[0]?.textContent);
    expect(numbers).toEqual(["2", "3", "5"]);
  });

  it("explains the gap instead of leaving it looking like a bug", async () => {
    stub(
      aProgram({
        items: [
          anItem({ id: "item-1", position: 1, number: 2 }),
          anItem({ id: "item-2", position: 2, number: 3 }),
        ],
      }),
    );
    await renderPage();

    expect(screen.getByText("номера сохранены за участниками")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Пересчитать номера/ })).toBeInTheDocument();
  });

  it("offers no renumbering while the numbers still match the order", async () => {
    stub();
    await renderPage();

    expect(screen.queryByRole("button", { name: /Пересчитать номера/ })).toBeNull();
    expect(screen.queryByText("номера сохранены за участниками")).toBeNull();
  });

  it("renumbers only when the organizer asks for it", async () => {
    stub(
      aProgram({
        items: [
          anItem({ id: "item-1", position: 1, number: 2 }),
          anItem({ id: "item-2", position: 2, number: 3 }),
        ],
      }),
    );
    await renderPage();

    await userEvent.click(screen.getByRole("button", { name: /Пересчитать номера/ }));
    expect(renumber).toHaveBeenCalledTimes(1);
  });

  it("sends the whole new order when an item is moved down", async () => {
    stub();
    await renderPage();

    await userEvent.click(screen.getByRole("button", { name: "Вниз: Катюша" }));

    expect(reorder).toHaveBeenCalledTimes(1);
    expect(reorder.mock.calls[0]?.[0]).toEqual(["item-2", "item-1"]);
  });

  it("sends the whole new order when an item is moved up", async () => {
    stub();
    await renderPage();

    await userEvent.click(screen.getByRole("button", { name: "Вверх: Калинка" }));

    expect(reorder.mock.calls[0]?.[0]).toEqual(["item-2", "item-1"]);
  });

  it("cannot move the first item up or the last item down", async () => {
    stub();
    await renderPage();

    expect(screen.getByRole("button", { name: "Вверх: Катюша" })).toBeDisabled();
    expect(screen.getByRole("button", { name: "Вниз: Калинка" })).toBeDisabled();
  });

  it("removes an item", async () => {
    stub();
    await renderPage();

    await userEvent.click(screen.getByRole("button", { name: "Удалить: Калинка" }));

    expect(removeItem).toHaveBeenCalledWith("item-2", expect.anything());
  });
});

describe("StaffProgramPage — breaks", () => {
  it("inserts a break with a title and a length in minutes", async () => {
    stub();
    await renderPage();

    const title = screen.getByLabelText("Название перерыва");
    await userEvent.clear(title);
    await userEvent.type(title, "Обед");
    const minutes = screen.getByLabelText("Длительность перерыва, минут");
    await userEvent.clear(minutes);
    await userEvent.type(minutes, "40");
    await userEvent.click(screen.getByRole("button", { name: /Вставить блок/ }));

    expect(addBlock).toHaveBeenCalledTimes(1);
    expect(addBlock.mock.calls[0]?.[0]).toEqual({ title: "Обед", durationSeconds: 2400 });
  });

  it("refuses to insert a block without a title", async () => {
    stub();
    await renderPage();

    await userEvent.clear(screen.getByLabelText("Название перерыва"));

    expect(screen.getByRole("button", { name: /Вставить блок/ })).toBeDisabled();
  });

  it("shows a break as a distinct kind and lets its length be edited", async () => {
    stub(
      aProgram({
        items: [
          anItem({ id: "item-1", position: 1, title: "Катюша" }),
          anItem({
            id: "item-2",
            position: 2,
            kind: "BREAK",
            title: "Перерыв",
            durationSeconds: 900,
            submissionId: null,
            leadParticipant: null,
            participants: [],
            nomination: null,
          }),
        ],
      }),
    );
    await renderPage();

    expect(screen.getByText("Перерыв")).toBeInTheDocument();
    const minutes = screen.getByLabelText("Минуты: Перерыв");
    await userEvent.clear(minutes);
    await userEvent.type(minutes, "20");
    await userEvent.tab();

    await waitFor(() => expect(editItem).toHaveBeenCalled());
    expect(editItem.mock.calls[0]?.[0]).toEqual({ itemId: "item-2", durationSeconds: 1200 });
  });
});

describe("StaffProgramPage — the buffer", () => {
  it("shows the programme's current buffer", async () => {
    stub();
    await renderPage();

    expect(screen.getByText("0:30")).toBeInTheDocument();
  });

  it("sends a new buffer when another preset is chosen", async () => {
    stub();
    await renderPage();

    await userEvent.click(screen.getByRole("combobox", { name: /Буфер между выступлениями/ }));
    await userEvent.click(await screen.findByRole("option", { name: "1:00" }));

    expect(updateProgram).toHaveBeenCalledTimes(1);
    expect(updateProgram.mock.calls[0]?.[0]).toEqual({ bufferSeconds: 60 });
  });

  it("explains that the buffer does not change an act's own duration", async () => {
    stub();
    await renderPage();

    expect(screen.getByText(/не меняет длительность номера/)).toBeInTheDocument();
  });
});

describe("StaffProgramPage — candidates", () => {
  it("shows the composition and the age band on the card, not one click away", async () => {
    stub(aProgram(), [
      {
        ...aCandidate(),
        nomination: "Вокал",
        discipline: "Эстрадный вокал",
        participantGroup: "Ансамбль",
        ageCategory: "13-15 лет",
        participationFormat: "Очно",
        organization: "Школа №2",
      },
    ]);
    await renderPage();

    const card = screen.getByTestId("program-candidate");
    expect(within(card).getByText("Ансамбль")).toBeInTheDocument();
    expect(within(card).getByText("13-15 лет")).toBeInTheDocument();
    expect(within(card).getByText("Вокал")).toBeInTheDocument();
    expect(within(card).getByText("Эстрадный вокал")).toBeInTheDocument();
    expect(within(card).getByText("Очно")).toBeInTheDocument();
    expect(within(card).getByText(/Школа №2/)).toBeInTheDocument();
  });

  it("omits a badge for a fact the act does not carry", async () => {
    stub(aProgram(), [{ ...aCandidate(), participantGroup: null, ageCategory: null }]);
    await renderPage();

    const card = screen.getByTestId("program-candidate");
    expect(within(card).getByText("Вокал")).toBeInTheDocument();
    expect(within(card).queryByText("Ансамбль")).toBeNull();
  });

  it("adds one act to the programme", async () => {
    stub();
    await renderPage();

    await userEvent.click(screen.getByRole("button", { name: "В программу" }));

    expect(addPerformance.mock.calls[0]?.[0]).toEqual({
      submissionId: "01900000-0000-7000-8000-0000000000c1",
    });
  });

  it("fills the whole nomination in one action", async () => {
    stub();
    await renderPage();

    await userEvent.click(screen.getByRole("button", { name: "Добавить все" }));

    expect(fillProgram).toHaveBeenCalledTimes(1);
  });

  it("disables the bulk fill when nothing is left to add", async () => {
    stub(aProgram(), []);
    await renderPage();

    expect(screen.getByRole("button", { name: "Добавить все" })).toBeDisabled();
    expect(screen.getByText("Все допущенные выступления уже в программе.")).toBeInTheDocument();
  });
});

describe("StaffProgramPage — public links", () => {
  it("publishes the default columns and every row when nothing is narrowed", async () => {
    stub();
    await renderPage();

    await userEvent.type(screen.getByLabelText("Название ссылки"), "Экран у сцены");
    await userEvent.click(screen.getByRole("button", { name: /Создать ссылку/ }));

    expect(createShare).toHaveBeenCalledTimes(1);
    expect(createShare.mock.calls[0]?.[0]).toEqual({
      name: "Экран у сцены",
      columns: ["POSITION", "TIME", "PARTICIPANT", "TITLE"],
      itemIds: [],
    });
  });

  it("sends exactly the columns the organizer ticked", async () => {
    stub();
    await renderPage();

    await userEvent.type(screen.getByLabelText("Название ссылки"), "Программа звукорежиссёра");
    // The sound engineer's cut: drop the two default columns they do not need, add the
    // two they do.
    await userEvent.click(screen.getByRole("checkbox", { name: "№" }));
    await userEvent.click(screen.getByRole("checkbox", { name: "Участник" }));
    await userEvent.click(screen.getByRole("checkbox", { name: "Длительность" }));
    await userEvent.click(screen.getByRole("checkbox", { name: "Комментарий" }));
    await userEvent.click(screen.getByRole("button", { name: /Создать ссылку/ }));

    const payload = createShare.mock.calls[0]?.[0] as { columns: string[] };
    expect(payload.columns).toEqual(["TIME", "TITLE", "DURATION", "COMMENT"]);
  });

  it("cannot publish a link with no columns at all", async () => {
    stub();
    await renderPage();

    await userEvent.type(screen.getByLabelText("Название ссылки"), "Пустая");
    for (const label of ["№", "Время", "Участник", "Номер"]) {
      await userEvent.click(screen.getByRole("checkbox", { name: label }));
    }

    expect(screen.getByRole("button", { name: /Создать ссылку/ })).toBeDisabled();
  });

  it("resolves a range of positions into the item ids the API takes", async () => {
    stub();
    await renderPage();

    await userEvent.type(screen.getByLabelText("Название ссылки"), "Программа звукорежиссёра");
    await userEvent.type(screen.getByLabelText("Пункты с"), "2");
    await userEvent.type(screen.getByLabelText("Пункты по"), "2");
    await userEvent.click(screen.getByRole("button", { name: /Создать ссылку/ }));

    const payload = createShare.mock.calls[0]?.[0] as { itemIds: string[] };
    expect(payload.itemIds).toEqual(["item-2"]);
  });

  it("shows which columns a live link publishes", async () => {
    stub(
      aProgram({
        shares: [
          {
            id: "share-1",
            name: "Программа звукорежиссёра",
            slug: "AbX82Kmn",
            path: "/program/AbX82Kmn",
            columns: [
              { key: "TIME", label: "Время" },
              { key: "TITLE", label: "Номер" },
              { key: "COMMENT", label: "Комментарий" },
            ],
            itemCount: 2,
            coversWholeProgram: false,
            createdAt: "2026-08-01T09:00:00Z",
          },
        ],
      }),
    );
    await renderPage();

    expect(screen.getByText("Колонки: Время, Номер, Комментарий")).toBeInTheDocument();
  });

  it("refuses to publish an unnamed edition", async () => {
    stub();
    await renderPage();

    expect(screen.getByRole("button", { name: /Создать ссылку/ })).toBeDisabled();
  });

  it("lists an existing link with its path and revokes it", async () => {
    stub(
      aProgram({
        shares: [
          {
            id: "share-1",
            name: "Программа звукорежиссёра",
            slug: "AbX82Kmn",
            path: "/program/AbX82Kmn",
            columns: [
              { key: "TIME", label: "Время" },
              { key: "TITLE", label: "Номер" },
              { key: "COMMENT", label: "Комментарий" },
            ],
            itemCount: 2,
            coversWholeProgram: false,
            createdAt: "2026-08-01T09:00:00Z",
          },
        ],
      }),
    );
    await renderPage();

    expect(screen.getByText(/\/program\/AbX82Kmn/)).toBeInTheDocument();
    await userEvent.click(
      screen.getByRole("button", { name: "Отозвать: Программа звукорежиссёра" }),
    );
    expect(removeShare).toHaveBeenCalledWith("share-1", expect.anything());
  });

  it("warns before publishing when an act behind a slot was withdrawn", async () => {
    stub(
      aProgram({
        items: [anItem({ id: "item-1", position: 1, title: "Катюша", missingPerformance: true })],
      }),
    );
    await renderPage();

    expect(screen.getByText("Номер снят")).toBeInTheDocument();
    expect(screen.getByText(/больше не участвуют в фестивале/)).toBeInTheDocument();
  });
});
