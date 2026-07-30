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
    receiptRequired: false,
    ...overrides,
  } as RegistrationUploadRequirement;
}

const EMPTY_SUBMISSION = { attachments: [] } as unknown as SubmissionResource;

/** A File of a given size without allocating the bytes. */
function aFile(name: string, sizeBytes: number, type = "audio/mpeg"): File {
  const file = new File(["x"], name, { type });
  Object.defineProperty(file, "size", { value: sizeBytes });
  return file;
}

beforeEach(() => {
  vi.clearAllMocks();
  vi.mocked(useUploadAttachment).mockReturnValue({
    mutate: upload,
    isPending: false,
  } as unknown as ReturnType<typeof useUploadAttachment>);
  vi.mocked(useRemoveAttachment).mockReturnValue({
    mutate: vi.fn(),
    isPending: false,
  } as unknown as ReturnType<typeof useRemoveAttachment>);
});

function renderControls(requirement = aRequirement()) {
  return render(
    <UploadControls
      submissionId={SUBMISSION_ID}
      submission={EMPTY_SUBMISSION}
      requirement={requirement}
    />,
  );
}

describe("UploadControls", () => {
  it("refuses an oversized file before it is sent", async () => {
    renderControls();

    await userEvent.upload(
      screen.getByLabelText("Фонограмма (обязательно)"),
      aFile("track.mp3", 42 * 1024 * 1024),
    );

    expect(upload).not.toHaveBeenCalled();
    expect(toast.error).toHaveBeenCalledWith("Файл 42 МБ, а допустимо до 25 МБ");
  });

  it("sends a file that fits", async () => {
    renderControls();

    await userEvent.upload(
      screen.getByLabelText("Фонограмма (обязательно)"),
      aFile("track.mp3", 3 * 1024 * 1024),
    );

    await waitFor(() => expect(upload).toHaveBeenCalled());
    expect(toast.error).not.toHaveBeenCalled();
  });

  it("names the limit when the server is the one that refuses", async () => {
    upload.mockImplementation((_input, handlers) => {
      handlers.onError(new ApiError("File too large", { status: 413 }));
    });
    renderControls();

    await userEvent.upload(
      screen.getByLabelText("Фонограмма (обязательно)"),
      aFile("track.mp3", 3 * 1024 * 1024),
    );

    await waitFor(() =>
      expect(toast.error).toHaveBeenCalledWith("Файл слишком большой. Допустимо до 25 МБ."),
    );
  });

  it("says what format is wanted when the type is refused", async () => {
    upload.mockImplementation((_input, handlers) => {
      handlers.onError(new ApiError("Unsupported", { status: 415 }));
    });
    renderControls();

    await userEvent.upload(
      screen.getByLabelText("Фонограмма (обязательно)"),
      aFile("track.mp3", 1024),
    );

    await waitFor(() =>
      expect(toast.error).toHaveBeenCalledWith(
        "Такой формат файла не принимается. Нужен: mp3, wav · до 25 МБ",
      ),
    );
  });

  it("falls back to a plain message for an unexpected failure", async () => {
    upload.mockImplementation((_input, handlers) => {
      handlers.onError(new Error("network down"));
    });
    renderControls();

    await userEvent.upload(
      screen.getByLabelText("Фонограмма (обязательно)"),
      aFile("track.mp3", 1024),
    );

    await waitFor(() =>
      expect(toast.error).toHaveBeenCalledWith("Не удалось загрузить: Фонограмма (обязательно)"),
    );
  });

  it("lets a video through unchecked, since the client is not told its limit", async () => {
    renderControls(
      aRequirement({ musicRequired: false, musicAllowedFormats: [], videoMode: "FILE_ONLY" }),
    );

    await userEvent.upload(
      screen.getByLabelText("Видео"),
      aFile("clip.mp4", 300 * 1024 * 1024, "video/mp4"),
    );

    await waitFor(() => expect(upload).toHaveBeenCalled());
  });
});
