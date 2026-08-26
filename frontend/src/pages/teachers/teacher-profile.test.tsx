import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import type { ReactNode } from "react";
import { MemoryRouter } from "react-router";
import { afterEach, describe, expect, it, vi } from "vitest";
import { teachersCreate } from "@/shared/api/generated/teacher-directory/teacher-directory";
import { TEACHER_CONSENT } from "@/shared/consents";
import { TeacherProfilePage } from "./index";

vi.mock("@/shared/api/generated/identity/identity", () => ({
  recordOwnConsent: vi.fn(async () => ({
    status: 201,
    data: { data: [{ id: "01900000-0000-7000-8000-00000000c0de" }] },
  })),
}));

vi.mock("@/shared/api/generated/teacher-directory/teacher-directory", () => ({
  teachersCreate: vi.fn(),
  teachersUpdate: vi.fn(),
}));

const mockedCreate = vi.mocked(teachersCreate);

function wrap(children: ReactNode): React.JSX.Element {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return (
    <QueryClientProvider client={client}>
      <MemoryRouter>{children}</MemoryRouter>
    </QueryClientProvider>
  );
}

/** The four fields a printed document needs, plus the two ways to reach the teacher. */
const REQUIRED_LABELS = ["Фамилия", "Имя", "Отчество", "Роль", "Email", "Телефон"];

afterEach(() => {
  vi.clearAllMocks();
});

describe("TeacherProfilePage", () => {
  it("marks the name, the role and the contacts as required", () => {
    render(wrap(<TeacherProfilePage />));
    for (const label of REQUIRED_LABELS) {
      expect(screen.getByLabelText(label, { exact: false })).toBeRequired();
    }
  });

  it("names the empty required fields instead of saving", async () => {
    const user = userEvent.setup();
    render(wrap(<TeacherProfilePage />));

    await user.type(screen.getByLabelText("Фамилия", { exact: false }), "Петрова");
    await user.click(screen.getByRole("button", { name: "Сохранить" }));

    // Five still empty → five messages, and nothing was sent.
    expect(screen.getAllByText("Обязательное поле")).toHaveLength(5);
    expect(mockedCreate).not.toHaveBeenCalled();
  });

  it("does not scold before a save has been attempted", () => {
    render(wrap(<TeacherProfilePage />));
    expect(screen.queryByText("Обязательное поле")).not.toBeInTheDocument();
  });

  it("saves once the name, the role and the contacts are filled in", async () => {
    mockedCreate.mockResolvedValue({
      status: 201,
      data: { data: { id: "01900000-0000-7000-8000-000000000001" } },
    } as unknown as Awaited<ReturnType<typeof teachersCreate>>);
    const user = userEvent.setup();
    render(wrap(<TeacherProfilePage />));

    await user.type(screen.getByLabelText("Фамилия", { exact: false }), "Петрова");
    await user.type(screen.getByLabelText("Имя", { exact: false }), "Мария");
    await user.type(screen.getByLabelText("Отчество", { exact: false }), "Сергеевна");
    await user.type(screen.getByLabelText("Роль", { exact: false }), "Педагог");
    await user.type(screen.getByLabelText("Email", { exact: false }), "maria@example.com");
    await user.type(screen.getByLabelText("Телефон", { exact: false }), "+7 999 000-00-00");
    // The teacher's own consent — an adult's details entered by somebody else are held
    // on that adult's consent (LEGAL-001 §5.4), so the form will not save without it.
    await user.click(screen.getByRole("checkbox"));
    await user.click(screen.getByRole("button", { name: "Сохранить" }));

    // The consent reference travels with the teacher.
    await waitFor(() =>
      expect(mockedCreate).toHaveBeenCalledWith({
        lastName: "Петрова",
        firstName: "Мария",
        middleName: "Сергеевна",
        role: "Педагог",
        email: "maria@example.com",
        phone: "+7 999 000-00-00",
        consentId: "01900000-0000-7000-8000-00000000c0de",
        consentVersion: TEACHER_CONSENT.version,
      }),
    );
  });
  it("refuses to save without the teacher's own consent", async () => {
    const user = userEvent.setup();
    render(wrap(<TeacherProfilePage />));

    await user.type(screen.getByLabelText("Фамилия", { exact: false }), "Петрова");
    await user.type(screen.getByLabelText("Имя", { exact: false }), "Мария");
    await user.type(screen.getByLabelText("Отчество", { exact: false }), "Сергеевна");
    await user.type(screen.getByLabelText("Роль", { exact: false }), "Педагог");
    await user.type(screen.getByLabelText("Email", { exact: false }), "maria@example.com");
    await user.type(screen.getByLabelText("Телефон", { exact: false }), "+7 999 000-00-00");
    await user.click(screen.getByRole("button", { name: "Сохранить" }));

    // Nothing was sent: the platform, not the form's good intentions, is what refuses.
    expect(mockedCreate).not.toHaveBeenCalled();
    expect(
      screen.getByText("Без согласия педагога добавить его в справочник нельзя"),
    ).toBeInTheDocument();
  });
});
