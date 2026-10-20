import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import {
  useRegistration,
  useRemoveSubmissionAttachment,
  useSubmissionDetail,
  useUploadSubmissionAttachment,
} from "@/entities/application";
import type {
  ApplicationResource,
  SubmissionResource,
} from "@/shared/api/generated/model-applications";

import { PhonogramsCard } from "./phonograms-card";

// The hooks are stubbed; the rule that decides whether files may be touched is not —
// it is the thing under test here as much as the markup is.
vi.mock("@/entities/application", async (importOriginal) => ({
  ...(await importOriginal<typeof import("@/entities/application")>()),
  useRegistration: vi.fn(),
  useSubmissionDetail: vi.fn(),
  useUploadSubmissionAttachment: vi.fn(),
  useRemoveSubmissionAttachment: vi.fn(),
}));

const SUBMISSION = "01900000-0000-7000-8000-000000000001";
const FORMAT = "01900000-0000-7000-8000-0000000000aa";
const INPUT_LABEL = "Фонограммы: Катюша";

const upload = vi.fn();

function anApplication(status = "ACCEPTED"): ApplicationResource {
  return {
    id: "01900000-0000-7000-8000-0000000000ff",
    competitionId: "01900000-0000-7000-8000-0000000000ee",
    status: "PAID",
    submissions: [{ submissionId: SUBMISSION, status, performanceTitle: "Катюша" }],
  } as unknown as ApplicationResource;
}

function aTrack(id: string, file: string) {
  return { id, type: "MUSIC", fileReference: file, caption: null };
}

function stubSubmission(attachments: unknown[]): void {
  vi.mocked(useSubmissionDetail).mockReturnValue({
    data: {
      id: SUBMISSION,
      attachments,
      performance: { participationFormatId: FORMAT },
    } as unknown as SubmissionResource,
  } as unknown as ReturnType<typeof useSubmissionDetail>);
}

beforeEach(() => {
  vi.clearAllMocks();
  upload.mockResolvedValue(undefined);
  vi.mocked(useRegistration).mockReturnValue({
    data: {
      editingLocked: false,
      musicUploadOpen: true,
      mediaUploadOpen: true,
      documentUploadOpen: true,
      uploadRequirements: [
        {
          participationFormatId: FORMAT,
          musicRequired: true,
          musicAllowedFormats: ["mp3", "wav"],
          musicMaxUploadSizeMb: 25,
          videoMode: "NONE",
          receiptRequired: false,
        },
      ],
    },
  } as unknown as ReturnType<typeof useRegistration>);
  vi.mocked(useUploadSubmissionAttachment).mockReturnValue({
    mutateAsync: upload,
    isPending: false,
  } as unknown as ReturnType<typeof useUploadSubmissionAttachment>);
  vi.mocked(useRemoveSubmissionAttachment).mockReturnValue({
    mutate: vi.fn(),
    isPending: false,
  } as unknown as ReturnType<typeof useRemoveSubmissionAttachment>);
});

describe("PhonogramsCard", () => {
  it("still offers the upload once the entry has been accepted into the programme", () => {
    stubSubmission([]);
    render(<PhonogramsCard application={anApplication("ACCEPTED")} />);

    expect(screen.getByText(/Фонограммы не приложены/)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Загрузить фонограмму/ })).toBeInTheDocument();
  });

  it("lists every track of one performance, numbered in order", () => {
    stubSubmission([
      aTrack("t1", "uploads/2026/vstuplenie.mp3"),
      aTrack("t2", "uploads/2026/osnova.mp3"),
    ]);
    render(<PhonogramsCard application={anApplication("SCHEDULED")} />);

    expect(screen.getByText("vstuplenie.mp3")).toBeInTheDocument();
    expect(screen.getByText("osnova.mp3")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Добавить ещё/ })).toBeInTheDocument();
  });

  it("uploads a whole selection one file at a time", async () => {
    stubSubmission([]);
    render(<PhonogramsCard application={anApplication("PAID")} />);

    await userEvent.upload(screen.getByLabelText(INPUT_LABEL), [
      new File(["a"], "part-1.mp3", { type: "audio/mpeg" }),
      new File(["b"], "part-2.mp3", { type: "audio/mpeg" }),
    ]);

    await waitFor(() => expect(upload).toHaveBeenCalledTimes(2));
    expect(upload.mock.calls.map(([input]) => (input.file as File).name)).toEqual([
      "part-1.mp3",
      "part-2.mp3",
    ]);
  });

  it("says so and offers nothing once the organizer has frozen the festival", () => {
    // Приём может быть ещё открыт, а срок загрузки — через неделю: единственный
    // честный ответ здесь тот, что это решение организатора.
    vi.mocked(useRegistration).mockReturnValue({
      data: { editingLocked: true, musicUploadOpen: false, uploadRequirements: [] },
    } as unknown as ReturnType<typeof useRegistration>);
    stubSubmission([aTrack("t1", "uploads/2026/final.mp3")]);

    render(<PhonogramsCard application={anApplication("ACCEPTED")} />);

    expect(screen.getByText(/Организатор закрыл редактирование/)).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /Добавить ещё/ })).not.toBeInTheDocument();
  });

  it("names the deadline, not the organizer, when it is the deadline that passed", () => {
    vi.mocked(useRegistration).mockReturnValue({
      data: { editingLocked: false, musicUploadOpen: false, uploadRequirements: [] },
    } as unknown as ReturnType<typeof useRegistration>);
    stubSubmission([]);

    render(<PhonogramsCard application={anApplication("ACCEPTED")} />);

    expect(screen.getByText(/Срок загрузки/)).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /Загрузить фонограмму/ })).not.toBeInTheDocument();
  });

  it("hides the controls for a finished entry but keeps showing its tracks", () => {
    stubSubmission([aTrack("t1", "uploads/2026/final.mp3")]);
    render(<PhonogramsCard application={anApplication("COMPLETED")} />);

    expect(screen.getByText("final.mp3")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /Добавить ещё/ })).not.toBeInTheDocument();
  });
});
