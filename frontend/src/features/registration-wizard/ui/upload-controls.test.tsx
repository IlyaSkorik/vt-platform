import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { ApiError } from "@/shared/api";
import type { SubmissionResource } from "@/shared/api/generated/model-applications";
import type { RegistrationUploadRequirement } from "@/shared/api/generated/model-public-catalog";
import { toast } from "@/shared/ui";

import { useRemoveAttachment, useUploadAttachment } from "../api/hooks";
import { UploadControls } from "./upload-controls";

vi.mock("../api/hooks", () => ({
  useUploadAttachment: vi.fn(),
  useRemoveAttachment: vi.fn(),
}));

vi.mock("@/shared/ui", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/shared/ui")>();
  return { ...actual, toast: { ...actual.toast, error: vi.fn(), success: vi.fn() } };
});

const SUBMISSION_ID = "01900000-0000-7000-8000-000000000001";
const upload = vi.fn();

function aRequirement(
  overrides: Partial<RegistrationUploadRequirement> = {},
): RegistrationUploadRequirement {
  return {
    participationFormatId: "01900000-0000-7000-8000-0000000000ff",
    musicRequired: true,
    musicAllowedFormats: ["mp3", "wav"],
    musicMaxUploadSizeMb: 25,
    videoMode: "NONE",
    videoAllowedFormats: ["mp4", "mov"],
    videoMaxUploadSizeMb: 200,
    receiptRequired: false,
    ...overrides,
  } as RegistrationUploadRequirement;
}

const MUSIC_LABEL = "Фонограммы (обязательно)";
const MUSIC_HINT = "mp3, wav · до 25 МБ за файл · можно несколько";

const EMPTY_SUBMISSION = { attachments: [] } as unknown as SubmissionResource;

/** A File of a given size without allocating the bytes. */
function aFile(name: string, sizeBytes: number, type = "audio/mpeg"): File {
  const file = new File(["x"], name, { type });
  Object.defineProperty(file, "size", { value: sizeBytes });
  return file;
}

beforeEach(() => {
  vi.clearAllMocks();
  upload.mockResolvedValue(EMPTY_SUBMISSION);
  vi.mocked(useUploadAttachment).mockReturnValue({
    mutateAsync: upload,
    isPending: false,
  } as unknown as ReturnType<typeof useUploadAttachment>);
  vi.mocked(useRemoveAttachment).mockReturnValue({
    mutate: vi.fn(),
    isPending: false,
  } as unknown as ReturnType<typeof useRemoveAttachment>);
});

function renderControls(
  requirement = aRequirement(),
  submission: SubmissionResource = EMPTY_SUBMISSION,
) {
  return render(
    <UploadControls
      submissionId={SUBMISSION_ID}
      submission={submission}
      requirement={requirement}
    />,
  );
}

describe("UploadControls", () => {
  it("refuses an oversized file before it is sent", async () => {
    renderControls();

    await userEvent.upload(
      screen.getByLabelText(MUSIC_LABEL),
      aFile("track.mp3", 42 * 1024 * 1024),
    );

    expect(upload).not.toHaveBeenCalled();
    expect(toast.error).toHaveBeenCalledWith("track.mp3: 42 МБ, а допустимо до 25 МБ");
  });

  it("sends a file that fits", async () => {
    renderControls();

    await userEvent.upload(screen.getByLabelText(MUSIC_LABEL), aFile("track.mp3", 3 * 1024 * 1024));

    await waitFor(() => expect(upload).toHaveBeenCalled());
    expect(toast.error).not.toHaveBeenCalled();
  });

  it("sends every phonogram of a multi-file selection, one at a time", async () => {
    renderControls();

    await userEvent.upload(screen.getByLabelText(MUSIC_LABEL), [
      aFile("part-1.mp3", 1024),
      aFile("part-2.mp3", 2048),
    ]);

    await waitFor(() => expect(upload).toHaveBeenCalledTimes(2));
    expect(upload.mock.calls.map(([input]) => (input.file as File).name)).toEqual([
      "part-1.mp3",
      "part-2.mp3",
    ]);
    expect(toast.error).not.toHaveBeenCalled();
  });

  it("keeps uploading the rest of the selection when one file is refused", async () => {
    upload.mockRejectedValueOnce(new ApiError("File too large", { status: 413 }));
    renderControls();

    await userEvent.upload(screen.getByLabelText(MUSIC_LABEL), [
      aFile("huge.mp3", 1024),
      aFile("fine.mp3", 1024),
    ]);

    await waitFor(() => expect(upload).toHaveBeenCalledTimes(2));
    expect(toast.error).toHaveBeenCalledWith("huge.mp3: Файл слишком большой. Допустимо до 25 МБ.");
  });

  it("offers to add another track once one is attached", () => {
    renderControls(aRequirement(), {
      attachments: [
        { id: "a1", type: "MUSIC", fileReference: "/media/x/Катюша.mp3", caption: null },
      ],
    } as unknown as SubmissionResource);

    expect(screen.getByRole("button", { name: "Добавить ещё" })).toBeInTheDocument();
    expect(screen.getByText("Катюша.mp3")).toBeInTheDocument();
  });

  it("names the limit when the server is the one that refuses", async () => {
    upload.mockRejectedValue(new ApiError("File too large", { status: 413 }));
    renderControls();

    await userEvent.upload(screen.getByLabelText(MUSIC_LABEL), aFile("track.mp3", 3 * 1024 * 1024));

    await waitFor(() =>
      expect(toast.error).toHaveBeenCalledWith(
        "track.mp3: Файл слишком большой. Допустимо до 25 МБ.",
      ),
    );
  });

  it("says what format is wanted when the type is refused", async () => {
    upload.mockRejectedValue(new ApiError("Unsupported", { status: 415 }));
    renderControls();

    await userEvent.upload(screen.getByLabelText(MUSIC_LABEL), aFile("track.mp3", 1024));

    await waitFor(() =>
      expect(toast.error).toHaveBeenCalledWith(
        `track.mp3: Такой формат файла не принимается. Нужен: ${MUSIC_HINT}`,
      ),
    );
  });

  it("falls back to a plain message for an unexpected failure", async () => {
    upload.mockRejectedValue(new Error("network down"));
    renderControls();

    await userEvent.upload(screen.getByLabelText(MUSIC_LABEL), aFile("track.mp3", 1024));

    await waitFor(() =>
      expect(toast.error).toHaveBeenCalledWith(`track.mp3: Не удалось загрузить: ${MUSIC_LABEL}`),
    );
  });

  it("refuses a video over the organizer's limit before uploading it", async () => {
    // The point of stating the limit client-side: a 300 MB file on a phone connection
    // must not be sent only to be refused at the end of it.
    renderControls(
      aRequirement({
        musicRequired: false,
        musicAllowedFormats: [],
        videoMode: "FILE_ONLY",
        videoMaxUploadSizeMb: 200,
      }),
    );

    await userEvent.upload(
      screen.getByLabelText("Видео (обязательно)"),
      aFile("clip.mp4", 300 * 1024 * 1024, "video/mp4"),
    );

    await waitFor(() => expect(toast.error).toHaveBeenCalled());
    expect(upload).not.toHaveBeenCalled();
  });

  it("uploads a video within the limit", async () => {
    renderControls(
      aRequirement({
        musicRequired: false,
        musicAllowedFormats: [],
        videoMode: "FILE_ONLY",
        videoMaxUploadSizeMb: 200,
      }),
    );

    await userEvent.upload(
      screen.getByLabelText("Видео (обязательно)"),
      aFile("clip.mp4", 5 * 1024 * 1024, "video/mp4"),
    );

    await waitFor(() => expect(upload).toHaveBeenCalled());
  });

  it("states the organizer's own formats and limit in the hint", async () => {
    renderControls(
      aRequirement({
        musicRequired: false,
        musicAllowedFormats: [],
        videoMode: "URL_OR_FILE",
        videoAllowedFormats: ["mp4", "webm"],
        videoMaxUploadSizeMb: 120,
      }),
    );

    expect(screen.getByText("mp4, webm · до 120 МБ")).toBeInTheDocument();
  });
});
