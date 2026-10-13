/**
 * Карточка номера, у которого кончился приём.
 *
 * Правило одно, и считает его сервер: `editable` на номере — тот же ответ,
 * которым эндпоинт откажет правке. Здесь проверяется, что карточка этому ответу
 * верит: не предлагает удалить, дублировать и править номер, который приём уже
 * не принимает, и говорит почему — иначе у заявителя остаются кнопки, ведущие
 * в 409, и никакого объяснения.
 *
 * Номинации разные у разных номеров одной заявки: фестиваль, остановивший вокал
 * и продолжающий хореографию, закрыт и открыт одновременно, поэтому вопрос
 * задаётся про каждый номер отдельно.
 */
import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import type { SubmissionResource } from "@/shared/api/generated/model-applications";
import type { Registration } from "@/shared/api/generated/model-public-catalog";

const submission: { data: SubmissionResource | undefined } = { data: undefined };

vi.mock("../api/hooks", () => ({
  useSubmission: () => submission,
}));

// Форма номера — отдельный компонент со своими запросами; этот набор про то,
// показывают её вообще или нет.
vi.mock("./performance-form", () => ({
  PerformanceForm: () => <div>Форма выступления</div>,
}));

const { PerformanceCard } = await import("./performance-card");

function aSubmission(editable: boolean): SubmissionResource {
  return {
    id: "01900000-0000-7000-8000-00000000000a",
    type: "submission",
    competitionId: "01900000-0000-7000-8000-0000000000ff",
    status: "SUBMITTED",
    editable,
    performance: {
      title: "Весенний вальс",
      durationSeconds: 180,
      nominationId: "01900000-0000-7000-8000-000000000001",
      disciplineId: "01900000-0000-7000-8000-000000000002",
      ageCategoryId: "01900000-0000-7000-8000-000000000003",
      participantGroupId: "01900000-0000-7000-8000-000000000004",
      participationFormatId: "01900000-0000-7000-8000-000000000005",
      comment: "",
      ageComposition: "",
    },
    participants: [],
    teachers: [],
    attachments: [],
    reviews: [],
    statusHistory: [],
    price: null,
    createdAt: "2026-08-17T10:00:00.000Z",
    updatedAt: "2026-08-17T10:00:00.000Z",
  } as unknown as SubmissionResource;
}

const REGISTRATION = {
  nominations: [{ id: "01900000-0000-7000-8000-000000000001", name: "Вокал" }],
  participationFormats: [],
  ageCategories: [],
  admissionRules: [],
} as unknown as Registration;

function renderCard(editable: boolean): void {
  submission.data = aSubmission(editable);
  render(
    <PerformanceCard
      submissionId="01900000-0000-7000-8000-00000000000a"
      index={0}
      registration={REGISTRATION}
      onRemove={() => {}}
      onDuplicate={() => {}}
      removing={false}
      duplicating={false}
    />,
  );
}

describe("PerformanceCard — приём по номинации закрыт", () => {
  it("offers the editing form while the genre is open", () => {
    renderCard(true);

    expect(screen.getByText("Форма выступления")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Удалить" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Дублировать" })).toBeInTheDocument();
  });

  it("replaces the form with the reason once it closes", () => {
    renderCard(false);

    expect(screen.queryByText("Форма выступления")).toBeNull();
    expect(screen.getByText(/Приём заявок по этой номинации закрыт/)).toBeInTheDocument();
  });

  it("takes away the controls that would be refused", () => {
    renderCard(false);

    expect(screen.queryByRole("button", { name: "Удалить" })).toBeNull();
    expect(screen.queryByRole("button", { name: "Дублировать" })).toBeNull();
  });

  it("says on the closed card itself that it is closed", () => {
    renderCard(false);

    expect(screen.getByText("Приём закрыт")).toBeInTheDocument();
  });
});
