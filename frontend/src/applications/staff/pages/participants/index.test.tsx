import { render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import {
  type RegistryList,
  type RegistryParticipant,
  useStaffParticipant,
  useStaffParticipants,
} from "@/features/staff-participants";
import { StaffParticipantsPage } from "./index";

vi.mock("@/features/staff-participants", async (importOriginal) => ({
  ...(await importOriginal<typeof import("@/features/staff-participants")>()),
  useStaffParticipants: vi.fn(),
  useStaffParticipant: vi.fn(),
}));

const mockedList = vi.mocked(useStaffParticipants);
const mockedDetail = vi.mocked(useStaffParticipant);

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

function stubList(data: RegistryList): void {
  mockedList.mockReturnValue({
    data,
    isLoading: false,
    isError: false,
  } as unknown as ReturnType<typeof useStaffParticipants>);
}

function stubDetail(): void {
  mockedDetail.mockReturnValue({
    data: undefined,
    isLoading: false,
    isError: false,
  } as unknown as ReturnType<typeof useStaffParticipant>);
}

afterEach(() => {
  vi.clearAllMocks();
});

describe("StaffParticipantsPage", () => {
  it("renders the auto-built registry with a server-provided count", () => {
    stubList(listResult([aParticipant(), aParticipant({ key: "r:2", fullName: "Сидорова Анна" })]));
    stubDetail();

    render(<StaffParticipantsPage />);

    expect(screen.getByText("Участники")).toBeInTheDocument();
    expect(screen.getByText("Найдено участников: 2")).toBeInTheDocument();
    expect(screen.getByText("Петров Пётр")).toBeInTheDocument();
    expect(screen.getByText("Сидорова Анна")).toBeInTheDocument();
  });

  it("never offers to add, create or import a participant (read-only projection)", () => {
    stubList(listResult([aParticipant()]));
    stubDetail();

    render(<StaffParticipantsPage />);

    for (const forbidden of [/добавить/i, /создать/i, /импорт/i, /новый участник/i]) {
      expect(screen.queryByRole("button", { name: forbidden })).toBeNull();
    }
  });

  it("shows an auto-generation empty state when the registry is empty", () => {
    stubList(listResult([]));
    stubDetail();

    render(<StaffParticipantsPage />);

    expect(screen.getByText("Пока нет участников")).toBeInTheDocument();
  });
});
