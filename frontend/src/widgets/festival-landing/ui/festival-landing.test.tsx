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
  // The registration block is a secondary, non-blocking read; the page renders
  // fine without it, so the tests default it to an empty result.
  usePublicRegistration: vi.fn(() => ({ data: undefined })),
}));

// The "Результаты" section is a third, independent read: it appears by itself once a protocol
// is published and renders nothing otherwise. These tests are about the organizer's blocks, so
// it is stubbed as "nothing published" — its own behaviour is covered where it lives.
vi.mock("@/features/public-protocol", async (importOriginal) => ({
  ...(await importOriginal<typeof import("@/features/public-protocol")>()),
  useCompetitionResults: vi.fn(() => ({ data: [] })),
}));

vi.mock("@/app/providers", async (importOriginal) => ({
  ...(await importOriginal<typeof import("@/app/providers")>()),
  useAuth: vi.fn(() => ({ isAuthenticated: true })),
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

  it("renders the cover, the summary card, the blocks and the footer on success", () => {
    mockQuery({ data: makeFestivalDetail() });
    renderLanding("01900000-0000-7000-8000-000000000001");

    expect(screen.getByRole("heading", { level: 1, name: /взлёт талантов/i })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "О фестивале" })).toBeInTheDocument();
    // The place is a row in the summary card now, not a section of its own.
    expect(screen.getByText("Место проведения")).toBeInTheDocument();
    expect(screen.getByText("Дворец культуры")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /google карты/i })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Положение фестиваля" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /скачать положение/i })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Документы" })).toBeInTheDocument();
    expect(screen.getByText("Программа фестиваля")).toBeInTheDocument();
    expect(screen.getByText("Оргкомитет фестиваля")).toBeInTheDocument();
    expect(screen.getByText(/УНП 100200300/)).toBeInTheDocument();

    const apply = screen.getAllByRole("link", { name: /подать заявку/i });
    expect(apply[0]).toHaveAttribute(
      "href",
      "/cabinet/competitions/01900000-0000-7000-8000-000000000001/apply",
    );
  });

  it("names the organizing entity once, in the footer, and by its festival name", () => {
    // The fixture is the interesting case on purpose: the organization's profile says
    // "Дом талантов" and the festival's contacts override it with "Оргкомитет
    // фестиваля". The hero and the summary rail used to print the profile name, so
    // one page showed both — the default up top and the override in the footer.
    mockQuery({ data: makeFestivalDetail() });
    renderLanding();

    expect(screen.queryByText("Дом талантов")).not.toBeInTheDocument();
    expect(screen.getAllByText("Оргкомитет фестиваля")).toHaveLength(1);
  });

  it("titles the card with the festival's own name when the organizer authored none", () => {
    // The overlay hero deliberately drew nothing when the HERO block carried no
    // title, so an untouched hero never looked authored. The card is different:
    // it is the page's heading, it is always visible, and a card with no title
    // is simply broken — so here the festival's own name is the fallback.
    mockQuery({
      data: makeFestivalDetail({
        landing: { blocks: [makeBlock({ id: "hero", type: "HERO", sortOrder: 0 })] },
      }),
    });
    renderLanding();

    const heading = screen.getByRole("heading", { level: 1 });
    expect(heading).not.toHaveClass("sr-only");
    expect(heading).toHaveTextContent("Весенний вокальный фестиваль");
  });

  it("keeps the dates, the place, the price and the CTA in the summary card", () => {
    mockQuery({ data: makeFestivalDetail() });
    renderLanding();

    const card = screen.getByRole("heading", { level: 1 }).closest("div");
    expect(card).not.toBeNull();
    const inCard = within(card as HTMLElement);
    // By each row's label rather than by the formatted value: the month name and
    // the currency come out of Intl and are not this test's subject.
    expect(inCard.getByText("Даты проведения")).toBeInTheDocument();
    expect(inCard.getByText("Место проведения")).toBeInTheDocument();
    expect(inCard.getByText("Форматы участия")).toBeInTheDocument();
    expect(inCard.getByText("Стоимость участия")).toBeInTheDocument();
    // The deadline is not here: the registration block carries the per-nomination
    // windows, which is the more precise answer to "до когда".
    expect(inCard.queryByText(/Заявки до/)).not.toBeInTheDocument();
    expect(screen.getAllByRole("link", { name: /подать заявку/i })[0]).toBeInTheDocument();
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
    expect(screen.getByRole("heading", { name: "Часто задаваемые вопросы" })).toBeInTheDocument();
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
