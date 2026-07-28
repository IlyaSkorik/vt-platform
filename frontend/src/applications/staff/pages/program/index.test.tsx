import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { useCompetitionDetail, useCompetitionsList } from "@/features/competitions";
import {
  type Program,
  type ProgramCandidate,
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
const PROGRAM_ID = "01900000-0000-7000-8000-00000000000a";

const reorder = vi.fn();
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
    durationSeconds: 200,
    submissionId: "01900000-0000-7000-8000-0000000000b1",
    leadParticipant: "Иванов Иван",
    participants: ["Иванов Иван"],
    teachers: [],
    nomination: "Вокал",
    discipline: null,
    ageCategory: null,
    participationFormat: null,
    organization: null,
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

describe("StaffProgramPage — the running order", () => {
  it("shows the computed start time of every item", async () => {
    stub();
    await renderPage();

    const items = screen.getAllByTestId("program-item");
    expect(items).toHaveLength(2);
    expect(within(items[0] as HTMLElement).getByText("Катюша")).toBeInTheDocument();
    expect(within(items[1] as HTMLElement).getByText("Калинка")).toBeInTheDocument();
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
  it("publishes the whole programme when no range is given", async () => {
    stub();
    await renderPage();

    await userEvent.type(screen.getByLabelText("Название ссылки"), "Экран у сцены");
    await userEvent.click(screen.getByRole("button", { name: /Создать ссылку/ }));

    expect(createShare).toHaveBeenCalledTimes(1);
    expect(createShare.mock.calls[0]?.[0]).toEqual({ name: "Экран у сцены", itemIds: [] });
  });

  it("resolves a range of positions into the item ids the API takes", async () => {
    stub();
    await renderPage();

    await userEvent.type(screen.getByLabelText("Название ссылки"), "Программа звукорежиссёра");
    await userEvent.type(screen.getByLabelText("Пункты с"), "2");
    await userEvent.type(screen.getByLabelText("Пункты по"), "2");
    await userEvent.click(screen.getByRole("button", { name: /Создать ссылку/ }));

    expect(createShare.mock.calls[0]?.[0]).toEqual({
      name: "Программа звукорежиссёра",
      itemIds: ["item-2"],
    });
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
