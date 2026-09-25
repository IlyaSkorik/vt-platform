import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router";
import { describe, expect, it, vi } from "vitest";

import { fetchOrganizations } from "@/entities/participant";
import { apiClient } from "@/shared/api";

import { ParticipantsProfilePage } from "./index";

vi.mock("@/entities/participant", async (importOriginal) => ({
  ...(await importOriginal<typeof import("@/entities/participant")>()),
  fetchOrganizations: vi.fn(async () => []),
  fetchParticipant: vi.fn(),
}));

vi.mock("@/shared/api", async (importOriginal) => ({
  ...(await importOriginal<typeof import("@/shared/api")>()),
  apiClient: { post: vi.fn(), patch: vi.fn() },
}));

function renderCreate(kind: "solo" | "collective") {
  vi.mocked(fetchOrganizations).mockResolvedValue([]);
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  return render(
    <QueryClientProvider client={client}>
      <MemoryRouter initialEntries={[`/cabinet/participants/new?kind=${kind}`]}>
        <ParticipantsProfilePage />
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

describe("ParticipantsProfilePage — creating a participant", () => {
  it("offers the way onward instead of leaving the first step without a button", async () => {
    // The button that creates the participant lives on the second step, and people who
    // filled in the name found nothing under it and stopped there.
    renderCreate("collective");

    expect(screen.getByRole("button", { name: "Далее" })).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Создать участника" })).not.toBeInTheDocument();
  });

  it("says what is missing on the step it is missing from", async () => {
    const user = userEvent.setup();
    renderCreate("collective");

    await user.click(screen.getByRole("button", { name: "Далее" }));

    expect(await screen.findByText("Укажите название коллектива")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Создать участника" })).not.toBeInTheDocument();
  });

  it("carries a named collective to the step that creates it", async () => {
    const user = userEvent.setup();
    renderCreate("collective");

    await user.type(screen.getByLabelText(/Название коллектива/), "Ансамбль «Ручеёк»");
    await user.click(screen.getByRole("button", { name: "Далее" }));

    expect(await screen.findByRole("button", { name: "Создать участника" })).toBeInTheDocument();
  });

  it("asks for a consent, not for a school", async () => {
    // A soloist taught privately and an adult long out of school belong to nobody, and
    // requiring an organization made them invent one. The consent is the only gate.
    const user = userEvent.setup();
    renderCreate("collective");

    await user.type(screen.getByLabelText(/Название коллектива/), "Ансамбль «Ручеёк»");
    await user.click(screen.getByRole("button", { name: "Далее" }));
    await user.click(await screen.findByRole("button", { name: "Создать участника" }));

    expect(
      await screen.findByText("Без согласия на обработку данных участника создать его нельзя"),
    ).toBeInTheDocument();
  });
});

async function reachTheOrganizationStep(user: ReturnType<typeof userEvent.setup>): Promise<void> {
  await user.type(screen.getByLabelText(/Название коллектива/), "Ансамбль «Ручеёк»");
  await user.click(screen.getByRole("button", { name: "Далее" }));
  await screen.findByRole("button", { name: "Создать участника" });
}

function addOrganizationButton(): HTMLElement {
  return screen.getAllByRole("button", { name: /Добавить организацию/ })[0] as HTMLElement;
}

describe("ParticipantsProfilePage — the personal directory on a phone", () => {
  it("says the directory is empty and offers to fill it", async () => {
    // An empty directory is how every account starts, and it used to render as a search
    // box over blank space — nothing to pick, nothing said, no way forward.
    const user = userEvent.setup();
    renderCreate("collective");

    await reachTheOrganizationStep(user);

    expect(await screen.findByText("В справочнике пока нет организаций")).toBeInTheDocument();
    expect(addOrganizationButton()).toBeInTheDocument();
  });

  it("opens straight on the form where the two do not fit side by side", async () => {
    // On a phone the form sat under the whole directory: people opened this to add
    // their school, saw a list, and never scrolled far enough to find the fields.
    const user = userEvent.setup();
    renderCreate("collective");
    await reachTheOrganizationStep(user);

    await user.click(addOrganizationButton());

    expect(await screen.findByText("Новая организация")).toBeInTheDocument();
    expect(screen.getByLabelText(/^Название/)).toBeInTheDocument();
    // And the list it used to open on is a step away, not above the fields.
    expect(screen.queryByPlaceholderText("Поиск в справочнике")).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: /К списку/ })).toBeInTheDocument();
  });

  it("closes itself once the organization is created", async () => {
    // Staying open with the fields cleared read as «ничего не произошло», and the new
    // organization still had to be found and ticked by hand.
    const user = userEvent.setup();
    vi.mocked(apiClient.post).mockResolvedValue({
      json: async () => ({ data: { id: "01900000-0000-7000-8000-0000000000cc" } }),
    } as unknown as Response);
    renderCreate("collective");
    await reachTheOrganizationStep(user);

    await user.click(addOrganizationButton());
    await user.type(await screen.findByLabelText(/^Название/), "ДШИ №1");
    await user.click(screen.getByRole("button", { name: "Создать" }));

    await waitFor(() =>
      expect(screen.queryByText("Личный справочник организаций")).not.toBeInTheDocument(),
    );
  });
});
