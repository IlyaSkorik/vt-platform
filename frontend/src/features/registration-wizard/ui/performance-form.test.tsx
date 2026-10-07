import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import type { SubmissionResource } from "@/shared/api/generated/model-applications";
import type { Registration } from "@/shared/api/generated/model-public-catalog";

import {
  useAddParticipant,
  useAddTeacher,
  useCalculatePrice,
  useRemoveParticipant,
  useRemoveTeacher,
  useSetPerformance,
  useSubmission,
} from "../api/hooks";
import { PerformanceForm } from "./performance-form";

vi.mock("../api/hooks", () => ({
  useSubmission: vi.fn(),
  useSetPerformance: vi.fn(),
  useAddParticipant: vi.fn(),
  useAddTeacher: vi.fn(),
  useRemoveParticipant: vi.fn(),
  useRemoveTeacher: vi.fn(),
  useCalculatePrice: vi.fn(),
}));

// The pickers and the uploader own their own data access; this suite is about the
// performance fields, so they are stubbed out to keep the tree self-contained.
vi.mock("./participant-picker", () => ({ ParticipantPicker: () => null }));
vi.mock("./teacher-picker", () => ({ TeacherPicker: () => null }));
vi.mock("./upload-controls", () => ({ UploadControls: () => null }));

const NOMINATION = "01900000-0000-7000-8000-000000000001";
const DISCIPLINE = "01900000-0000-7000-8000-000000000002";
const AGE_CATEGORY = "01900000-0000-7000-8000-000000000003";
const GROUP = "01900000-0000-7000-8000-000000000004";
const FORMAT = "01900000-0000-7000-8000-000000000005";

const COMMENT = "Выход с точки 3. Нужен микрофон на стойке.";
/** The label carries a required marker ("*"), so it is matched loosely. */
const AGE_FIELD_LABEL = /Возрастной состав участников/;

const savePerformance = vi.fn();

function aRegistration({
  mixedAge = false,
  commentEnabled = true,
  waitlisted = false,
}: {
  mixedAge?: boolean;
  commentEnabled?: boolean;
  /** The genre has closed but keeps a queue — the second door into it. */
  waitlisted?: boolean;
} = {}): Registration {
  return {
    competition: {
      id: "01900000-0000-7000-8000-0000000000ff",
      title: "Весенний фестиваль",
      season: "2025/2026",
      status: "PUBLISHED",
      venueName: null,
      venueAddress: null,
    },
    registrationOpen: !waitlisted,
    waitlistOpen: waitlisted,
    allowMultiplePerformances: true,
    collectPayerDetails: false,
    participantCommentEnabled: commentEnabled,
    deadlines: {
      application: null,
      payment: null,
      musicUpload: null,
      documentUpload: null,
      correction: null,
    },
    nominations: [
      {
        id: NOMINATION,
        name: "Хореография",
        description: null,
        sortOrder: 1,
        registrationOpen: !waitlisted,
        registrationStopped: waitlisted,
        waitlistEnabled: waitlisted,
        waitlistOpen: waitlisted,
        registrationOpensAt: null,
        registrationClosesAt: null,
      },
    ],
    disciplines: [
      { id: DISCIPLINE, nominationId: NOMINATION, name: "Народный танец", sortOrder: 1 },
    ],
    ageCategories: [
      {
        id: AGE_CATEGORY,
        participantGroupId: GROUP,
        name: mixedAge ? "Смешанная" : "10-12 лет",
        minAge: 10,
        maxAge: mixedAge ? 60 : 12,
        sortOrder: 1,
        type: mixedAge ? "MIXED" : "STANDARD",
        mixedCalculationMethod: mixedAge ? "AVERAGE" : null,
      },
    ],
    participantGroups: [{ id: GROUP, name: "Соло", minCount: 1, maxCount: 1, sortOrder: 1 }],
    participationFormats: [{ id: FORMAT, name: "Очно", sortOrder: 1 }],
    admissionRules: [
      {
        nominationId: NOMINATION,
        disciplineId: DISCIPLINE,
        ageCategoryId: AGE_CATEGORY,
        participantGroupId: GROUP,
        participationFormatId: FORMAT,
      },
    ],
    additionalServices: [],
    requiredConsents: [],
    uploadRequirements: [],
  };
}

/** A submission whose performance is already complete and admissible. */
function aSubmission(comment: string, ageComposition = ""): SubmissionResource {
  return {
    id: "01900000-0000-7000-8000-00000000000a",
    type: "submission",
    competitionId: "01900000-0000-7000-8000-0000000000ff",
    status: "DRAFT",
    performance: {
      title: "Танец с лентами",
      durationSeconds: 180,
      nominationId: NOMINATION,
      disciplineId: DISCIPLINE,
      ageCategoryId: AGE_CATEGORY,
      participantGroupId: GROUP,
      participationFormatId: FORMAT,
      comment,
      ageComposition,
    },
    participants: [],
    teachers: [],
    attachments: [],
    statusHistory: [],
    price: null,
    createdAt: "2026-07-10T10:00:00Z",
    updatedAt: "2026-07-10T10:00:00Z",
  };
}

function stubHooks(submission: SubmissionResource): void {
  vi.mocked(useSubmission).mockReturnValue({
    data: submission,
    isLoading: false,
  } as unknown as ReturnType<typeof useSubmission>);
  vi.mocked(useSetPerformance).mockReturnValue({
    mutate: savePerformance,
    isPending: false,
  } as unknown as ReturnType<typeof useSetPerformance>);
  const idleMutation = { mutate: vi.fn(), mutateAsync: vi.fn(), isPending: false };
  vi.mocked(useAddParticipant).mockReturnValue(
    idleMutation as unknown as ReturnType<typeof useAddParticipant>,
  );
  vi.mocked(useAddTeacher).mockReturnValue(
    idleMutation as unknown as ReturnType<typeof useAddTeacher>,
  );
  vi.mocked(useRemoveParticipant).mockReturnValue(
    idleMutation as unknown as ReturnType<typeof useRemoveParticipant>,
  );
  vi.mocked(useRemoveTeacher).mockReturnValue(
    idleMutation as unknown as ReturnType<typeof useRemoveTeacher>,
  );
  vi.mocked(useCalculatePrice).mockReturnValue(
    idleMutation as unknown as ReturnType<typeof useCalculatePrice>,
  );
}

function renderForm({
  mixedAge = false,
  commentEnabled = true,
  waitlisted = false,
}: {
  mixedAge?: boolean;
  commentEnabled?: boolean;
  waitlisted?: boolean;
} = {}): void {
  // The attached participants read their organization straight from the registry, so
  // the tree needs a query client even though this suite stubs every wizard hook.
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter>
        <PerformanceForm
          submissionId="01900000-0000-7000-8000-00000000000a"
          registration={aRegistration({ mixedAge, commentEnabled, waitlisted })}
        />
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

const FIELD_LABEL = "Дополнительная информация для организаторов";

beforeEach(() => {
  savePerformance.mockReset();
});

afterEach(() => {
  vi.clearAllMocks();
});

describe("PerformanceForm — the applicant's note for the organizers", () => {
  it("renders an optional multi-line field with its hint", () => {
    stubHooks(aSubmission(""));
    renderForm();

    const field = screen.getByLabelText(FIELD_LABEL);
    expect(field.tagName).toBe("TEXTAREA");
    // Optional: no required marker on the label.
    expect(field).not.toBeRequired();
    expect(screen.getByText(/Здесь можно указать особенности выступления/)).toBeInTheDocument();
  });

  it("is not offered at all where the festival does not accept a note", () => {
    stubHooks(aSubmission(""));
    renderForm({ commentEnabled: false });

    expect(screen.queryByLabelText(FIELD_LABEL)).not.toBeInTheDocument();
  });

  it("clears a note written before the organizer switched the field off", async () => {
    // The field is gone, so the applicant cannot delete the note themselves — and the
    // backend refuses to accept a submission that still carries one. The form drops it.
    stubHooks(aSubmission(COMMENT));
    renderForm({ commentEnabled: false });

    await waitFor(() => expect(savePerformance).toHaveBeenCalled(), { timeout: 3000 });
    const [body] = savePerformance.mock.calls.at(-1) as [{ comment: string }];
    expect(body.comment).toBe("");
  });

  it("saves nothing on mount where the field is off and no note was ever written", async () => {
    stubHooks(aSubmission(""));
    renderForm({ commentEnabled: false });

    await new Promise((resolve) => setTimeout(resolve, 1000));
    expect(savePerformance).not.toHaveBeenCalled();
  });

  it("prefills the stored note", () => {
    stubHooks(aSubmission(COMMENT));
    renderForm();

    expect(screen.getByLabelText(FIELD_LABEL)).toHaveValue(COMMENT);
  });

  it("autosaves the note with the rest of the performance", async () => {
    const user = userEvent.setup();
    stubHooks(aSubmission(""));
    renderForm();

    await user.type(screen.getByLabelText(FIELD_LABEL), "микрофон");

    // The form debounces saves, so wait past the debounce window.
    await waitFor(() => expect(savePerformance).toHaveBeenCalled(), { timeout: 3000 });
    const [body] = savePerformance.mock.calls.at(-1) as [{ comment: string; title: string }];
    expect(body.comment).toBe("микрофон");
    expect(body.title).toBe("Танец с лентами");
  });

  it("trims the note before saving it", async () => {
    const user = userEvent.setup();
    stubHooks(aSubmission(""));
    renderForm();

    await user.type(screen.getByLabelText(FIELD_LABEL), "  реквизит  ");

    await waitFor(() => expect(savePerformance).toHaveBeenCalled(), { timeout: 3000 });
    const [body] = savePerformance.mock.calls.at(-1) as [{ comment: string }];
    expect(body.comment).toBe("реквизит");
  });

  it("stops at the backend's length bound rather than letting the save fail", () => {
    stubHooks(aSubmission(""));
    renderForm();

    expect(screen.getByLabelText(FIELD_LABEL)).toHaveAttribute("maxlength", "1000");
  });

  it("leaves the note out of the form's completeness check (it is optional)", () => {
    stubHooks(aSubmission(""));
    renderForm();

    expect(screen.getByText("Изменения сохраняются автоматически")).toBeInTheDocument();
  });
});

describe("PerformanceForm — a genre that closed but keeps a queue", () => {
  it("still offers the genre, marked for what it is", () => {
    stubHooks(aSubmission(""));
    renderForm({ waitlisted: true });

    expect(screen.queryByText("Приём заявок закрыт")).not.toBeInTheDocument();
    expect(screen.getByText("Хореография — лист ожидания")).toBeInTheDocument();
  });

  it("says up front that this buys a place in a queue, not in the programme", () => {
    stubHooks(aSubmission(""));
    renderForm({ waitlisted: true });

    expect(screen.getByText("Заявка пойдёт в лист ожидания")).toBeInTheDocument();
    expect(screen.getByText(/оплата не потребуется/)).toBeInTheDocument();
  });

  it("says none of that while the genre is open", () => {
    stubHooks(aSubmission(""));
    renderForm();

    expect(screen.queryByText("Заявка пойдёт в лист ожидания")).not.toBeInTheDocument();
  });
});

describe("PerformanceForm — the ages behind a mixed category", () => {
  it("asks for nothing when the age category is a standard band", () => {
    stubHooks(aSubmission(""));
    renderForm();

    expect(screen.queryByLabelText(AGE_FIELD_LABEL)).not.toBeInTheDocument();
  });

  it("asks for the ages, as required, when the category is a mixed one", () => {
    stubHooks(aSubmission(""));
    renderForm({ mixedAge: true });

    const field = screen.getByLabelText(AGE_FIELD_LABEL);
    expect(field.tagName).toBe("TEXTAREA");
    expect(field).toBeRequired();
  });

  it("says how the organizer will read the answer back to one age", () => {
    stubHooks(aSubmission(""));
    renderForm({ mixedAge: true });

    expect(screen.getByText(/по среднему возрасту/)).toBeInTheDocument();
  });

  it("prefills what was already stated", () => {
    stubHooks(aSubmission("", "12 детей 8–11 лет"));
    renderForm({ mixedAge: true });

    expect(screen.getByLabelText(AGE_FIELD_LABEL)).toHaveValue("12 детей 8–11 лет");
  });

  it("autosaves the ages with the rest of the performance", async () => {
    const user = userEvent.setup();
    stubHooks(aSubmission(""));
    renderForm({ mixedAge: true });

    await user.type(screen.getByLabelText(AGE_FIELD_LABEL), "  дети и педагоги  ");

    await waitFor(() => expect(savePerformance).toHaveBeenCalled(), { timeout: 3000 });
    const [body] = savePerformance.mock.calls.at(-1) as [{ ageComposition: string }];
    expect(body.ageComposition).toBe("дети и педагоги");
  });
});
