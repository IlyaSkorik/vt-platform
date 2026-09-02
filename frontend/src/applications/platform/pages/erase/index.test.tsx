/**
 * The eraser page.
 *
 * The API layer is mocked rather than the network, the same way the other console
 * suites do it: what is worth pinning down here is not the response envelope but
 * the guardrails — that a blank box searches nothing, that the plan is shown before
 * the button exists, and that the button stays dead until the name is retyped.
 */
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import type { PurgePlan, PurgeTarget } from "@/applications/platform/api/platform-api";

// Radix drives the kind picker, and jsdom implements neither of these.
Element.prototype.hasPointerCapture = () => false;
Element.prototype.scrollIntoView = () => {};

const erase = vi.fn();
const searchSpy = vi.fn();
const planSpy = vi.fn();

const results = {
  data: undefined as PurgeTarget[] | undefined,
  isLoading: false,
  isError: false,
};
const plan = {
  data: undefined as PurgePlan | undefined,
  isLoading: false,
  isError: false,
};

vi.mock("@/applications/platform/api/platform-api", () => ({
  PURGE_MIN_QUERY: 2,
  usePurgeSearch: (kind: string, query: string) => {
    searchSpy(kind, query);
    return results;
  },
  usePurgePlan: (kind: string, id: string | null) => {
    planSpy(kind, id);
    return plan;
  },
  usePurge: () => ({ mutate: erase, isPending: false }),
  refusalMessage: async (_error: unknown, fallback: string) => fallback,
}));

const { PlatformErasePage } = await import("./index");

const FESTIVAL: PurgeTarget = {
  kind: "festival",
  id: "0199a000-0000-7000-8000-000000000001",
  label: "Взлёт талантов",
  hint: "Дом культуры · 2026",
};

const PLAN: PurgePlan = {
  target: FESTIVAL,
  rows: [
    { table: "applications_application", label: "Заявки", count: 42 },
    { table: "diplomas_diploma", label: "Дипломы", count: 340 },
  ],
  total: 382,
  files: 355,
  warnings: ["Организация, её сотрудники и шаблоны дипломов остаются."],
};

async function openTheDialog(): Promise<ReturnType<typeof userEvent.setup>> {
  const user = userEvent.setup();
  render(<PlatformErasePage />);
  await user.click(screen.getByRole("button", { name: /Удалить…/ }));
  return user;
}

describe("PlatformErasePage", () => {
  beforeEach(() => {
    erase.mockReset();
    searchSpy.mockReset();
    planSpy.mockReset();
    results.data = [FESTIVAL];
    results.isLoading = false;
    results.isError = false;
    plan.data = PLAN;
    plan.isLoading = false;
    plan.isError = false;
  });

  it("says plainly that this is not the soft delete used everywhere else", () => {
    render(<PlatformErasePage />);

    expect(screen.getByText(/Это не «скрыть», а «удалить»/)).toBeInTheDocument();
  });

  it("starts on the festival target and searches for nothing until asked", () => {
    results.data = undefined;
    render(<PlatformErasePage />);

    expect(searchSpy).toHaveBeenCalledWith("festival", "");
    expect(screen.queryByText("Ничего не найдено")).not.toBeInTheDocument();
  });

  it("passes the typed query and the chosen kind to the search", async () => {
    const user = userEvent.setup();
    render(<PlatformErasePage />);

    await user.type(screen.getByLabelText("Поиск"), "Взлёт");

    expect(searchSpy).toHaveBeenLastCalledWith("festival", "Взлёт");
  });

  it("offers the narrow targets and points the search at the one picked", async () => {
    // The reason they exist: "программу собрали не так" and "шаблон сверстали
    // заново" are asks that must not be answered by erasing the whole festival.
    const user = userEvent.setup();
    render(<PlatformErasePage />);

    await user.click(screen.getByRole("combobox", { name: "Тип объекта" }));
    await user.click(await screen.findByRole("option", { name: "Программа фестиваля" }));

    expect(searchSpy).toHaveBeenLastCalledWith("program", "");
    expect(screen.getByText(/уходит только сама программа/)).toBeInTheDocument();

    await user.click(screen.getByRole("combobox", { name: "Тип объекта" }));
    await user.click(await screen.findByRole("option", { name: "Шаблон диплома" }));

    expect(searchSpy).toHaveBeenLastCalledWith("template", "");
    expect(screen.getByText(/Уже выданные дипломы остаются/)).toBeInTheDocument();
  });

  it("clears the query when the kind changes, so old results cannot be clicked", async () => {
    const user = userEvent.setup();
    render(<PlatformErasePage />);
    await user.type(screen.getByLabelText("Поиск"), "Взлёт");

    await user.click(screen.getByRole("combobox", { name: "Тип объекта" }));
    await user.click(await screen.findByRole("option", { name: "Шаблон диплома" }));

    expect(screen.getByLabelText("Поиск")).toHaveValue("");
    expect(searchSpy).toHaveBeenLastCalledWith("template", "");
  });

  it("lists a candidate with the second line that tells it apart", () => {
    render(<PlatformErasePage />);

    expect(screen.getByText("Взлёт талантов")).toBeInTheDocument();
    expect(screen.getByText("Дом культуры · 2026")).toBeInTheDocument();
    expect(screen.getByText(FESTIVAL.id)).toBeInTheDocument();
  });

  it("shows what would go before it offers the button", async () => {
    await openTheDialog();

    expect(planSpy).toHaveBeenLastCalledWith("festival", FESTIVAL.id);
    expect(screen.getByText("Заявки")).toBeInTheDocument();
    expect(screen.getByText("340")).toBeInTheDocument();
    expect(screen.getByText(/382/)).toBeInTheDocument();
    expect(screen.getByText(/355/)).toBeInTheDocument();
    expect(
      screen.getByText("Организация, её сотрудники и шаблоны дипломов остаются."),
    ).toBeInTheDocument();
  });

  it("keeps the button dead until the name is retyped", async () => {
    const user = await openTheDialog();
    const button = screen.getByRole("button", { name: /Удалить безвозвратно/ });

    expect(button).toBeDisabled();

    await user.type(screen.getByLabelText(/Введите название/), "Не тот фестиваль");
    expect(button).toBeDisabled();

    await user.clear(screen.getByLabelText(/Введите название/));
    await user.type(screen.getByLabelText(/Введите название/), "Взлёт талантов");
    expect(button).toBeEnabled();
  });

  it("forgives case and spacing, because punishing them only teaches copy-paste", async () => {
    const user = await openTheDialog();

    await user.type(screen.getByLabelText(/Введите название/), "  ВЗЛЁТ  ТАЛАНТОВ ");

    expect(screen.getByRole("button", { name: /Удалить безвозвратно/ })).toBeEnabled();
  });

  it("sends the id and the retyped name when the operator commits", async () => {
    const user = await openTheDialog();

    await user.type(screen.getByLabelText(/Введите название/), "Взлёт талантов");
    await user.click(screen.getByRole("button", { name: /Удалить безвозвратно/ }));

    expect(erase).toHaveBeenCalledWith(
      { kind: "festival", id: FESTIVAL.id, confirm: "Взлёт талантов" },
      expect.anything(),
    );
  });

  it("says so when nothing matched rather than leaving an empty page", () => {
    results.data = [];
    const user = userEvent.setup();
    render(<PlatformErasePage />);

    return user.type(screen.getByLabelText("Поиск"), "Взлёт").then(() => {
      expect(screen.getByText("Ничего не найдено")).toBeInTheDocument();
    });
  });
});
