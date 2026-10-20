/**
 * Видео и фото на карточке заявки — то место, где их меняют после закрытия приёма.
 *
 * До этой карточки материал жил только внутри экрана редактирования, который
 * закрывается вместе с приёмом: «перезалить видео» означало написать организатору.
 * Поэтому тесты здесь про две вещи — что файл действительно можно загрузить у
 * принятой заявки, и что карточка честно говорит, когда уже нельзя.
 */
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

import { MediaCard } from "./media-card";

// Хуки подменены, правило доступа к файлам — нет: оно здесь предмет проверки
// ровно в той же мере, что и разметка.
vi.mock("@/entities/application", async (importOriginal) => ({
  ...(await importOriginal<typeof import("@/entities/application")>()),
  useRegistration: vi.fn(),
  useSubmissionDetail: vi.fn(),
  useUploadSubmissionAttachment: vi.fn(),
  useRemoveSubmissionAttachment: vi.fn(),
}));

const SUBMISSION = "01900000-0000-7000-8000-000000000001";
const FORMAT = "01900000-0000-7000-8000-0000000000aa";
const INPUT_LABEL = "Видео и фото: Катюша";

const upload = vi.fn();

function anApplication(status = "ACCEPTED"): ApplicationResource {
  return {
    id: "01900000-0000-7000-8000-0000000000ff",
    competitionId: "01900000-0000-7000-8000-0000000000ee",
    status: "PAID",
    submissions: [{ submissionId: SUBMISSION, status, performanceTitle: "Катюша" }],
  } as unknown as ApplicationResource;
}

function aFile(id: string, type: "VIDEO" | "IMAGE", reference: string) {
  return { id, type, fileReference: reference, caption: null, sizeBytes: 1024 };
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

function stubRegistration(overrides: Record<string, unknown> = {}, mediaMode = "FILE_ONLY"): void {
  vi.mocked(useRegistration).mockReturnValue({
    data: {
      editingLocked: false,
      musicUploadOpen: true,
      mediaUploadOpen: true,
      documentUploadOpen: true,
      uploadRequirements: [
        {
          participationFormatId: FORMAT,
          musicRequired: false,
          musicAllowedFormats: ["mp3"],
          musicMaxUploadSizeMb: 25,
          mediaMode,
          mediaRequired: false,
          mediaAllowedFormats: ["mp4", "jpg"],
          mediaMaxTotalSizeMb: 200,
          receiptRequired: false,
        },
      ],
      ...overrides,
    },
  } as unknown as ReturnType<typeof useRegistration>);
}

beforeEach(() => {
  vi.clearAllMocks();
  upload.mockResolvedValue(undefined);
  stubRegistration();
  vi.mocked(useUploadSubmissionAttachment).mockReturnValue({
    mutateAsync: upload,
    isPending: false,
  } as unknown as ReturnType<typeof useUploadSubmissionAttachment>);
  vi.mocked(useRemoveSubmissionAttachment).mockReturnValue({
    mutate: vi.fn(),
    isPending: false,
  } as unknown as ReturnType<typeof useRemoveSubmissionAttachment>);
});

describe("MediaCard", () => {
  it("offers the upload for an entry already accepted into the programme", () => {
    stubSubmission([]);

    render(<MediaCard application={anApplication("ACCEPTED")} />);

    expect(screen.getByText(/Видео и фотографии не приложены/)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Загрузить файлы/ })).toBeInTheDocument();
  });

  it("sends a photograph as IMAGE and everything else as VIDEO", async () => {
    // Одно поле на оба вида: разделение по расширению — то же правило, что в мастере,
    // и заявитель про типы вложений ничего не знает.
    stubSubmission([]);
    render(<MediaCard application={anApplication("PAID")} />);

    await userEvent.upload(screen.getByLabelText(INPUT_LABEL), [
      new File(["a"], "nomer.mp4", { type: "video/mp4" }),
      new File(["b"], "scena.JPG", { type: "image/jpeg" }),
    ]);

    await waitFor(() => expect(upload).toHaveBeenCalledTimes(2));
    expect(upload.mock.calls.map(([input]) => input.attachmentType)).toEqual(["VIDEO", "IMAGE"]);
  });

  it("lists what is attached, saying which is which", () => {
    stubSubmission([
      aFile("f1", "VIDEO", "uploads/2026/nomer.mp4"),
      aFile("f2", "IMAGE", "uploads/2026/scena.jpg"),
    ]);

    render(<MediaCard application={anApplication("SCHEDULED")} />);

    expect(screen.getByText("nomer.mp4")).toBeInTheDocument();
    expect(screen.getByText("scena.jpg")).toBeInTheDocument();
    expect(screen.getByText("видео")).toBeInTheDocument();
    expect(screen.getByText("фото")).toBeInTheDocument();
  });

  it("says who closed it when the organizer froze the festival", () => {
    stubRegistration({ editingLocked: true, mediaUploadOpen: false });
    stubSubmission([aFile("f1", "VIDEO", "uploads/2026/nomer.mp4")]);

    render(<MediaCard application={anApplication("ACCEPTED")} />);

    expect(screen.getByText(/Организатор закрыл редактирование/)).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /Добавить ещё/ })).not.toBeInTheDocument();
  });

  it("blames the deadline when it is the deadline that passed", () => {
    stubRegistration({ mediaUploadOpen: false });
    stubSubmission([]);

    render(<MediaCard application={anApplication("ACCEPTED")} />);

    expect(screen.getByText(/Срок загрузки/)).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /Загрузить файлы/ })).not.toBeInTheDocument();
  });

  it("stays out of the way of a festival that collects no media files", () => {
    // Фестиваль, который берёт только ссылку на видео (или не берёт ничего), не
    // должен показывать поле загрузки, которого у него нет.
    stubRegistration({}, "URL_ONLY");
    stubSubmission([]);

    render(<MediaCard application={anApplication("ACCEPTED")} />);

    expect(screen.queryByRole("button", { name: /Загрузить файлы/ })).not.toBeInTheDocument();
  });
});
