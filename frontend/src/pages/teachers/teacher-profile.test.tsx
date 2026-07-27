import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import type { ReactNode } from "react";
import { MemoryRouter } from "react-router";
import { afterEach, describe, expect, it, vi } from "vitest";
import { teachersCreate } from "@/shared/api/generated/teacher-directory/teacher-directory";
import { TeacherProfilePage } from "./index";

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

/** The four fields a printed document needs, and the two contacts it does not. */
const REQUIRED_LABELS = ["Фамилия", "Имя", "Отчество", "Роль"];
const OPTIONAL_LABELS = ["Email", "Телефон"];

afterEach(() => {
  vi.clearAllMocks();
});

describe("TeacherProfilePage", () => {
  it("marks the name and the role as required", () => {
    render(wrap(<TeacherProfilePage />));
    for (const label of REQUIRED_LABELS) {
      expect(screen.getByLabelText(label, { exact: false })).toBeRequired();
    }
  });

  it("leaves the contacts optional", () => {
    render(wrap(<TeacherProfilePage />));
    for (const label of OPTIONAL_LABELS) {
      expect(screen.getByLabelText(label, { exact: false })).not.toBeRequired();
    }
  });

  it("names the empty required fields instead of saving", async () => {
    const user = userEvent.setup();
    render(wrap(<TeacherProfilePage />));

    await user.type(screen.getByLabelText("Фамилия", { exact: false }), "Петрова");
    await user.click(screen.getByRole("button", { name: "Сохранить" }));

    // Three still empty → three messages, and nothing was sent.
    expect(screen.getAllByText("Обязательное поле")).toHaveLength(3);
    expect(mockedCreate).not.toHaveBeenCalled();
  });

  it("does not scold before a save has been attempted", () => {
    render(wrap(<TeacherProfilePage />));
    expect(screen.queryByText("Обязательное поле")).not.toBeInTheDocument();
  });

  it("saves once the name and the role are filled in, contacts empty", async () => {
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
    await user.click(screen.getByRole("button", { name: "Сохранить" }));

    // Absent contacts travel as null, not as empty strings.
    expect(mockedCreate).toHaveBeenCalledWith({
      lastName: "Петрова",
      firstName: "Мария",
      middleName: "Сергеевна",
      role: "Педагог",
      email: null,
      phone: null,
    });
  });
});
