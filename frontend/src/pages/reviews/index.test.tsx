import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes } from "react-router";
import { beforeEach, describe, expect, it, vi } from "vitest";

import {
  type PublicReviewPage as PublicReviewPageData,
  usePublicReviewPage,
  useSubmitReview,
} from "@/features/public-reviews";

import { PublicReviewPage } from "./index";

vi.mock("@/features/public-reviews", async (importOriginal) => ({
  ...(await importOriginal<typeof import("@/features/public-reviews")>()),
  usePublicReviewPage: vi.fn(),
  useSubmitReview: vi.fn(),
}));

vi.mock("@/shared/ui", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/shared/ui")>();
  return { ...actual, toast: { ...actual.toast, error: vi.fn(), success: vi.fn() } };
});

const submit = vi.fn();

function page(overrides: Partial<PublicReviewPageData> = {}): PublicReviewPageData {
  return {
    slug: "AbX82Kqm9p",
    title: "Оставьте отзыв",
    intro: "",
    organizationName: "Центр «Взлёт»",
    accepting: true,
    festivals: [],
    ...overrides,
  };
}

function show(
  data: PublicReviewPageData | undefined,
  state: { isLoading?: boolean; isError?: boolean } = {},
) {
  vi.mocked(usePublicReviewPage).mockReturnValue({
    data,
    isLoading: state.isLoading ?? false,
    isError: state.isError ?? false,
  } as ReturnType<typeof usePublicReviewPage>);

  render(
    <MemoryRouter initialEntries={["/reviews/AbX82Kqm9p"]}>
      <Routes>
        <Route path="/reviews/:slug" element={<PublicReviewPage />} />
      </Routes>
    </MemoryRouter>,
  );
}

beforeEach(() => {
  submit.mockReset();
  vi.mocked(useSubmitReview).mockReturnValue({
    mutate: submit,
    isPending: false,
  } as unknown as ReturnType<typeof useSubmitReview>);
});

describe("the review form", () => {
  it("names whose page this is before anything is typed", () => {
    show(page());

    expect(screen.getByText("Центр «Взлёт»")).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Оставьте отзыв" })).toBeInTheDocument();
  });

  it("sends the words, the accepted consent and nothing else when nothing else was filled", async () => {
    show(page());
    const user = userEvent.setup();

    await user.type(screen.getByLabelText(/Ваш отзыв/), "Было здорово");
    await user.click(screen.getByRole("checkbox"));
    await user.click(screen.getByRole("button", { name: "Отправить отзыв" }));

    expect(submit).toHaveBeenCalledTimes(1);
    const draft = submit.mock.calls[0]?.[0];
    expect(draft).toMatchObject({
      text: "Было здорово",
      authorName: "",
      competitionId: null,
      photos: [],
    });
    // The pair the server records: what was agreed to, and which wording of it.
    expect(draft.consentType).toBeTruthy();
    expect(draft.consentVersion).toBeTruthy();
  });

  it("refuses to send without the consent, and says why", async () => {
    show(page());
    const user = userEvent.setup();

    await user.type(screen.getByLabelText(/Ваш отзыв/), "Было здорово");
    await user.click(screen.getByRole("button", { name: "Отправить отзыв" }));

    expect(submit).not.toHaveBeenCalled();
    expect(screen.getByText("Без согласия отзыв отправить нельзя")).toBeInTheDocument();
  });

  it("does not pre-tick the consent", () => {
    // A consent that starts checked is not freely given, whatever the label says.
    show(page());

    expect(screen.getByRole("checkbox")).not.toBeChecked();
  });

  it("will not send an empty note", async () => {
    show(page());

    expect(screen.getByRole("button", { name: "Отправить отзыв" })).toBeDisabled();
  });

  it("keeps the name optional", async () => {
    show(page());
    const user = userEvent.setup();

    await user.type(screen.getByLabelText(/Ваш отзыв/), "Спасибо");
    await user.type(screen.getByLabelText(/Как вас зовут/), "Мария");
    await user.click(screen.getByRole("checkbox"));
    await user.click(screen.getByRole("button", { name: "Отправить отзыв" }));

    expect(submit.mock.calls[0]?.[0]).toMatchObject({ authorName: "Мария" });
  });

  it("offers the festival picker only when there is something to pick", () => {
    show(page());

    expect(screen.queryByText("О каком фестивале отзыв")).not.toBeInTheDocument();
  });

  it("explains a closed page instead of taking a note", () => {
    // The banner is printed and will outlive the season: the link has to say so.
    show(page({ accepting: false }));

    expect(screen.getByText("Приём отзывов закрыт")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Отправить отзыв" })).not.toBeInTheDocument();
  });

  it("says plainly when the link resolves to nothing", () => {
    show(undefined, { isError: true });

    expect(screen.getByText("Страница не найдена")).toBeInTheDocument();
  });

  it("thanks the person once the note is accepted", async () => {
    show(page());
    const user = userEvent.setup();
    submit.mockImplementation((_draft, options) => options?.onSuccess?.());

    await user.type(screen.getByLabelText(/Ваш отзыв/), "Спасибо");
    await user.click(screen.getByRole("checkbox"));
    await user.click(screen.getByRole("button", { name: "Отправить отзыв" }));

    expect(await screen.findByText("Спасибо!")).toBeInTheDocument();
  });
});
