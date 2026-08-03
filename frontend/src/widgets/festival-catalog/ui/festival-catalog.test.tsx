import type { UseQueryResult } from "@tanstack/react-query";
import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router";
import { afterEach, describe, expect, it, vi } from "vitest";
import type { Festival } from "@/features/festival-catalog";
import { usePublicFestivals } from "@/features/festival-catalog";
import { makeFestival } from "@/features/festival-catalog/lib/fixtures";
import type { ApiError } from "@/shared/api";
import { FestivalCatalog } from "./festival-catalog";

vi.mock("@/features/festival-catalog", async (importOriginal) => ({
  ...(await importOriginal<typeof import("@/features/festival-catalog")>()),
  usePublicFestivals: vi.fn(),
}));

// The cards this renders read the session to build their apply link. These tests are
// about the list — search, empty state — so the session is fixed rather than varied here;
// where the link itself points is asserted in festival-card.test.tsx.
vi.mock("@/app/providers", async (importOriginal) => ({
  ...(await importOriginal<typeof import("@/app/providers")>()),
  useAuth: vi.fn(() => ({ isAuthenticated: true })),
}));

const mockedHook = vi.mocked(usePublicFestivals);

type QueryResult = UseQueryResult<Festival[], ApiError>;

function mockQuery(overrides: Partial<QueryResult>): void {
  mockedHook.mockReturnValue({
    data: undefined,
    isPending: false,
    isError: false,
    isRefetching: false,
    refetch: vi.fn(),
    ...overrides,
  } as unknown as QueryResult);
}

function renderCatalog() {
  return render(
    <MemoryRouter>
      <FestivalCatalog />
    </MemoryRouter>,
  );
}

afterEach(() => {
  vi.clearAllMocks();
});

describe("FestivalCatalog", () => {
  it("renders a skeleton grid while loading", () => {
    mockQuery({ isPending: true });
    const { container } = renderCatalog();
    expect(container.querySelector(".animate-pulse")).not.toBeNull();
  });

  it("shows the empty state when nothing is published", () => {
    mockQuery({ data: [], isPending: false });
    renderCatalog();
    expect(screen.getByText("Пока нет фестивалей")).toBeInTheDocument();
  });

  it("shows a retry affordance on error", () => {
    mockQuery({ isError: true });
    renderCatalog();
    expect(screen.getByRole("button", { name: /повторить/i })).toBeInTheDocument();
  });

  it("renders festivals and filters live by search", async () => {
    mockQuery({
      data: [
        makeFestival({ id: "a", title: "Весенний вокал", city: "Минск", categories: ["Вокал"] }),
        makeFestival({
          id: "b",
          title: "Танцевальный кубок",
          city: "Гомель",
          categories: ["Танцы"],
        }),
      ],
    });
    renderCatalog();
    const grid = within(screen.getByRole("region", { name: "Каталог фестивалей" }));

    expect(grid.getByText("Весенний вокал")).toBeInTheDocument();
    expect(grid.getByText("Танцевальный кубок")).toBeInTheDocument();

    await userEvent.type(screen.getByLabelText("Поиск фестивалей"), "гомель");

    expect(grid.queryByText("Весенний вокал")).not.toBeInTheDocument();
    expect(grid.getByText("Танцевальный кубок")).toBeInTheDocument();
  });

  it("shows the no-results state and resets the search", async () => {
    mockQuery({ data: [makeFestival({ title: "Весенний вокал", categories: ["Вокал"] })] });
    renderCatalog();
    const grid = within(screen.getByRole("region", { name: "Каталог фестивалей" }));

    await userEvent.type(screen.getByLabelText("Поиск фестивалей"), "балалайка");
    expect(screen.getByText("Ничего не найдено")).toBeInTheDocument();

    await userEvent.click(screen.getByRole("button", { name: /сбросить фильтры/i }));
    expect(grid.getByText("Весенний вокал")).toBeInTheDocument();
  });
});
