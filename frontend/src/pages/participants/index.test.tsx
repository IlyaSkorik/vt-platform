import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router";
import { describe, expect, it, vi } from "vitest";

import { fetchOrganizations } from "@/entities/participant";

import { ParticipantsProfilePage } from "./index";

vi.mock("@/entities/participant", async (importOriginal) => ({
  ...(await importOriginal<typeof import("@/entities/participant")>()),
  fetchOrganizations: vi.fn(async () => []),
  fetchParticipant: vi.fn(),
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
