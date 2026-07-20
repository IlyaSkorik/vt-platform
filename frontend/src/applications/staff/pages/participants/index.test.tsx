import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router";
import { afterEach, describe, expect, it, vi } from "vitest";
import {
  type RegistryList,
  type RegistryParticipant,
  type RegistryParticipantDetail,
  useStaffParticipant,
  useStaffParticipants,
} from "@/features/staff-participants";
import { useMediaQuery } from "@/shared/hooks";
import { StaffParticipantsPage } from "./index";

vi.mock("@/features/staff-participants", async (importOriginal) => ({
  ...(await importOriginal<typeof import("@/features/staff-participants")>()),
  useStaffParticipants: vi.fn(),
  useStaffParticipant: vi.fn(),
}));

vi.mock("@/shared/hooks", async (importOriginal) => ({
  ...(await importOriginal<typeof import("@/shared/hooks")>()),
  useMediaQuery: vi.fn(() => false),
}));

const mockedList = vi.mocked(useStaffParticipants);
const mockedDetail = vi.mocked(useStaffParticipant);
const mockedMedia = vi.mocked(useMediaQuery);

function aParticipant(overrides: Partial<RegistryParticipant> = {}): RegistryParticipant {
  return {
    key: "r:0190-abc",
    participantType: "solo",
    displayName: "Петров Пётр",
    firstName: "Пётр",
    lastName: "Петров",
    middleName: null,
    fullName: "Петров Пётр",
    birthDate: "2015-05-01",
    age: 11,
    gender: "male",
    memberCount: 1,
    primaryOrganization: { id: "org-1", name: "Школа №1" },
    organizations: [{ id: "org-1", name: "Школа №1" }],
    teachers: [{ name: "Иванова Мария", role: "COACH" }],
    competitionsCount: 1,
    applicationsCount: 2,
    performancesCount: 2,
    documentsCount: 1,
    lastActivity: "2026-07-12T10:00:00Z",
    ...overrides,
  };
}

function listResult(rows: RegistryParticipant[]): RegistryList {
  return {
    rows,
    total: rows.length,
    facets: {
      total: rows.length,
      solo: rows.length,
      collective: 0,
      withDocuments: rows.length,
      female: 0,
      male: rows.length,
    },
    competitions: [{ id: "comp-1", title: "Весенний конкурс" }],
  };
}

function aDetail(): RegistryParticipantDetail {
  return {
    ...aParticipant(),
    applications: [
      {
        submissionId: "sub-1",
        applicationId: "app-1",
        competitionId: "comp-1",
        competition: "Весенний конкурс",
        status: "ACCEPTED",
        performanceTitle: "Танец с лентами",
        organization: "Школа №1",
        teachers: [{ name: "Иванова Мария", role: "COACH" }],
        submittedAt: "2026-07-10T10:00:00Z",
        updatedAt: "2026-07-12T10:00:00Z",
      },
    ],
    performances: [
      {
        submissionId: "sub-1",
        competitionId: "comp-1",
        competition: "Весенний конкурс",
        status: "ACCEPTED",
        title: "Танец с лентами",
        durationSeconds: 180,
        nomination: "Хореография",
        discipline: "Народный танец",
        ageCategory: "10-12 лет",
        participantGroup: null,
        participationFormat: "Соло",
      },
    ],
    documents: [],
    history: [],
    notes: [],
    awards: [],
  };
}

function stubList(data: RegistryList): void {
  mockedList.mockReturnValue({
    data,
    isLoading: false,
    isError: false,
  } as unknown as ReturnType<typeof useStaffParticipants>);
}

function stubDetail(data: RegistryParticipantDetail | undefined): void {
  mockedDetail.mockReturnValue({
    data,
    isLoading: false,
    isError: false,
  } as unknown as ReturnType<typeof useStaffParticipant>);
}

function renderPage(): void {
  render(
    <MemoryRouter>
      <StaffParticipantsPage />
    </MemoryRouter>,
  );
}

afterEach(() => {
  vi.clearAllMocks();
  mockedMedia.mockReturnValue(false);
});

describe("StaffParticipantsPage", () => {
  it("renders the auto-built registry with a server-provided count", () => {
    stubList(listResult([aParticipant(), aParticipant({ key: "r:2", fullName: "Сидорова Анна" })]));
    stubDetail(undefined);

    renderPage();

    expect(screen.getByText("Участники")).toBeInTheDocument();
    expect(screen.getByText("Найдено участников: 2")).toBeInTheDocument();
    expect(screen.getByText("Петров Пётр")).toBeInTheDocument();
    expect(screen.getByText("Сидорова Анна")).toBeInTheDocument();
  });

  it("never offers to add, create or import a participant (read-only projection)", () => {
    stubList(listResult([aParticipant()]));
    stubDetail(undefined);

    renderPage();

    for (const forbidden of [/добавить/i, /создать/i, /импорт/i, /новый участник/i]) {
      expect(screen.queryByRole("button", { name: forbidden })).toBeNull();
    }
  });

  it("shows an auto-generation empty state when the registry is empty", () => {
    stubList(listResult([]));
    stubDetail(undefined);

    renderPage();

    expect(screen.getByText("Пока нет участников")).toBeInTheDocument();
  });

  it("shows the summary metrics and a one-click link to the application in the card", () => {
    // Desktop: the first participant is auto-selected and the detail renders inline.
    mockedMedia.mockReturnValue(true);
    stubList(listResult([aParticipant()]));
    stubDetail(aDetail());

    renderPage();

    // Summary metric strip.
    expect(screen.getByText("Конкурсов")).toBeInTheDocument();
    expect(screen.getByText("Выступлений")).toBeInTheDocument();
    expect(screen.getByText("Наград")).toBeInTheDocument();
    // Unified participation row with quick navigation.
    expect(screen.getByText("История участия (1)")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Открыть заявку/i })).toBeInTheDocument();
  });
});
