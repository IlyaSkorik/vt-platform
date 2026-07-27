import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";
import { useCompetitionDetail, useCompetitionsList } from "@/features/competitions";
import {
  type DiplomaAssignment,
  type DiplomaTemplate,
  useCreateAssignmentMutation,
  useDeleteAssignmentMutation,
  useDiplomaAssignments,
  useDiplomaTemplates,
} from "@/features/diplomas";
import { AssignmentsSection } from "./assignments-section";

Element.prototype.hasPointerCapture = () => false;
Element.prototype.scrollIntoView = () => {};

vi.mock("@/features/competitions", async (importOriginal) => ({
  ...(await importOriginal<typeof import("@/features/competitions")>()),
  useCompetitionDetail: vi.fn(),
  useCompetitionsList: vi.fn(),
}));

vi.mock("@/features/diplomas", async (importOriginal) => ({
  ...(await importOriginal<typeof import("@/features/diplomas")>()),
  useCreateAssignmentMutation: vi.fn(),
  useDeleteAssignmentMutation: vi.fn(),
  useDiplomaAssignments: vi.fn(),
  useDiplomaTemplates: vi.fn(),
}));

const COMPETITION_ID = "01900000-0000-7000-8000-0000000000c0";
const VOCALS = "01900000-0000-7000-8000-000000000001";
const DANCE = "01900000-0000-7000-8000-000000000002";
const THEATRE = "01900000-0000-7000-8000-000000000003";
const DIPLOMA_TEMPLATE = "01900000-0000-7000-8000-0000000000d1";

/** «Вокал» already has a diploma template; the other two are free. */
const ASSIGNED_VOCALS: DiplomaAssignment = {
  id: "01900000-0000-7000-8000-0000000000a1",
  competitionId: COMPETITION_ID,
  competition: "Восходящие таланты",
  categoryId: VOCALS,
  nomination: "Вокал",
  templateId: DIPLOMA_TEMPLATE,
  templateName: "Диплом A4",
  documentType: "DIPLOMA",
  createdAt: "2026-05-20T12:00:00Z",
  updatedAt: "2026-05-20T12:00:00Z",
};

const TEMPLATES: DiplomaTemplate[] = [
  {
    id: DIPLOMA_TEMPLATE,
    name: "Диплом A4",
    description: "",
    type: "DIPLOMA",
    usageCount: 1,
    updatedAt: "2026-05-01T12:00:00Z",
  },
];

function setup(assignments: DiplomaAssignment[] = [ASSIGNED_VOCALS]): {
  createAssignment: ReturnType<typeof vi.fn>;
} {
  const createAssignment = vi.fn().mockResolvedValue(undefined);

  vi.mocked(useCompetitionsList).mockReturnValue({
    data: [{ id: COMPETITION_ID, title: "Восходящие таланты" }],
    isLoading: false,
  } as unknown as ReturnType<typeof useCompetitionsList>);

  vi.mocked(useCompetitionDetail).mockReturnValue({
    data: {
      id: COMPETITION_ID,
      categories: [
        { id: VOCALS, name: "Вокал" },
        { id: DANCE, name: "Танец" },
        { id: THEATRE, name: "Театр" },
      ],
    },
    isLoading: false,
  } as unknown as ReturnType<typeof useCompetitionDetail>);

  vi.mocked(useDiplomaTemplates).mockReturnValue({
    data: TEMPLATES,
    isLoading: false,
  } as unknown as ReturnType<typeof useDiplomaTemplates>);

  vi.mocked(useDiplomaAssignments).mockReturnValue({
    data: assignments,
    isLoading: false,
  } as unknown as ReturnType<typeof useDiplomaAssignments>);

  vi.mocked(useCreateAssignmentMutation).mockReturnValue({
    mutateAsync: createAssignment,
    isPending: false,
  } as unknown as ReturnType<typeof useCreateAssignmentMutation>);

  vi.mocked(useDeleteAssignmentMutation).mockReturnValue({
    mutateAsync: vi.fn(),
    isPending: false,
  } as unknown as ReturnType<typeof useDeleteAssignmentMutation>);

  return { createAssignment };
}

/** Pick the section's competition — everything else only exists after that. */
async function chooseCompetition(): Promise<ReturnType<typeof userEvent.setup>> {
  const user = userEvent.setup();
  await user.click(screen.getByRole("combobox", { name: "Конкурс" }));
  await user.click(await screen.findByRole("option", { name: "Восходящие таланты" }));
  return user;
}

/** …and open the dialog on it, the state every dialog test starts from. */
async function openDialogForCompetition(): Promise<ReturnType<typeof userEvent.setup>> {
  const user = await chooseCompetition();
  await user.click(screen.getByRole("button", { name: "Создать назначение" }));
  return user;
}

afterEach(() => {
  vi.clearAllMocks();
});

describe("AssignmentsSection", () => {
  it("asks for the competition before anything else", async () => {
    setup();
    render(<AssignmentsSection />);

    expect(screen.getByText(/Выберите конкурс, чтобы увидеть его назначения/)).toBeInTheDocument();
    // Nothing to assign to yet, so there is nothing to assign with.
    expect(screen.queryByRole("button", { name: "Создать назначение" })).not.toBeInTheDocument();

    await chooseCompetition();

    expect(screen.getByRole("button", { name: "Создать назначение" })).toBeInTheDocument();
  });

  it("lists only the chosen competition's assignments", async () => {
    setup([
      ASSIGNED_VOCALS,
      {
        ...ASSIGNED_VOCALS,
        id: "01900000-0000-7000-8000-0000000000a9",
        competitionId: "01900000-0000-7000-8000-0000000000c9",
        competition: "Другой конкурс",
        nomination: "Хореография",
      },
    ]);
    render(<AssignmentsSection />);
    await chooseCompetition();

    expect(screen.getByText("Вокал")).toBeInTheDocument();
    // Another competition's assignment is not this competition's business.
    expect(screen.queryByText("Хореография")).not.toBeInTheDocument();
  });
});

describe("CreateAssignmentDialog", () => {
  it("offers only the nominations whose slot of that kind is free", async () => {
    setup();
    render(<AssignmentsSection />);
    await openDialogForCompetition();

    const dialog = screen.getByRole("dialog");
    expect(within(dialog).getByRole("checkbox", { name: "Танец" })).toBeInTheDocument();
    expect(within(dialog).getByRole("checkbox", { name: "Театр" })).toBeInTheDocument();
    // «Вокал» already has a diploma template, so offering it could only conflict.
    expect(within(dialog).queryByRole("checkbox", { name: "Вокал" })).not.toBeInTheDocument();
  });

  it("still offers a nomination whose other slot is taken", async () => {
    setup();
    render(<AssignmentsSection />);
    const user = await openDialogForCompetition();

    // «Вокал» has a diploma template but no thank-you one, so it is free here.
    await user.click(screen.getByRole("combobox", { name: "Тип документа" }));
    await user.click(await screen.findByRole("option", { name: "Благодарность" }));

    const dialog = screen.getByRole("dialog");
    expect(within(dialog).getByRole("checkbox", { name: "Вокал" })).toBeInTheDocument();
  });

  it("assigns one template to several nominations in one request", async () => {
    const { createAssignment } = setup();
    render(<AssignmentsSection />);
    const user = await openDialogForCompetition();

    await user.click(screen.getByRole("checkbox", { name: "Танец" }));
    await user.click(screen.getByRole("checkbox", { name: "Театр" }));
    await user.click(screen.getByRole("combobox", { name: "Шаблон диплома" }));
    await user.click(await screen.findByRole("option", { name: "Диплом A4" }));
    await user.click(screen.getByRole("button", { name: "Создать" }));

    expect(createAssignment).toHaveBeenCalledTimes(1);
    expect(createAssignment).toHaveBeenCalledWith({
      competitionId: COMPETITION_ID,
      categoryIds: [DANCE, THEATRE],
      templateId: DIPLOMA_TEMPLATE,
    });
  });

  it("selects and clears every free nomination at once", async () => {
    const { createAssignment } = setup();
    render(<AssignmentsSection />);
    const user = await openDialogForCompetition();

    await user.click(screen.getByRole("button", { name: "Выбрать все" }));
    expect(screen.getByText("Выбрано: 2")).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "Снять все" }));
    expect(screen.queryByText(/^Выбрано:/)).not.toBeInTheDocument();
    // Nothing picked — the submit stays closed rather than sending an empty batch.
    expect(screen.getByRole("button", { name: "Создать" })).toBeDisabled();
    expect(createAssignment).not.toHaveBeenCalled();
  });

  it("says so when every nomination of that kind is already assigned", async () => {
    setup([
      ASSIGNED_VOCALS,
      { ...ASSIGNED_VOCALS, id: "a2", categoryId: DANCE, nomination: "Танец" },
      { ...ASSIGNED_VOCALS, id: "a3", categoryId: THEATRE, nomination: "Театр" },
    ]);
    render(<AssignmentsSection />);
    await openDialogForCompetition();

    expect(screen.getByText(/уже назначен шаблон диплома/)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Создать" })).toBeDisabled();
  });
});
