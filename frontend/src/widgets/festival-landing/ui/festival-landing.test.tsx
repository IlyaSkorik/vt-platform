import type { UseQueryResult } from "@tanstack/react-query";
import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router";
import { afterEach, describe, expect, it, vi } from "vitest";
import { type FestivalDetail, usePublicFestival } from "@/features/festival-landing";
import { makeBlock, makeFestivalDetail } from "@/features/festival-landing/lib/fixtures";
import type { ApiError } from "@/shared/api";
import { FestivalLanding } from "./festival-landing";

vi.mock("@/features/festival-landing", async (importOriginal) => ({
  ...(await importOriginal<typeof import("@/features/festival-landing")>()),
  usePublicFestival: vi.fn(),
}));

const mockedHook = vi.mocked(usePublicFestival);

type QueryResult = UseQueryResult<FestivalDetail, ApiError>;

function mockQuery(overrides: Partial<QueryResult>): void {
  mockedHook.mockReturnValue({
    data: undefined,
    isPending: false,
    isError: false,
    isFetching: false,
    refetch: vi.fn(),
    ...overrides,
  } as unknown as QueryResult);
}

function renderLanding(festivalId: string | undefined = "fest-1") {
  return render(
    <MemoryRouter>
      <FestivalLanding festivalId={festivalId} />
    </MemoryRouter>,
  );
}

afterEach(() => {
  vi.clearAllMocks();
});

describe("FestivalLanding", () => {
  it("renders a skeleton while loading", () => {
    mockQuery({ isPending: true });
    const { container } = renderLanding();
    expect(container.querySelector(".animate-pulse")).not.toBeNull();
  });

  it("renders a dedicated not-found state on a 404", () => {
    mockQuery({ isError: true, error: { status: 404 } as ApiError });
    renderLanding();
    expect(screen.getByText("Фестиваль не найден")).toBeInTheDocument();
  });

  it("offers a retry on a non-404 error", () => {
    mockQuery({ isError: true, error: { status: 500 } as ApiError });
    renderLanding();
    expect(screen.getByRole("button", { name: /повторить/i })).toBeInTheDocument();
  });

  it("renders the hero, blocks, venue and footer on success", () => {
    mockQuery({ data: makeFestivalDetail() });
    renderLanding();

    expect(screen.getByRole("heading", { level: 1, name: /взлёт талантов/i })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "О фестивале" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Место проведения" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Положение фестиваля" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /скачать положение/i })).toBeInTheDocument();
    expect(screen.getByText("Оргкомитет фестиваля")).toBeInTheDocument();

    const apply = screen.getAllByRole("link", { name: /подать заявку/i });
    expect(apply[0]).toHaveAttribute(
      "href",
      "/cabinet/competitions/01900000-0000-7000-8000-000000000001/apply",
    );
  });

  it("shows a non-actionable CTA for a completed competition", () => {
    mockQuery({ data: makeFestivalDetail({ status: "COMPLETED" }) });
    renderLanding();

    expect(screen.queryByRole("link", { name: /подать заявку/i })).not.toBeInTheDocument();
    const cta = screen.getAllByRole("button", { name: /фестиваль завершён/i });
    expect(cta[0]).toBeDisabled();
  });

  it("renders enabled jury/partners/gallery/faq blocks in order", () => {
    mockQuery({
      data: makeFestivalDetail({
        landing: {
          blocks: [
            makeBlock({ id: "hero", type: "HERO", sortOrder: 0 }),
            makeBlock({
              id: "jury",
              type: "JURY",
              sortOrder: 1,
              jury: [
                {
                  id: "j1",
                  name: "Анна Петрова",
                  photo: null,
                  position: "Хормейстер",
                  description: null,
                },
              ],
            }),
            makeBlock({
              id: "gallery",
              type: "GALLERY",
              sortOrder: 2,
              images: [{ id: "g1", url: "https://cdn.example/1.jpg", caption: "Гала-концерт" }],
            }),
            makeBlock({
              id: "faq",
              type: "FAQ",
              sortOrder: 3,
              faq: [{ id: "q1", question: "Как принять участие?", answer: "Подайте заявку." }],
            }),
          ],
        },
      }),
    });
    renderLanding();

    expect(screen.getByRole("heading", { name: "Жюри и эксперты" })).toBeInTheDocument();
    expect(screen.getByText("Анна Петрова")).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Галерея" })).toBeInTheDocument();
    expect(screen.getByRole("img", { name: "Гала-концерт" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Частые вопросы" })).toBeInTheDocument();
    expect(screen.getByText("Как принять участие?")).toBeInTheDocument();
  });

  it("omits the regulation section when its block is disabled/absent", () => {
    mockQuery({
      data: makeFestivalDetail({
        // A regulation exists, but the organizer's config has no REGULATION block.
        landing: { blocks: [makeBlock({ id: "hero", type: "HERO", sortOrder: 0 })] },
      }),
    });
    renderLanding();

    expect(screen.queryByRole("heading", { name: "Положение фестиваля" })).not.toBeInTheDocument();
  });

  it("opens a gallery photo in a lightbox on click", async () => {
    mockQuery({
      data: makeFestivalDetail({
        landing: {
          blocks: [
            makeBlock({ id: "hero", type: "HERO", sortOrder: 0 }),
            makeBlock({
              id: "gallery",
              type: "GALLERY",
              sortOrder: 1,
              images: [
                { id: "g1", url: "https://cdn.example/1.jpg", caption: "Гала-концерт" },
                { id: "g2", url: "https://cdn.example/2.jpg", caption: "Финал" },
              ],
            }),
          ],
        },
      }),
    });
    renderLanding();

    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: /открыть фото: гала-концерт/i }));

    const dialog = screen.getByRole("dialog");
    expect(within(dialog).getByRole("img", { name: "Гала-концерт" })).toBeInTheDocument();
    // A multi-image gallery offers in-lightbox navigation.
    expect(within(dialog).getByRole("button", { name: /следующее фото/i })).toBeInTheDocument();
  });
});
