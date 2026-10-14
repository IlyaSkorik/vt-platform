import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import type { CorrectablePerformance, SubmissionTaxonomy } from "../api/hooks";
import { useCorrectSubmission } from "../api/hooks";
import { SubmissionCorrectionDialog } from "./correction-dialog";

vi.mock("../api/hooks", async (importOriginal) => ({
  ...(await importOriginal<typeof import("../api/hooks")>()),
  useCorrectSubmission: vi.fn(),
}));

const SUBMISSION = "01900000-0000-7000-8000-0000000000aa";
const PERFORMER = "01900000-0000-7000-8000-0000000000bb";
const TEACHER = "01900000-0000-7000-8000-0000000000cc";

const save = vi.fn();

const TAXONOMY: SubmissionTaxonomy = {
  nominations: [
    { id: "n1", name: "Вокал" },
    { id: "n2", name: "Хореография" },
  ],
  disciplines: [
    { id: "d1", name: "Эстрадный вокал", nominationId: "n1" },
    { id: "d2", name: "Народный танец", nominationId: "n2" },
  ],
  participantGroups: [{ id: "g1", name: "Соло" }],
  ageCategories: [
    { id: "a1", name: "7-9 лет", participantGroupId: "g1" },
    { id: "a2", name: "10-12 лет", participantGroupId: "g1" },
  ],
  participationFormats: [{ id: "f1", name: "Очно" }],
};

function aPerformance(overrides: Partial<CorrectablePerformance> = {}): CorrectablePerformance {
  return {
    submissionId: SUBMISSION,
    title: "Лебединое озеро",
    status: "SCHEDULED",
    canEditContent: true,
    durationSeconds: 210,
    comment: "",
    ageComposition: "",
    nominationId: "n1",
    disciplineId: "d1",
    ageCategoryId: "a1",
    participantGroupId: "g1",
    participationFormatId: "f1",
    participants: [
      {
        id: PERFORMER,
        displayName: "Иванва Анна",
        firstName: "Анна",
        lastName: "Иванва",
        middleName: null,
        birthDate: "2016-05-12",
        gender: "FEMALE",
        memberCount: 1,
        members: [],
      },
    ],
    teachers: [
      { id: TEACHER, firstName: "Ольга", lastName: "Петрова", middleName: null, role: "Педагог" },
    ],
    ...overrides,
  };
}

/** Солистка из `aPerformance`, с переопределённым учреждением. */
function withOrganization(pinned: string | null, resolved: string | null): CorrectablePerformance {
  const performance = aPerformance();
  return {
    ...performance,
    participants: (performance.participants ?? []).map((performer) => ({
      ...performer,
      organizationName: pinned,
      resolvedOrganizationName: resolved,
    })),
  };
}

function renderFor(performance: CorrectablePerformance = aPerformance()) {
  const onOpenChange = vi.fn();
  render(
    <SubmissionCorrectionDialog
      open
      onOpenChange={onOpenChange}
      performance={performance}
      taxonomy={TAXONOMY}
    />,
  );
  return { onOpenChange };
}

/**
 * Поля формы адресуются внутри своего раздела: «Фамилия» есть и у участника, и у
 * педагога, и запрос по всему диалогу нашёл бы обе.
 */
function section(name: "Выступление" | "Участники" | "Педагоги") {
  return within(screen.getByRole("region", { name }));
}

beforeEach(() => {
  save.mockReset();
  vi.mocked(useCorrectSubmission).mockReturnValue({
    mutate: save,
    isPending: false,
  } as unknown as ReturnType<typeof useCorrectSubmission>);
});

describe("SubmissionCorrectionDialog", () => {
  it("opens on what the entry actually says, not on an empty form", async () => {
    // Исправляют опечатку, а не заполняют заявку заново: незаполненная форма
    // означала бы, что организатор должен перебить все данные участника.
    renderFor();

    expect(await screen.findByLabelText("Название номера")).toHaveValue("Лебединое озеро");
    expect(section("Участники").getByLabelText("Фамилия")).toHaveValue("Иванва");
    expect(screen.getByLabelText("Минут")).toHaveValue(3);
    expect(screen.getByLabelText("Секунд")).toHaveValue(30);
  });

  it("sends a soloist without a caption, so the fixed surname renames the entry", async () => {
    // Подпись участника собирается сервером из ФИО. Отправить старую значит оставить
    // в карточке «Иванва Анна» рядом с исправленной фамилией.
    const user = userEvent.setup();
    renderFor();

    const surname = section("Участники").getByLabelText("Фамилия");
    await user.clear(surname);
    await user.type(surname, "Иванова");
    await user.click(screen.getByRole("button", { name: "Сохранить исправление" }));

    await waitFor(() => expect(save).toHaveBeenCalled());
    const payload = save.mock.calls[0]?.[0].payload;
    expect(payload.participants[0]).toMatchObject({
      id: PERFORMER,
      lastName: "Иванова",
      displayName: null,
    });
  });

  it("sends the whole section, so a removed performer is actually removed", async () => {
    const user = userEvent.setup();
    renderFor();

    await user.click(section("Участники").getByRole("button", { name: /Убрать/ }));
    await user.click(screen.getByRole("button", { name: "Сохранить исправление" }));

    await waitFor(() =>
      expect(
        screen.getByText("В номере должен остаться хотя бы один участник."),
      ).toBeInTheDocument(),
    );
    expect(save).not.toHaveBeenCalled();
  });

  it("keeps a collective's roster as the lines it was typed in", async () => {
    const user = userEvent.setup();
    renderFor(
      aPerformance({
        participants: [
          {
            id: PERFORMER,
            displayName: "Ансамбль «Радуга»",
            firstName: null,
            lastName: null,
            middleName: null,
            birthDate: null,
            gender: null,
            memberCount: 8,
            members: ["Иванова Анна", "Петров Пётр"],
          },
        ],
      }),
    );

    expect(await screen.findByLabelText("Название коллектива")).toHaveValue("Ансамбль «Радуга»");
    expect(screen.getByLabelText("Численность")).toHaveValue(8);

    await user.click(screen.getByRole("button", { name: "Сохранить исправление" }));

    await waitFor(() => expect(save).toHaveBeenCalled());
    expect(save.mock.calls[0]?.[0].payload.participants[0]).toMatchObject({
      displayName: "Ансамбль «Радуга»",
      memberCount: 8,
      members: ["Иванова Анна", "Петров Пётр"],
      lastName: null,
    });
  });

  describe("учреждение", () => {
    it("opens on the institution that is printed today, not on an empty field", async () => {
      // Пустое поле там, где учреждение есть, читается как «его нет» — и первое же
      // сохранение сделало бы это правдой.
      renderFor(withOrganization(null, "ДШИ №1"));

      expect(await section("Участники").findByLabelText("Учреждение")).toHaveValue("ДШИ №1");
    });

    it("pins nothing when the organizer did not touch the institution", async () => {
      // Иначе любая правка фамилии молча отвязывала бы заявку от реестра, и заявка,
      // поданная год назад, перестала бы следовать за переименованием школы.
      const user = userEvent.setup();
      renderFor(withOrganization(null, "ДШИ №1"));

      const surname = section("Участники").getByLabelText("Фамилия");
      await user.clear(surname);
      await user.type(surname, "Иванова");
      await user.click(screen.getByRole("button", { name: "Сохранить исправление" }));

      await waitFor(() => expect(save).toHaveBeenCalled());
      expect(save.mock.calls[0]?.[0].payload.participants[0].organizationName).toBeNull();
    });

    it("pins the institution the organizer typed over the registry's", async () => {
      const user = userEvent.setup();
      renderFor(withOrganization(null, "ДШИ №1"));

      const organization = await section("Участники").findByLabelText("Учреждение");
      await user.clear(organization);
      await user.type(organization, "ДШИ №2");
      await user.click(screen.getByRole("button", { name: "Сохранить исправление" }));

      await waitFor(() => expect(save).toHaveBeenCalled());
      expect(save.mock.calls[0]?.[0].payload.participants[0].organizationName).toBe("ДШИ №2");
    });

    it("clearing the field hands the performer back to the registry", async () => {
      // Пустое поле — «брать из реестра», а не «учреждения нет»: организатор
      // отменяет свою правку, а не утверждает, что участник ниоткуда.
      const user = userEvent.setup();
      renderFor(withOrganization("ДШИ №2", "ДШИ №2"));

      await user.clear(await section("Участники").findByLabelText("Учреждение"));
      await user.click(screen.getByRole("button", { name: "Сохранить исправление" }));

      await waitFor(() => expect(save).toHaveBeenCalled());
      expect(save.mock.calls[0]?.[0].payload.participants[0].organizationName).toBeNull();
    });
  });

  it("offers only the nominations of the chosen genre", async () => {
    // Номинация заведена внутри жанра; чужая строка — сочетание, которого фестиваль
    // не принимает, и заявка встанет на нём же.
    const user = userEvent.setup();
    renderFor();

    await user.click(section("Выступление").getByRole("combobox", { name: /Номинация/ }));

    expect(await screen.findByRole("option", { name: "Эстрадный вокал" })).toBeInTheDocument();
    expect(screen.queryByRole("option", { name: "Народный танец" })).not.toBeInTheDocument();
  });

  it("refuses to save a number with no title rather than sending a blank one", async () => {
    const user = userEvent.setup();
    renderFor();

    const title = await screen.findByLabelText("Название номера");
    await user.clear(title);
    await user.click(screen.getByRole("button", { name: "Сохранить исправление" }));

    expect(await screen.findByText("Укажите название номера.")).toBeInTheDocument();
    expect(save).not.toHaveBeenCalled();
  });
});
