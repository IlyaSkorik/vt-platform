import { act, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { useCompetitionDetail, useCompetitionsList } from "@/features/competitions";
import {
  downloadProgramMedia as downloadProgramMediaImpl,
  downloadProgramMusic as downloadProgramMusicImpl,
  downloadProgramPdf as downloadProgramPdfImpl,
  downloadProgramXlsx as downloadProgramXlsxImpl,
  type Program,
  type ProgramCandidate,
  type ProgramColumn,
  type ProgramItem,
  useAddBlock,
  useAddColumn,
  useAddPerformance,
  useAnnounceShare,
  useArrangeProgram,
  useCreateProgram,
  useCreateShare,
  useDeleteProgram,
  useEditItem,
  useFillCells,
  useFillProgram,
  useProgram,
  useProgramCandidates,
  usePrograms,
  useRemoveColumn,
  useRemoveItem,
  useRemoveShare,
  useRenameColumn,
  useRenumberItems,
  useReorderItems,
  useUndoArrange,
  useUpdateProgram,
} from "@/features/program-builder";

import { festivalInputToIso } from "@/shared/lib";
import { toast } from "@/shared/ui";

import { StaffProgramPage } from "./index";

vi.mock("@/features/program-builder", async (importOriginal) => ({
  ...(await importOriginal<typeof import("@/features/program-builder")>()),
  usePrograms: vi.fn(),
  useProgram: vi.fn(),
  useProgramCandidates: vi.fn(),
  useCreateProgram: vi.fn(),
  useUpdateProgram: vi.fn(),
  useAddPerformance: vi.fn(),
  useArrangeProgram: vi.fn(),
  useUndoArrange: vi.fn(),
  useAddBlock: vi.fn(),
  useEditItem: vi.fn(),
  useFillProgram: vi.fn(),
  useRemoveItem: vi.fn(),
  useReorderItems: vi.fn(),
  useRenumberItems: vi.fn(),
  useCreateShare: vi.fn(),
  useDeleteProgram: vi.fn(),
  useAnnounceShare: vi.fn(),
  useRemoveShare: vi.fn(),
  useAddColumn: vi.fn(),
  useRenameColumn: vi.fn(),
  useRemoveColumn: vi.fn(),
  useFillCells: vi.fn(),
  downloadProgramPdf: vi.fn(),
  downloadProgramXlsx: vi.fn(),
  downloadProgramMedia: vi.fn(),
  downloadProgramMusic: vi.fn(),
}));

// The export panel reports failures through the toaster, which is worth asserting.
vi.mock("@/shared/ui", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/shared/ui")>();
  // `loading` returns the id the later success/error toast replaces, so it has to answer
  // something stable rather than undefined.
  return {
    ...actual,
    toast: { ...actual.toast, error: vi.fn(), success: vi.fn(), loading: vi.fn(() => "waiting") },
  };
});

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
  { key: "POSITION", label: "№", custom: false },
  { key: "TIME", label: "Время", custom: false },
  { key: "PARTICIPANT", label: "Участник", custom: false },
  { key: "TITLE", label: "Номер", custom: false },
  { key: "DURATION", label: "Длительность", custom: false },
  { key: "NOMINATION", label: "Жанр", custom: false },
  { key: "DISCIPLINE", label: "Номинация", custom: false },
  { key: "PARTICIPANT_GROUP", label: "Состав участников", custom: false },
  { key: "AGE_CATEGORY", label: "Возрастная категория", custom: false },
  { key: "PARTICIPATION_FORMAT", label: "Формат участия", custom: false },
  { key: "TEACHERS", label: "Педагог", custom: false },
  { key: "ORGANIZATION", label: "Организация", custom: false },
  { key: "COMMENT", label: "Комментарий", custom: false },
];
const PROGRAM_ID = "01900000-0000-7000-8000-00000000000a";

const reorder = vi.fn();
const renumber = vi.fn();
const addBlock = vi.fn();
const updateProgram = vi.fn();
const createShare = vi.fn();
const addPerformance = vi.fn();
const fillProgram = vi.fn();
const arrangeProgram = vi.fn();
const undoArrange = vi.fn();
const removeItem = vi.fn();
const removeShare = vi.fn();
const deleteProgram = vi.fn();
const announceShare = vi.fn();
const editItem = vi.fn();
const createProgram = vi.fn();
const addColumn = vi.fn();
const renameColumn = vi.fn();
const removeColumn = vi.fn();
const fillCells = vi.fn();
const downloadProgramPdf = vi.mocked(downloadProgramPdfImpl);
const downloadProgramXlsx = vi.mocked(downloadProgramXlsxImpl);
const downloadProgramMusic = vi.mocked(downloadProgramMusicImpl);
const downloadProgramMedia = vi.mocked(downloadProgramMediaImpl);

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
    customValues: {},
    progress: "PENDING",
    durationSeconds: 200,
    submissionId: "01900000-0000-7000-8000-0000000000b1",
    participants: ["Иванов Иван"],
    participantCount: 1,
    teachers: [],
    contacts: [],
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
    // Most tests describe a published programme, which is when numbers matter.
    numbersFrozen: true,
    numbersFrozenAt: "2026-08-01T09:00:00Z",
    totalSeconds: 460,
    endsAt: "2026-08-01T10:07:40Z",
    // Built by hand, like every programme that predates the generator.
    arrangement: null,
    // Nothing to undo: no rebuild has happened in these fixtures unless one says so.
    canUndoArrange: false,
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
  vi.mocked(useArrangeProgram).mockReturnValue(mutation(arrangeProgram));
  vi.mocked(useUndoArrange).mockReturnValue(mutation(undoArrange));
  vi.mocked(useRemoveItem).mockReturnValue(mutation(removeItem));
  vi.mocked(useReorderItems).mockReturnValue(mutation(reorder));
  vi.mocked(useRenumberItems).mockReturnValue(mutation(renumber));
  vi.mocked(useCreateShare).mockReturnValue(mutation(createShare));
  vi.mocked(useRemoveShare).mockReturnValue(mutation(removeShare));
  vi.mocked(useDeleteProgram).mockReturnValue(mutation(deleteProgram));
  vi.mocked(useAnnounceShare).mockReturnValue(mutation(announceShare));
  vi.mocked(useAddColumn).mockReturnValue(mutation(addColumn));
  vi.mocked(useRenameColumn).mockReturnValue(mutation(renameColumn));
  vi.mocked(useRemoveColumn).mockReturnValue(mutation(removeColumn));
  vi.mocked(useFillCells).mockReturnValue(mutation(fillCells));
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
    arrangeProgram,
    removeItem,
    removeShare,
    deleteProgram,
    editItem,
    createProgram,
    addColumn,
    renameColumn,
    removeColumn,
    fillCells,
  ]) {
    spy.mockReset();
  }
  downloadProgramPdf.mockReset();
  downloadProgramPdf.mockResolvedValue(undefined);
  vi.mocked(toast.error).mockReset();
  vi.mocked(toast.loading).mockClear();
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

  it("прячет колонку с экрана, не трогая то, что печатается и публикуется", async () => {
    // Thirteen columns at once is a table that only reads sideways; what a PDF prints and
    // what a link publishes are separate decisions, made in their own panels.
    stub();
    await renderPage();

    await userEvent.click(screen.getByRole("button", { name: /Колонки на экране/ }));
    // Scoped to the popover: the PDF panel offers a checkbox of the same name, and that
    // is the point of the test.
    const picker = await screen.findByRole("group", { name: "Колонки на экране" });
    await userEvent.click(within(picker).getByRole("checkbox", { name: "Организация" }));

    expect(screen.queryByRole("columnheader", { name: "Организация" })).not.toBeInTheDocument();
    // The PDF panel still offers it, because it was never asked about.
    const pdf = screen.getByRole("group", { name: "Колонки в выгрузке" });
    expect(within(pdf).getByRole("checkbox", { name: "Организация" })).toBeInTheDocument();
  });

  it("сворачивает список программ, чтобы таблица заняла всю ширину", async () => {
    stub();
    await renderPage();

    await userEvent.click(screen.getByRole("button", { name: "Свернуть список программ" }));

    expect(screen.queryByRole("button", { name: /Новая программа/ })).not.toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: /^Программы$/ }));
    expect(screen.getByRole("button", { name: /Создать программу/ })).toBeInTheDocument();
  });

  it("puts each value in its own column", async () => {
    stub();
    await renderPage();

    const rows = screen.getAllByTestId("program-item");
    // `slice(1)`: the first cell of every row is the drag handle, not a column.
    const cells = within(rows[0] as HTMLElement)
      .getAllByRole("cell")
      .slice(1);
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
      // `[1]`, not `[0]`: the drag handle leads every row.
      .map((row) => within(row).getAllByRole("cell")[1]?.textContent);
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

  it("says numbers are still provisional before the first publication", async () => {
    stub(aProgram({ numbersFrozen: false, numbersFrozenAt: null }));
    await renderPage();

    expect(
      screen.getByText("номера идут по порядку и зафиксируются после первой публикации"),
    ).toBeInTheDocument();
    // Nothing to renumber: they already follow the order and will keep doing so.
    expect(screen.queryByRole("button", { name: /Пересчитать номера/ })).toBeNull();
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

  /**
   * Grouping and the group move — what "возьми весь эстрадный вокал и подними наверх"
   * actually costs. It is one action here and forty arrow clicks without it, and the
   * endpoint takes the whole order, so an off-by-one is a running order nobody asked for.
   */
  describe("группы", () => {
    /**
     * Drag a run over `row` at a given height.
     *
     * A plain `fireEvent.dragOver(el, { clientY })` will not do: jsdom's `DragEvent` drops
     * the pointer coordinates, and which half of the row the pointer is in is the whole
     * of "перед ней" versus "после неё". A `MouseEvent` named `dragover` carries them and
     * React routes it to the same handler.
     */
    function hoverAt(row: HTMLElement, clientY: number): void {
      fireEvent(row, new MouseEvent("dragover", { bubbles: true, cancelable: true, clientY }));
    }

    /** Two disciplines, three acts, in the order эстрада / эстрада / народный. */
    function aGroupedProgram(): Program {
      return aProgram({
        items: [
          anItem({ id: "item-1", position: 1, title: "Катюша", discipline: "Эстрадный вокал" }),
          anItem({ id: "item-2", position: 2, title: "Калинка", discipline: "Эстрадный вокал" }),
          anItem({ id: "item-3", position: 3, title: "Барыня", discipline: "Народный вокал" }),
        ],
      });
    }

    async function groupByDiscipline(): Promise<void> {
      await userEvent.click(screen.getByRole("combobox", { name: "Группировать" }));
      await userEvent.click(await screen.findByRole("option", { name: "Номинация" }));
    }

    it("собирает подряд идущие строки одной номинации в одну группу", async () => {
      stub(aGroupedProgram());
      await renderPage();
      await groupByDiscipline();

      const groups = screen.getAllByTestId("program-group");
      expect(groups).toHaveLength(2);
      expect(groups[0]).toHaveTextContent("Эстрадный вокал");
      expect(groups[0]).toHaveTextContent("2 номера");
      expect(groups[1]).toHaveTextContent("Народный вокал");
    });

    it("переносит всю группу целиком одним действием", async () => {
      stub(aGroupedProgram());
      await renderPage();
      await groupByDiscipline();

      await userEvent.click(screen.getByRole("button", { name: "Группу выше: Народный вокал" }));

      // Both эстрада acts move together, in their own order, and nothing else changes.
      expect(reorder.mock.calls[0]?.[0]).toEqual(["item-3", "item-1", "item-2"]);
    });

    it("перетаскивает всю группу на место, куда её бросили", async () => {
      stub(aGroupedProgram());
      await renderPage();
      await groupByDiscipline();

      const target = screen.getAllByTestId("program-item")[0] as HTMLElement;
      // jsdom measures every element as a zero-sized box at the origin, and the drop
      // side is decided by which half of the row the pointer is in — so the row has to
      // be given a size before "верхняя половина" means anything.
      vi.spyOn(target, "getBoundingClientRect").mockReturnValue({
        top: 100,
        height: 40,
      } as DOMRect);

      fireEvent.dragStart(screen.getByLabelText("Перетащить группу: Народный вокал"));
      // The upper half of the first row: "перед ней".
      hoverAt(target, 105);
      fireEvent.drop(target);

      expect(reorder.mock.calls[0]?.[0]).toEqual(["item-3", "item-1", "item-2"]);
    });

    it("перетаскивает одну строку, когда тянут её саму", async () => {
      stub(aGroupedProgram());
      await renderPage();

      const target = screen.getAllByTestId("program-item")[0] as HTMLElement;
      vi.spyOn(target, "getBoundingClientRect").mockReturnValue({
        top: 100,
        height: 40,
      } as DOMRect);

      fireEvent.dragStart(screen.getByLabelText("Перетащить: Барыня"));
      // The lower half of the first row: "после неё", not "перед ней".
      hoverAt(target, 130);
      fireEvent.drop(target);

      expect(reorder.mock.calls[0]?.[0]).toEqual(["item-1", "item-3", "item-2"]);
    });

    it("возвращает плоский порядок, когда группировку выключают", async () => {
      stub(aGroupedProgram());
      await renderPage();
      await groupByDiscipline();
      expect(screen.getAllByTestId("program-group")).toHaveLength(2);

      await userEvent.click(screen.getByRole("combobox", { name: "Группировать" }));
      await userEvent.click(await screen.findByRole("option", { name: "Без группировки" }));

      expect(screen.queryAllByTestId("program-group")).toHaveLength(0);
      expect(screen.getAllByTestId("program-item")).toHaveLength(3);
    });

    it("не даёт поднять первую группу и опустить последнюю", async () => {
      stub(aGroupedProgram());
      await renderPage();
      await groupByDiscipline();

      expect(screen.getByRole("button", { name: "Группу выше: Эстрадный вокал" })).toBeDisabled();
      expect(screen.getByRole("button", { name: "Группу ниже: Народный вокал" })).toBeDisabled();
    });

    it("оставляет перерыв отдельной строкой, а не частью группы", async () => {
      // Otherwise moving вокал somewhere would take lunch along with it.
      stub(
        aProgram({
          items: [
            anItem({ id: "item-1", position: 1, title: "Катюша", discipline: "Эстрадный вокал" }),
            anItem({
              id: "item-pause",
              position: 2,
              kind: "BREAK",
              title: "Обед",
              submissionId: null,
              discipline: null,
            }),
            anItem({ id: "item-2", position: 3, title: "Калинка", discipline: "Эстрадный вокал" }),
          ],
        }),
      );
      await renderPage();
      await groupByDiscipline();

      const groups = screen.getAllByTestId("program-group");
      expect(groups.map((group) => group.textContent)).toHaveLength(2);
      expect(screen.queryByRole("button", { name: "Группу выше: Обед" })).not.toBeInTheDocument();
    });
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

  /**
   * The programme is rearranged live while the day runs, and the arrows walk a slot one
   * row at a time. These cover the other move: naming where an act should land.
   */
  function aThreeActProgram(): Program {
    return aProgram({
      items: [
        anItem({ id: "item-1", position: 1, title: "Катюша" }),
        anItem({ id: "item-2", position: 2, title: "Калинка" }),
        anItem({ id: "item-3", position: 3, title: "Барыня" }),
      ],
    });
  }

  it("throws an act from the end to the top of the programme in one move", async () => {
    stub(aThreeActProgram());
    await renderPage();

    await userEvent.click(screen.getByRole("button", { name: "Перенести: Барыня" }));
    await userEvent.click(await screen.findByRole("button", { name: "В начало" }));

    expect(reorder.mock.calls[0]?.[0]).toEqual(["item-3", "item-1", "item-2"]);
  });

  it("puts an act straight after the number the host just announced", async () => {
    stub(aThreeActProgram());
    await renderPage();

    await userEvent.click(screen.getByRole("button", { name: "Перенести: Барыня" }));
    await userEvent.type(await screen.findByLabelText("Рядом с номером"), "1");
    await userEvent.click(screen.getByRole("button", { name: "После" }));

    expect(reorder.mock.calls[0]?.[0]).toEqual(["item-1", "item-3", "item-2"]);
  });

  it("puts an act in front of a number when asked for", async () => {
    stub(aThreeActProgram());
    await renderPage();

    await userEvent.click(screen.getByRole("button", { name: "Перенести: Барыня" }));
    await userEvent.type(await screen.findByLabelText("Рядом с номером"), "2");
    await userEvent.click(screen.getByRole("button", { name: "Перед" }));

    expect(reorder.mock.calls[0]?.[0]).toEqual(["item-1", "item-3", "item-2"]);
  });

  it("reads the printed number, not the row, on a published programme", async () => {
    // Numbers stay with their participants after a publication, so row 3 is №7 here. A
    // move onto "№7" must land next to that act rather than next to whatever is third.
    stub(
      aProgram({
        items: [
          anItem({ id: "item-1", position: 1, number: 4, title: "Катюша" }),
          anItem({ id: "item-2", position: 2, number: 9, title: "Калинка" }),
          anItem({ id: "item-3", position: 3, number: 7, title: "Барыня" }),
        ],
      }),
    );
    await renderPage();

    await userEvent.click(screen.getByRole("button", { name: "Перенести: Катюша" }));
    await userEvent.type(await screen.findByLabelText("Рядом с номером"), "7");
    await userEvent.click(screen.getByRole("button", { name: "После" }));

    expect(reorder.mock.calls[0]?.[0]).toEqual(["item-2", "item-3", "item-1"]);
  });

  it("says so instead of moving anything when the programme has no such number", async () => {
    stub(aThreeActProgram());
    await renderPage();

    await userEvent.click(screen.getByRole("button", { name: "Перенести: Барыня" }));
    await userEvent.type(await screen.findByLabelText("Рядом с номером"), "9");
    await userEvent.click(screen.getByRole("button", { name: "После" }));

    expect(reorder).not.toHaveBeenCalled();
    expect(toast.error).toHaveBeenCalledWith("В программе нет №9");
    // Still open, so the typo can be corrected rather than the move redone.
    expect(screen.getByLabelText("Рядом с номером")).toBeInTheDocument();
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

describe("StaffProgramPage — the organizer's own columns", () => {
  const CUSTOM: ProgramColumn = { key: "custom:col-1", label: "Микрофон", custom: true };

  it("adds a column with a name of the organizer's choosing", async () => {
    stub();
    await renderPage();

    await userEvent.type(screen.getByLabelText("Название колонки"), "Микрофон");
    await userEvent.click(screen.getByRole("button", { name: /Колонка/ }));

    expect(addColumn).toHaveBeenCalledWith("Микрофон", expect.anything());
  });

  it("refuses to add a column without a name", async () => {
    stub();
    await renderPage();

    expect(screen.getByRole("button", { name: /Колонка/ })).toBeDisabled();
  });

  it("renders a custom column's header as an editable name with a remove button", async () => {
    stub(aProgram({ availableColumns: [...ALL_COLUMNS, CUSTOM] }));
    await renderPage();

    expect(screen.getByLabelText("Колонка: Микрофон")).toHaveValue("Микрофон");
    expect(screen.getByRole("button", { name: "Удалить колонку: Микрофон" })).toBeInTheDocument();
  });

  it("renames a column on blur, keeping its values", async () => {
    stub(aProgram({ availableColumns: [...ALL_COLUMNS, CUSTOM] }));
    await renderPage();

    const header = screen.getByLabelText("Колонка: Микрофон");
    await userEvent.clear(header);
    await userEvent.type(header, "Микрофон (тип)");
    await userEvent.tab();

    await waitFor(() => expect(renameColumn).toHaveBeenCalled());
    expect(renameColumn.mock.calls[0]?.[0]).toEqual({ columnId: "col-1", title: "Микрофон (тип)" });
  });

  it("removes a column", async () => {
    stub(aProgram({ availableColumns: [...ALL_COLUMNS, CUSTOM] }));
    await renderPage();

    await userEvent.click(screen.getByRole("button", { name: "Удалить колонку: Микрофон" }));
    expect(removeColumn).toHaveBeenCalledWith("col-1", expect.anything());
  });

  it("fills a cell in place and saves it on blur", async () => {
    stub(
      aProgram({
        availableColumns: [...ALL_COLUMNS, CUSTOM],
        items: [anItem({ id: "item-1", position: 1, title: "Катюша" })],
      }),
    );
    await renderPage();

    const cell = screen.getByLabelText("Значение: Катюша");
    await userEvent.type(cell, "на стойке");
    await userEvent.tab();

    await waitFor(() => expect(fillCells).toHaveBeenCalled());
    expect(fillCells.mock.calls[0]?.[0]).toEqual({
      itemId: "item-1",
      values: { "custom:col-1": "на стойке" },
    });
  });

  it("shows a value already filled in", async () => {
    stub(
      aProgram({
        availableColumns: [...ALL_COLUMNS, CUSTOM],
        items: [
          anItem({
            id: "item-1",
            position: 1,
            title: "Катюша",
            customValues: { "custom:col-1": "на стойке" },
          }),
        ],
      }),
    );
    await renderPage();

    expect(screen.getByLabelText("Значение: Катюша")).toHaveValue("на стойке");
  });

  it("offers a custom column when publishing a link", async () => {
    stub(aProgram({ availableColumns: [...ALL_COLUMNS, CUSTOM] }));
    await renderPage();

    await userEvent.type(screen.getByLabelText("Название ссылки"), "Звукорежиссёр");
    const panel = screen.getByRole("group", { name: "Колонки для публикации" });
    await userEvent.click(within(panel).getByRole("checkbox", { name: "Микрофон" }));
    await userEvent.click(screen.getByRole("button", { name: /Создать ссылку/ }));

    const payload = createShare.mock.calls[0]?.[0] as { columns: string[] };
    expect(payload.columns).toContain("custom:col-1");
  });
});

describe("StaffProgramPage — printing the programme", () => {
  it("downloads a PDF of the columns that are ticked", async () => {
    stub();
    await renderPage();

    // Drop one default column and add one that is not.
    const panel = screen.getByRole("group", { name: "Колонки в выгрузке" });
    await userEvent.click(within(panel).getByRole("checkbox", { name: "Организация" }));
    await userEvent.click(within(panel).getByRole("checkbox", { name: "Педагог" }));
    await userEvent.click(screen.getByRole("button", { name: /Скачать PDF/ }));

    await waitFor(() => expect(downloadProgramPdf).toHaveBeenCalled());
    const [programId, columns, fallback] = downloadProgramPdf.mock.calls[0] as [
      string,
      string[],
      string,
    ];
    expect(programId).toBe(PROGRAM_ID);
    expect(columns).toEqual(["POSITION", "TIME", "PARTICIPANT", "TITLE", "DURATION", "TEACHERS"]);
    expect(fallback).toBe("Вокал, 1 отделение");
  });

  it("downloads the same table as Excel, on the same columns", async () => {
    stub();
    await renderPage();

    const panel = screen.getByRole("group", { name: "Колонки в выгрузке" });
    await userEvent.click(within(panel).getByRole("checkbox", { name: "Организация" }));
    await userEvent.click(screen.getByRole("button", { name: /Скачать Excel/ }));

    await waitFor(() => expect(downloadProgramXlsx).toHaveBeenCalled());
    const [programId, columns, fallback] = downloadProgramXlsx.mock.calls[0] as [
      string,
      string[],
      string,
    ];
    expect(programId).toBe(PROGRAM_ID);
    // The PDF's selection, minus the column just unticked — one choice, two exports.
    expect(columns).toEqual(["POSITION", "TIME", "PARTICIPANT", "TITLE", "DURATION"]);
    expect(fallback).toBe("Вокал, 1 отделение");
  });

  it("starts from the columns a printed running order usually wants", async () => {
    stub();
    await renderPage();

    const panel = screen.getByRole("group", { name: "Колонки в выгрузке" });
    for (const label of ["№", "Время", "Участник", "Номер", "Длительность", "Организация"]) {
      expect(within(panel).getByRole("checkbox", { name: label })).toBeChecked();
    }
    expect(within(panel).getByRole("checkbox", { name: "Комментарий" })).not.toBeChecked();
  });

  it("offers a custom column for printing too", async () => {
    stub(
      aProgram({
        availableColumns: [
          ...ALL_COLUMNS,
          { key: "custom:col-1", label: "Микрофон", custom: true },
        ],
      }),
    );
    await renderPage();

    const panel = screen.getByRole("group", { name: "Колонки в выгрузке" });
    expect(within(panel).getByRole("checkbox", { name: "Микрофон" })).toBeInTheDocument();
  });

  /**
   * Which columns *and in what order*: a page printed for the sound desk wants the number
   * and the act first, the one taken to the register wants the organization there. A
   * published link is arranged the same way, by the same strip — see the public links
   * below.
   */
  it("prints the columns in the order the organizer arranged them", async () => {
    stub();
    await renderPage();

    // «Организация» is last by default; two steps left put it in front of «Номер».
    await userEvent.click(screen.getByRole("button", { name: "Левее: Организация" }));
    await userEvent.click(screen.getByRole("button", { name: "Левее: Организация" }));
    await userEvent.click(screen.getByRole("button", { name: /Скачать PDF/ }));

    await waitFor(() => expect(downloadProgramPdf).toHaveBeenCalled());
    expect(downloadProgramPdf.mock.calls[0]?.[1]).toEqual([
      "POSITION",
      "TIME",
      "PARTICIPANT",
      "ORGANIZATION",
      "TITLE",
      "DURATION",
    ]);
  });

  it("moves a column the other way too, and no further than the edge", async () => {
    stub();
    await renderPage();

    const strip = screen.getByRole("group", { name: /Порядок колонок в выгрузке/ });
    expect(within(strip).getByRole("button", { name: "Левее: №" })).toBeDisabled();
    expect(within(strip).getByRole("button", { name: "Правее: Организация" })).toBeDisabled();

    await userEvent.click(within(strip).getByRole("button", { name: "Правее: №" }));
    await userEvent.click(screen.getByRole("button", { name: /Скачать PDF/ }));

    await waitFor(() => expect(downloadProgramPdf).toHaveBeenCalled());
    expect(downloadProgramPdf.mock.calls[0]?.[1]).toEqual([
      "TIME",
      "POSITION",
      "PARTICIPANT",
      "TITLE",
      "DURATION",
      "ORGANIZATION",
    ]);
  });

  it("puts a newly ticked column last, where whoever added it expects it", async () => {
    stub();
    await renderPage();

    const panel = screen.getByRole("group", { name: "Колонки в выгрузке" });
    await userEvent.click(within(panel).getByRole("checkbox", { name: "Комментарий" }));
    await userEvent.click(screen.getByRole("button", { name: /Скачать PDF/ }));

    await waitFor(() => expect(downloadProgramPdf).toHaveBeenCalled());
    expect(downloadProgramPdf.mock.calls[0]?.[1]?.at(-1)).toBe("COMMENT");
  });

  it("offers no arrangement for a single column, which has only one place to be", async () => {
    stub();
    await renderPage();

    const panel = screen.getByRole("group", { name: "Колонки в выгрузке" });
    for (const label of ["№", "Время", "Участник", "Длительность", "Организация"]) {
      await userEvent.click(within(panel).getByRole("checkbox", { name: label }));
    }

    expect(
      screen.queryByRole("group", { name: /Порядок колонок в выгрузке/ }),
    ).not.toBeInTheDocument();
  });

  it("cannot export nothing at all", async () => {
    stub();
    await renderPage();

    const panel = screen.getByRole("group", { name: "Колонки в выгрузке" });
    for (const label of ["№", "Время", "Участник", "Номер", "Длительность", "Организация"]) {
      await userEvent.click(within(panel).getByRole("checkbox", { name: label }));
    }

    expect(screen.getByRole("button", { name: /Скачать PDF/ })).toBeDisabled();
  });

  it("says so when the export fails rather than failing silently", async () => {
    downloadProgramPdf.mockRejectedValueOnce(new Error("nope"));
    stub();
    await renderPage();

    await userEvent.click(screen.getByRole("button", { name: /Скачать PDF/ }));

    await waitFor(() => expect(toast.error).toHaveBeenCalledWith("Не удалось сформировать PDF"));
  });
});

describe("StaffProgramPage — collecting the backing tracks", () => {
  it("downloads the archive for the programme on screen", async () => {
    stub();
    await renderPage();

    await userEvent.click(screen.getByRole("button", { name: /Скачать фонограммы/ }));

    await waitFor(() => expect(downloadProgramMusic).toHaveBeenCalled());
    expect(downloadProgramMusic.mock.calls[0]).toEqual([PROGRAM_ID, "Вокал, 1 отделение"]);
  });

  it("does not depend on the print columns, which are a different decision", async () => {
    stub();
    await renderPage();

    const panel = screen.getByRole("group", { name: "Колонки в выгрузке" });
    for (const label of ["№", "Время", "Участник", "Номер", "Длительность", "Организация"]) {
      await userEvent.click(within(panel).getByRole("checkbox", { name: label }));
    }

    expect(screen.getByRole("button", { name: /Скачать фонограммы/ })).toBeEnabled();
  });

  it("says so when the archive cannot be built", async () => {
    downloadProgramMusic.mockRejectedValueOnce(new Error("nope"));
    stub();
    await renderPage();

    await userEvent.click(screen.getByRole("button", { name: /Скачать фонограммы/ }));

    await waitFor(() =>
      expect(toast.error).toHaveBeenCalledWith("Не удалось собрать архив фонограмм", {
        id: "waiting",
      }),
    );
    // The failure replaces the "собираем" toast rather than stacking under it: a
    // multi-minute wait has to be announced, and then closed out either way.
    expect(toast.loading).toHaveBeenCalled();
  });
});

describe("StaffProgramPage — the host's link and the live day", () => {
  it("publishes a host edition when asked to", async () => {
    stub();
    await renderPage();

    await userEvent.type(screen.getByLabelText("Название ссылки"), "Программа ведущего");
    await userEvent.click(screen.getByRole("checkbox", { name: /Программа ведущего/ }));
    await userEvent.click(screen.getByRole("button", { name: /Создать ссылку/ }));

    const payload = createShare.mock.calls[0]?.[0] as { controlsRunningOrder: boolean };
    expect(payload.controlsRunningOrder).toBe(true);
  });

  it("publishes a read-only edition by default", async () => {
    stub();
    await renderPage();

    await userEvent.type(screen.getByLabelText("Название ссылки"), "Экран");
    await userEvent.click(screen.getByRole("button", { name: /Создать ссылку/ }));

    const payload = createShare.mock.calls[0]?.[0] as { controlsRunningOrder: boolean };
    expect(payload.controlsRunningOrder).toBe(false);
  });

  it("marks a host link as such in the list", async () => {
    stub(
      aProgram({
        shares: [
          {
            id: "share-1",
            name: "Программа ведущего",
            slug: "Host23456",
            path: "/program/Host23456",
            columns: [{ key: "TIME", label: "Время", custom: false }],
            itemCount: 2,
            coversWholeProgram: true,
            controlsRunningOrder: true,
            createdAt: "2026-08-01T09:00:00Z",
          },
        ],
      }),
    );
    await renderPage();

    expect(screen.getByText("Ведущий: управляет программой")).toBeInTheDocument();
  });

  it("shows what the host has announced on the organizer's own table", async () => {
    stub(
      aProgram({
        items: [
          anItem({ id: "item-1", position: 1, title: "Катюша", progress: "PERFORMED" }),
          anItem({ id: "item-2", position: 2, title: "Калинка", progress: "ON_STAGE" }),
        ],
      }),
    );
    await renderPage();

    const rows = screen.getAllByTestId("program-item");
    expect(rows[0]).toHaveAttribute("data-progress", "PERFORMED");
    expect(rows[1]).toHaveAttribute("data-progress", "ON_STAGE");
    expect(within(rows[0] as HTMLElement).getByText("Выступил")).toBeInTheDocument();
    expect(within(rows[1] as HTMLElement).getByText("На сцене")).toBeInTheDocument();
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
            participants: [],
            nomination: null,
          }),
        ],
      }),
    );
    await renderPage();

    // A block's name lives in a field, not in static text: it is the organizer's own
    // words and is rewritten here.
    expect(screen.getByLabelText("Название: Перерыв")).toHaveValue("Перерыв");
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

    // Named in minutes and seconds, not as a stopwatch reading: «1:30» was read as an
    // hour and a half often enough to be worth the extra characters.
    expect(screen.getByText("30 сек")).toBeInTheDocument();
  });

  it("sends a new buffer when another preset is chosen", async () => {
    stub();
    await renderPage();

    await userEvent.click(screen.getByRole("combobox", { name: /Буфер между выступлениями/ }));
    await userEvent.click(await screen.findByRole("option", { name: "1 мин" }));

    expect(updateProgram).toHaveBeenCalledTimes(1);
    expect(updateProgram.mock.calls[0]?.[0]).toEqual({ bufferSeconds: 60 });
  });

  it("explains that the buffer does not change an act's own duration", async () => {
    stub();
    await renderPage();

    expect(screen.getByText(/не меняет длительность номера/)).toBeInTheDocument();
  });

  it("offers the twenty seconds a tight changeover actually takes", async () => {
    stub();
    await renderPage();

    await userEvent.click(screen.getByRole("combobox", { name: /Буфер между выступлениями/ }));
    await userEvent.click(await screen.findByRole("option", { name: "20 сек" }));

    expect(updateProgram.mock.calls[0]?.[0]).toEqual({ bufferSeconds: 20 });
  });
});

/**
 * The start time, which is typed rather than chosen — and therefore passes through
 * states that are not answers.
 *
 * Both of these were reported from real festivals. A field wired straight into the
 * mutation sent one PATCH per keystroke that happened to make a valid time, and the
 * whole programme comes back on every reply — so the buffer set a moment earlier was
 * put back to its old value by a reply to an older write. The fix is upstream of the
 * race: do not write until the organizer has finished saying what they mean.
 */
describe("StaffProgramPage — the start time", () => {
  it("saves once the typing stops, not once per keystroke", async () => {
    vi.useFakeTimers({ shouldAdvanceTime: true });
    try {
      stub();
      await renderPage();

      const time = screen.getByLabelText("Время начала");
      await userEvent.clear(time);
      // «1047» passes through «10:4», which is a perfectly valid 10:04 — the state the
      // old field saved on its way to the time the organizer was actually typing.
      await userEvent.type(time, "1047");
      expect(updateProgram).not.toHaveBeenCalled();

      await act(async () => {
        vi.advanceTimersByTime(1500);
      });
      expect(updateProgram).toHaveBeenCalledTimes(1);
      expect(updateProgram.mock.calls[0]?.[0]).toEqual({
        startsAt: festivalInputToIso("2026-08-01T10:47"),
      });
    } finally {
      vi.useRealTimers();
    }
  });

  it("moves a programme to another day the moment it is picked", async () => {
    stub();
    await renderPage();

    await userEvent.click(screen.getByRole("button", { name: /Начало программы/ }));
    await userEvent.click(within(await screen.findByRole("grid")).getByText("7"));

    // No timers advanced: the hour is unchanged, so the click is the whole answer and
    // there is no second keystroke coming to wait for.
    expect(updateProgram).toHaveBeenCalledTimes(1);
  });

  it("saves a day picked on an untimed programme at once, at midnight", async () => {
    stub(aProgram({ startsAt: null }));
    await renderPage();

    await userEvent.click(screen.getByRole("button", { name: /Начало программы/ }));
    await userEvent.click(within(await screen.findByRole("grid")).getByText("7"));

    // Midnight is not the answer, but it is saved immediately and visibly provisional,
    // and it is one keystroke from right. Holding the day back until an hour arrives
    // reads as «выбрал — пропало» to anybody who reloads to check that it took.
    expect(updateProgram).toHaveBeenCalledTimes(1);
    expect(screen.getByLabelText("Время начала")).toHaveValue("00:00");
  });

  it("waits for the hour rather than saving a day at midnight", async () => {
    vi.useFakeTimers({ shouldAdvanceTime: true });
    try {
      stub();
      await renderPage();

      // Emptying the time to retype it is not «эта программа начинается в полночь», and
      // the old field saved exactly that on the way past.
      await userEvent.clear(screen.getByLabelText("Время начала"));
      await act(async () => {
        vi.advanceTimersByTime(1500);
      });

      expect(updateProgram).not.toHaveBeenCalled();
    } finally {
      vi.useRealTimers();
    }
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
      controlsRunningOrder: false,
    });
  });

  it("sends exactly the columns the organizer ticked", async () => {
    stub();
    await renderPage();

    await userEvent.type(screen.getByLabelText("Название ссылки"), "Программа звукорежиссёра");
    // The sound engineer's cut: drop the two default columns they do not need, add the
    // two they do.
    const panel = screen.getByRole("group", { name: "Колонки для публикации" });
    await userEvent.click(within(panel).getByRole("checkbox", { name: "№" }));
    await userEvent.click(within(panel).getByRole("checkbox", { name: "Участник" }));
    await userEvent.click(within(panel).getByRole("checkbox", { name: "Длительность" }));
    await userEvent.click(within(panel).getByRole("checkbox", { name: "Комментарий" }));
    await userEvent.click(screen.getByRole("button", { name: /Создать ссылку/ }));

    const payload = createShare.mock.calls[0]?.[0] as { columns: string[] };
    expect(payload.columns).toEqual(["TIME", "TITLE", "DURATION", "COMMENT"]);
  });

  it("cannot publish a link with no columns at all", async () => {
    stub();
    await renderPage();

    await userEvent.type(screen.getByLabelText("Название ссылки"), "Пустая");
    const panel = screen.getByRole("group", { name: "Колонки для публикации" });
    for (const label of ["№", "Время", "Участник", "Номер"]) {
      await userEvent.click(within(panel).getByRole("checkbox", { name: label }));
    }

    expect(screen.getByRole("button", { name: /Создать ссылку/ })).toBeDisabled();
  });

  it("publishes the columns in the order the organizer arranged them", async () => {
    // The reader of a public link should not scroll to reach the column their job
    // depends on, so the strip is the order the screen draws.
    stub();
    await renderPage();

    await userEvent.type(screen.getByLabelText("Название ссылки"), "Экран у сцены");
    const strip = screen.getByRole("group", { name: /Порядок колонок по ссылке/ });
    await userEvent.click(within(strip).getByRole("button", { name: "Левее: Участник" }));
    await userEvent.click(screen.getByRole("button", { name: /Создать ссылку/ }));

    const payload = createShare.mock.calls[0]?.[0] as { columns: string[] };
    expect(payload.columns).toEqual(["POSITION", "PARTICIPANT", "TIME", "TITLE"]);
  });

  it("publishes the whole programme, so a link picks up items added later", async () => {
    stub();
    await renderPage();

    await userEvent.type(screen.getByLabelText("Название ссылки"), "Программа звукорежиссёра");
    await userEvent.click(screen.getByRole("button", { name: /Создать ссылку/ }));

    const payload = createShare.mock.calls[0]?.[0] as { itemIds: string[] };
    expect(payload.itemIds).toEqual([]);
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
              { key: "TIME", label: "Время", custom: false },
              { key: "TITLE", label: "Номер", custom: false },
              { key: "COMMENT", label: "Комментарий", custom: false },
            ],
            itemCount: 2,
            coversWholeProgram: false,
            controlsRunningOrder: false,
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
              { key: "TIME", label: "Время", custom: false },
              { key: "TITLE", label: "Номер", custom: false },
              { key: "COMMENT", label: "Комментарий", custom: false },
            ],
            itemCount: 2,
            coversWholeProgram: false,
            controlsRunningOrder: false,
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

  it("announces one chosen link to the people it covers, not the whole programme", async () => {
    stub(
      aProgram({
        shares: [
          {
            id: "share-1",
            name: "Для участников",
            slug: "AbX82Kmn",
            path: "/program/AbX82Kmn",
            columns: [{ key: "TIME", label: "Время", custom: false }],
            itemCount: 2,
            coversWholeProgram: true,
            controlsRunningOrder: false,
            createdAt: "2026-08-01T09:00:00Z",
          },
        ],
      }),
    );
    await renderPage();

    await userEvent.click(
      screen.getByRole("button", { name: "Разослать участникам: Для участников" }),
    );
    await userEvent.type(
      await screen.findByLabelText("Что добавить от себя"),
      "Сбор за час до начала.",
    );
    // Two buttons say «Разослать» by now — the row's and the dialog's. The dialog is
    // the one that sends, and saying so here is the point of the confirmation step.
    const dialog = screen.getByRole("dialog");
    await userEvent.click(within(dialog).getByRole("button", { name: /Разослать/ }));

    expect(announceShare).toHaveBeenCalledTimes(1);
    expect(announceShare.mock.calls[0]?.[0]).toEqual({
      shareId: "share-1",
      note: "Сбор за час до начала.",
    });
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

describe("StaffProgramPage — collecting the video material", () => {
  it("downloads the media archive for the programme on screen", async () => {
    stub();
    await renderPage();

    await userEvent.click(screen.getByRole("button", { name: /Скачать видеоматериалы/ }));

    await waitFor(() => expect(downloadProgramMedia).toHaveBeenCalled());
    expect(downloadProgramMedia.mock.calls[0]).toEqual([PROGRAM_ID, "Вокал, 1 отделение"]);
  });

  it("is a separate archive from the phonograms", async () => {
    // One archive per desk: pressing one must not fetch the other's files, or the screen
    // operator ends up searching a zip full of backing tracks.
    stub();
    await renderPage();

    await userEvent.click(screen.getByRole("button", { name: /Скачать видеоматериалы/ }));

    await waitFor(() => expect(downloadProgramMedia).toHaveBeenCalled());
    expect(downloadProgramMusic).not.toHaveBeenCalled();
  });

  it("says so when the archive cannot be assembled", async () => {
    stub();
    downloadProgramMedia.mockRejectedValueOnce(new Error("boom"));
    await renderPage();

    await userEvent.click(screen.getByRole("button", { name: /Скачать видеоматериалы/ }));

    await waitFor(() =>
      expect(toast.error).toHaveBeenCalledWith("Не удалось собрать архив медиафайлов", {
        id: "waiting",
      }),
    );
  });
});

describe("StaffProgramPage — автосоставление", () => {
  /** A programme that has not been published yet: the only one that may be rebuilt. */
  function draft(overrides: Partial<Program> = {}): Program {
    return aProgram({ numbersFrozen: false, numbersFrozenAt: null, ...overrides });
  }

  /** Any saved rules — what makes «Пересобрать» appear at all. */
  const SAVED_RULES = {
    grouping: ["NOMINATION"],
    orderWithinGroup: "TITLE",
    breakRule: "NONE",
    breakAfterSeconds: 0,
    breakAfterItems: 0,
    breakTitle: null,
    breakDurationSeconds: null,
    repeatGap: 3,
    openingTitle: null,
    openingDurationSeconds: null,
    awardTitle: null,
    awardDurationSeconds: null,
  } satisfies Program["arrangement"];

  it("отправляет правила, выбранные в форме", async () => {
    stub(draft());
    await renderPage();

    await userEvent.click(screen.getByRole("button", { name: /Собрать программу/ }));
    const dialog = await screen.findByRole("dialog");
    await userEvent.click(within(dialog).getByRole("button", { name: "Собрать программу" }));

    expect(arrangeProgram).toHaveBeenCalledTimes(1);
    expect(arrangeProgram.mock.calls[0]?.[0]).toMatchObject({
      grouping: ["NOMINATION", "DISCIPLINE", "AGE_CATEGORY"],
      orderWithinGroup: "AGE_ASC",
      breakRule: "NONE",
    });
  });

  it("называет признаки теми же словами, что и колонки программы", async () => {
    // Платформа переименовала NOMINATION в «Жанр», а DISCIPLINE в «Номинацию»; подписи
    // диалога отстали, и он предлагал собрать «по номинации», а собирал по жанрам.
    stub(draft());
    await renderPage();

    await userEvent.click(screen.getByRole("button", { name: /Собрать программу/ }));
    const dialog = await screen.findByRole("dialog");

    const column = (key: string) => ALL_COLUMNS.find((item) => item.key === key)?.label ?? "";
    for (const key of ["NOMINATION", "DISCIPLINE", "AGE_CATEGORY", "PARTICIPANT_GROUP"]) {
      expect(within(dialog).getByRole("checkbox", { name: column(key) })).toBeInTheDocument();
    }
  });

  it("порядок признаков группировки — это и есть форма дня, и его можно менять", async () => {
    stub(draft());
    await renderPage();

    await userEvent.click(screen.getByRole("button", { name: /Собрать программу/ }));
    const dialog = await screen.findByRole("dialog");
    const rows = within(dialog).getAllByTestId("arrange-axis");
    // Возрастная категория стоит третьей; поднимаем её на вторую строку.
    await userEvent.click(within(rows[2] as HTMLElement).getByRole("button", { name: "Выше" }));
    await userEvent.click(within(dialog).getByRole("button", { name: "Собрать программу" }));

    expect(arrangeProgram.mock.calls[0]?.[0]).toMatchObject({
      grouping: ["NOMINATION", "AGE_CATEGORY", "DISCIPLINE"],
    });
  });

  it("«Пересобрать» повторяет сохранённые правила без формы", async () => {
    // Пересобирают чаще, чем собирают впервые: заявки идут до последнего дня.
    stub(draft({ arrangement: SAVED_RULES }));
    await renderPage();

    await userEvent.click(screen.getByRole("button", { name: "Пересобрать" }));
    const dialog = await screen.findByRole("dialog");
    await userEvent.click(within(dialog).getByRole("button", { name: "Пересобрать" }));

    expect(arrangeProgram).toHaveBeenCalledTimes(1);
    expect(arrangeProgram.mock.calls[0]?.[0]).toBeUndefined();
  });

  it("«Пересобрать» сначала спрашивает и называет, сколько строк на кону", async () => {
    // Кнопка стоит в общем ряду, а заменяет состав целиком: однажды по ней нажали,
    // не собираясь, и потеряли день расстановки.
    stub(draft({ arrangement: SAVED_RULES }));
    await renderPage();

    await userEvent.click(screen.getByRole("button", { name: "Пересобрать" }));

    const dialog = await screen.findByRole("dialog");
    expect(within(dialog).getByText(/Сейчас в программе строк: 2/)).toBeInTheDocument();
    expect(within(dialog).getByText(/заполненные ячейки пропадут/)).toBeInTheDocument();
    expect(arrangeProgram).not.toHaveBeenCalled();
  });

  it("отказ в диалоге не трогает программу", async () => {
    stub(draft({ arrangement: SAVED_RULES }));
    await renderPage();

    await userEvent.click(screen.getByRole("button", { name: "Пересобрать" }));
    const dialog = await screen.findByRole("dialog");
    await userEvent.click(within(dialog).getByRole("button", { name: "Отмена" }));

    expect(arrangeProgram).not.toHaveBeenCalled();
  });

  it("«Отменить пересборку» показывается, пока сервер держит точку возврата", async () => {
    stub(draft({ arrangement: SAVED_RULES, canUndoArrange: true }));
    await renderPage();

    await userEvent.click(screen.getByRole("button", { name: /Отменить пересборку/ }));

    expect(undoArrange).toHaveBeenCalledTimes(1);
  });

  it("без точки возврата отменять нечего, и кнопки нет", async () => {
    // Кнопка живёт по ответу сервера, а не по тому, что помнит эта вкладка: точку
    // возврата мог потратить соседний экран.
    stub(draft({ arrangement: SAVED_RULES, canUndoArrange: false }));
    await renderPage();

    expect(screen.queryByRole("button", { name: /Отменить пересборку/ })).not.toBeInTheDocument();
  });

  it("опубликованную программу пересобрать нельзя", async () => {
    // Номера уже названы участникам, а пересборка выдала бы слоты заново.
    stub(aProgram({ numbersFrozen: true }));
    await renderPage();

    expect(screen.getByRole("button", { name: /Собрать программу/ })).toBeDisabled();
    expect(screen.queryByRole("button", { name: "Пересобрать" })).not.toBeInTheDocument();
  });
});

describe("StaffProgramPage — удаление программы", () => {
  const A_SHARE = {
    id: "share-1",
    name: "Программа звукорежиссёра",
    slug: "Sound2345",
    path: "/program/Sound2345",
    columns: [{ key: "TIME" as const, label: "Время", custom: false }],
    itemCount: 2,
    coversWholeProgram: true,
    controlsRunningOrder: false,
    createdAt: "2026-08-01T09:00:00Z",
  };

  it("публичная ссылка держит программу, и видно почему", async () => {
    // Ссылка — это чья-то открытая вкладка за пультом; удаление закрыло бы её молча.
    stub(aProgram({ shares: [A_SHARE] }));
    await renderPage();

    expect(screen.getByRole("button", { name: /Удалить программу/ })).toBeDisabled();
    expect(screen.getByText(/Сначала отзовите публичные ссылки \(1\)/)).toBeInTheDocument();
  });

  it("без ссылок удаляет — но только после подтверждения", async () => {
    stub(aProgram({ shares: [] }));
    await renderPage();

    await userEvent.click(screen.getByRole("button", { name: /Удалить программу/ }));
    // Первый клик только открывает диалог: удаление необратимо и стоит рядом с
    // обычными настройками, по которым кликают не глядя.
    expect(deleteProgram).not.toHaveBeenCalled();

    const dialog = within(await screen.findByRole("dialog"));
    expect(
      screen.getByRole("heading", { name: /Удалить программу «Вокал, 1 отделение»/ }),
    ).toBeInTheDocument();
    await userEvent.click(dialog.getByRole("button", { name: "Удалить программу" }));

    expect(deleteProgram).toHaveBeenCalledTimes(1);
    expect(deleteProgram.mock.calls[0]?.[0]).toBe(PROGRAM_ID);
  });
});
