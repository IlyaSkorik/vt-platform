/**
 * The start time, end to end through the real data layer.
 *
 * Every other test on this page mocks the `program-builder` hooks, which means the one
 * thing an organizer kept losing — a date that saves, reappears, vanishes and lets
 * itself be set again — has never actually been exercised. The loss lives in the seam
 * those mocks replace: the field's own draft, the mutation, the response, the query
 * cache, and the next render reading back out of it.
 *
 * So this file mocks nothing but the wire. A real QueryClient, the real hooks, and a
 * fake server that behaves like the backend does: it holds one programme, bumps its
 * version on every write, and answers every read with what it currently holds.
 */
import { QueryClientProvider } from "@tanstack/react-query";
import { cleanup, render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { useCompetitionDetail, useCompetitionsList } from "@/features/competitions";
import { apiClient, createQueryClient } from "@/shared/api";

import { StaffProgramPage } from "./index";

vi.mock("@/features/competitions", () => ({
  useCompetitionsList: vi.fn(),
  useCompetitionDetail: vi.fn(),
}));

vi.mock("@/shared/api", async (importOriginal) => ({
  ...(await importOriginal<typeof import("@/shared/api")>()),
  apiClient: vi.fn(),
}));

/** How long the fake server takes to answer. Long enough to overlap with typing. */
const LATENCY_MS = 60;

const COMPETITION_ID = "01900000-0000-7000-8000-000000000001";
const PROGRAM_ID = "01900000-0000-7000-8000-00000000000a";

const ALL_COLUMNS = [
  { key: "POSITION", label: "№", custom: false },
  { key: "TIME", label: "Время", custom: false },
  { key: "PARTICIPANT", label: "Участник", custom: false },
  { key: "TITLE", label: "Номер", custom: false },
];

/** The one programme the fake server holds, in the shape the API returns. */
function aStoredProgram() {
  return {
    id: PROGRAM_ID,
    competitionId: COMPETITION_ID,
    nominationId: null,
    name: "Вокал, 1 отделение",
    bufferSeconds: 30,
    startsAt: null as string | null,
    items: [],
    shares: [],
    availableColumns: ALL_COLUMNS,
    numbersFrozen: false,
    numbersFrozenAt: null,
    totalSeconds: 0,
    endsAt: null,
    arrangement: null,
    createdAt: "2026-08-01T09:00:00Z",
    updatedAt: "2026-08-01T09:00:00Z",
    version: 3,
  };
}

/**
 * A stand-in for the backend: one programme, a version that grows on every write, and
 * a record of what was asked of it.
 */
function fakeServer() {
  const state = { program: aStoredProgram() };
  const writes: { path: string; body: Record<string, unknown> }[] = [];

  // Latency on purpose: the field holds a draft while a write is in flight, and every
  // way this has gone wrong so far has lived inside that window.
  const respond = (data: unknown) => ({
    json: async () => {
      await new Promise((resolve) => setTimeout(resolve, LATENCY_MS));
      return { data, meta: { requestId: "req-1" } };
    },
  });

  const handle = (path: string, options?: { method?: string; json?: Record<string, unknown> }) => {
    const method = (options?.method ?? "get").toLowerCase();
    if (method === "patch" && path === `staff/programs/${PROGRAM_ID}`) {
      const body = options?.json ?? {};
      writes.push({ path, body });
      if ("startsAt" in body) {
        state.program.startsAt = (body.startsAt as string | null) ?? null;
      }
      if ("bufferSeconds" in body) {
        state.program.bufferSeconds = body.bufferSeconds as number;
      }
      state.program.version += 1;
      return respond({ ...state.program });
    }
    if (path === `staff/programs/${PROGRAM_ID}`) {
      return respond({ ...state.program });
    }
    if (path.startsWith(`staff/programs/${PROGRAM_ID}/candidates`)) {
      return respond([]);
    }
    if (path.startsWith("staff/programs?")) {
      return respond([
        {
          id: PROGRAM_ID,
          competitionId: COMPETITION_ID,
          nominationId: null,
          name: state.program.name,
          bufferSeconds: state.program.bufferSeconds,
          startsAt: state.program.startsAt,
          itemCount: 0,
          performanceCount: 0,
          totalSeconds: 0,
          shareCount: 0,
          createdAt: state.program.createdAt,
          updatedAt: state.program.updatedAt,
        },
      ]);
    }
    return respond(null);
  };

  return { state, writes, handle };
}

let server: ReturnType<typeof fakeServer>;

beforeEach(() => {
  server = fakeServer();
  vi.mocked(apiClient).mockImplementation(((path: string, options?: never) =>
    server.handle(path, options)) as never);
  vi.mocked(useCompetitionsList).mockReturnValue({
    data: [{ id: COMPETITION_ID, title: "Весенний фестиваль", season: "2025/2026" }],
    isLoading: false,
  } as never);
  vi.mocked(useCompetitionDetail).mockReturnValue({
    data: { categories: [] },
    isLoading: false,
  } as never);
});

afterEach(() => {
  vi.clearAllMocks();
});

async function openTheProgramme() {
  const queryClient = createQueryClient();
  render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter>
        <StaffProgramPage />
      </MemoryRouter>
    </QueryClientProvider>,
  );
  await userEvent.click(await screen.findByText("Вокал, 1 отделение"));
  await screen.findByLabelText("Время начала");
  return queryClient;
}

/** Pick a day in the calendar, the way an organizer does. */
async function pickTheSeventh() {
  await userEvent.click(screen.getByRole("button", { name: /Начало программы/ }));
  await userEvent.click(within(await screen.findByRole("grid")).getByText("7"));
}

describe("the programme's start time, through the real data layer", () => {
  it("saves a picked day at once, so reloading to check finds it there", async () => {
    await openTheProgramme();

    await pickTheSeventh();

    // Immediately, with no pause to sit through: the organizer who picks a day and
    // reloads a second later to see whether it took must find that it did.
    await waitFor(() => expect(server.writes).toHaveLength(1));
    expect(server.state.program.startsAt).toBe("2026-10-06T21:00:00.000Z");
    expect(screen.getByRole("button", { name: /Начало программы/ })).toHaveTextContent(/2026/);
  });

  it("lets the hour be typed straight over the midnight it was filled with", async () => {
    await openTheProgramme();
    await pickTheSeventh();
    await waitFor(() => expect(screen.getByLabelText("Время начала")).toHaveValue("00:00"));

    // Clicking in selects what is there, so the first digit replaces it. Without that
    // the field is at its maximum length and silently swallows everything typed.
    await userEvent.type(screen.getByLabelText("Время начала"), "1430");

    await waitFor(() => expect(screen.getByLabelText("Время начала")).toHaveValue("14:30"));
    await waitFor(() => expect(server.state.program.startsAt).toBe("2026-10-07T11:30:00.000Z"), {
      timeout: 3000,
    });
  });

  it("is still there when the page is loaded again from scratch", async () => {
    // The whole complaint in one test: pick a day, reload, is it there. "Reload" means
    // what it means — a new QueryClient, nothing carried over, everything re-fetched.
    await openTheProgramme();
    await pickTheSeventh();
    await waitFor(() => expect(server.writes).toHaveLength(1));
    cleanup();

    await openTheProgramme();

    expect(screen.getByRole("button", { name: /Начало программы/ })).toHaveTextContent(
      /07 октября 2026/,
    );
  });

  it("is still there after a reload when the hour was set too", async () => {
    await openTheProgramme();
    await pickTheSeventh();
    await userEvent.type(screen.getByLabelText("Время начала"), "1430");
    await waitFor(() => expect(server.state.program.startsAt).toBe("2026-10-07T11:30:00.000Z"), {
      timeout: 3000,
    });
    cleanup();

    await openTheProgramme();

    expect(screen.getByRole("button", { name: /Начало программы/ })).toHaveTextContent(
      /07 октября 2026/,
    );
    expect(screen.getByLabelText("Время начала")).toHaveValue("14:30");
  });

  it("moves a programme to another day in one click", async () => {
    server.state.program.startsAt = "2026-10-01T11:30:00.000Z";
    await openTheProgramme();

    await pickTheSeventh();

    // The hour is unchanged, so the whole answer arrived with the click — no waiting.
    await waitFor(() => expect(server.writes).toHaveLength(1));
    expect(server.state.program.startsAt).toBe("2026-10-07T11:30:00.000Z");
  });

  it("takes the hour typed straight after the day, and keeps both", async () => {
    await openTheProgramme();

    await pickTheSeventh();
    // Straight on into the time field, without waiting for the day to come back from
    // the server — which is exactly how fast a person does it.
    await userEvent.type(screen.getByLabelText("Время начала"), "1430");

    await waitFor(() => expect(screen.getByLabelText("Время начала")).toHaveValue("14:30"), {
      timeout: 3000,
    });
    // 14:30 on the wall in Minsk is 11:30Z. Anything else means the hour was dropped and
    // the day was left standing at midnight.
    await waitFor(() => expect(server.state.program.startsAt).toBe("2026-10-07T11:30:00.000Z"), {
      timeout: 3000,
    });
  });

  it("does not flicker back to empty while the write is in flight", async () => {
    await openTheProgramme();

    await pickTheSeventh();
    // Watch the field across the whole round trip rather than only after it.
    for (let tick = 0; tick < 12; tick += 1) {
      await new Promise((resolve) => setTimeout(resolve, 20));
      expect(screen.getByRole("button", { name: /Начало программы/ })).toHaveTextContent(/2026/);
    }
  });

  it("survives the next thing the organizer touches", async () => {
    await openTheProgramme();
    await pickTheSeventh();
    await userEvent.type(screen.getByLabelText("Время начала"), "1430");
    await waitFor(() => expect(server.state.program.startsAt).not.toBeNull(), { timeout: 3000 });

    // The buffer is the control right beside it, and the one they change next.
    await userEvent.click(screen.getByRole("combobox", { name: /Буфер между выступлениями/ }));
    await userEvent.click(await screen.findByRole("option", { name: "1 мин" }));

    await waitFor(() => expect(server.state.program.bufferSeconds).toBe(60));
    expect(server.state.program.startsAt).not.toBeNull();
    expect(screen.getByRole("button", { name: /Начало программы/ })).toHaveTextContent(/2026/);
  });
});
