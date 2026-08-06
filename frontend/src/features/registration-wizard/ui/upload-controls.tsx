import { useRef } from "react";

import { ApiError } from "@/shared/api";
import type { SubmissionResource } from "@/shared/api/generated/model-applications";
import type { RegistrationUploadRequirement } from "@/shared/api/generated/model-public-catalog";
import { Badge, Button, toast } from "@/shared/ui";

import { useRemoveAttachment, useUploadAttachment } from "../api/hooks";

const BYTES_PER_MB = 1024 * 1024;

/** The attachment types the wire knows; a row may cover more than one. */
type AttachmentKind = "MUSIC" | "VIDEO" | "IMAGE";

type UploadKind = {
  /** Row identity, and the type single-type rows upload as. */
  id: "MUSIC" | "MEDIA";
  /**
   * The attachment types this row owns — what it lists, and what counts toward its
   * limit. Media covers video and photographs together, because the organizer
   * configured one ceiling over both.
   */
  types: readonly AttachmentKind[];
  label: string;
  hint: string;
  accept: string;
  /**
   * Whether an act can bring more than one file.
   *
   * A number is not always performed to a single track — a backing track plus a fanfare,
   * a two-part routine — and photographs come in handfuls, so both rows take several.
   */
  multiple: boolean;
  /** The server's limit, when the projection tells the client what it is. */
  maxBytes?: number;
  /**
   * Whether ``maxBytes`` bounds the sum of the row's files rather than each of them.
   *
   * Media is a shared budget: several photographs and a video are the normal case, and a
   * per-file limit would either wave ten of them through or refuse one legitimate one.
   */
  sharedBudget?: boolean;
};

/** Photographs, by extension — everything else in a media row travels as video. */
const IMAGE_EXTENSIONS = new Set(["jpg", "jpeg", "png", "webp", "heic", "heif"]);

/** Which attachment type a chosen file becomes. */
function attachmentTypeFor(kind: UploadKind, file: File): AttachmentKind {
  if (kind.id === "MUSIC") {
    return "MUSIC";
  }
  const extension = file.name.split(".").pop()?.toLowerCase() ?? "";
  return IMAGE_EXTENSIONS.has(extension) ? "IMAGE" : "VIDEO";
}

/** A file size a person reads, rounded the way a file manager would show it. */
function megabytes(bytes: number): string {
  return `${(bytes / BYTES_PER_MB).toFixed(1).replace(".0", "")} МБ`;
}

/** The last segment of a stored file reference — what the applicant recognises. */
function fileName(reference: string): string {
  return decodeURIComponent(reference.split("/").pop() || reference);
}

/**
 * Why the server refused an upload, in the applicant's language.
 *
 * The backend answers a rejected upload with a Problem Detail whose message is
 * precise but English and byte-counted ("the maximum for MUSIC is 26214400
 * bytes"). Showing "Не удалось загрузить" instead threw that away and left the
 * applicant guessing at a file that looked perfectly fine to them.
 */
function refusalMessage(error: unknown, kind: UploadKind): string {
  const status = error instanceof ApiError ? error.status : 0;
  if (status === 413) {
    const limit = kind.maxBytes ? ` Допустимо до ${megabytes(kind.maxBytes)}.` : "";
    return `Файл слишком большой.${limit}`;
  }
  if (status === 415) {
    return `Такой формат файла не принимается. Нужен: ${kind.hint}`;
  }
  if (status === 409 || status === 422) {
    return `Загрузка сейчас недоступна: ${kind.label.toLowerCase()}`;
  }
  return `Не удалось загрузить: ${kind.label}`;
}

/** Which upload controls to show for a format, per its upload requirement. */
function uploadKinds(requirement: RegistrationUploadRequirement | undefined): UploadKind[] {
  if (!requirement) {
    return [];
  }
  const kinds: UploadKind[] = [];
  if (requirement.musicRequired || requirement.musicAllowedFormats.length > 0) {
    kinds.push({
      id: "MUSIC",
      types: ["MUSIC"],
      label: requirement.musicRequired ? "Фонограммы (обязательно)" : "Фонограммы",
      hint: `${requirement.musicAllowedFormats.join(", ")} · до ${requirement.musicMaxUploadSizeMb} МБ за файл · можно несколько`,
      accept: requirement.musicAllowedFormats.map((ext) => `.${ext}`).join(",") || "audio/*",
      multiple: true,
      maxBytes: requirement.musicMaxUploadSizeMb * BYTES_PER_MB,
    });
  }
  if (requirement.mediaMode === "FILE_ONLY" || requirement.mediaMode === "URL_OR_FILE") {
    // One row for video and photographs, on the organizer's own limits, and the limit is
    // stated here so an oversized selection is refused before it is sent: an upload that
    // only fails at the end costs the applicant the whole wait, and on a phone that is the
    // difference between entering the festival and giving up.
    kinds.push({
      id: "MEDIA",
      types: ["VIDEO", "IMAGE"],
      // Whether it is demanded is its own setting: a festival may collect files for the
      // hall's screen without turning an entry away for their absence.
      label: requirement.mediaRequired ? "Медиа (обязательно)" : "Медиа",
      hint: `${requirement.mediaAllowedFormats.join(", ")} · суммарно до ${requirement.mediaMaxTotalSizeMb} МБ`,
      accept:
        requirement.mediaAllowedFormats.map((ext) => `.${ext}`).join(",") || "video/*,image/*",
      multiple: true,
      maxBytes: requirement.mediaMaxTotalSizeMb * BYTES_PER_MB,
      sharedBudget: true,
    });
  }
  // The payment receipt is no longer a per-performance upload: it proves payment of
  // the whole order and is uploaded once on the application card after submission.
  return kinds;
}

function UploadRow({
  submissionId,
  kind,
  submission,
}: {
  submissionId: string;
  kind: UploadKind;
  submission: SubmissionResource;
}): React.JSX.Element {
  const inputRef = useRef<HTMLInputElement>(null);
  const upload = useUploadAttachment(submissionId);
  const remove = useRemoveAttachment(submissionId);
  const existing = submission.attachments.filter((attachment) =>
    kind.types.includes(attachment.type as AttachmentKind),
  );
  // What the shared ceiling is measured against. A zero size is an attachment stored
  // before sizes were tracked: counted as nothing here, and the server still has the
  // final word.
  const attachedBytes = existing.reduce(
    (total, attachment) => total + ((attachment as { sizeBytes?: number }).sizeBytes ?? 0),
    0,
  );

  const clearInput = () => {
    if (inputRef.current) {
      inputRef.current.value = "";
    }
  };

  /**
   * Upload every chosen file, one after the other.
   *
   * Sequential on purpose, never in parallel: the submission is one aggregate behind
   * an optimistic version check, so two uploads racing on it would have the second
   * rejected as a concurrent modification and silently lose that track.
   */
  const onFilesChosen = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const files = [...(event.target.files ?? [])];
    if (files.length === 0) {
      return;
    }
    // Grows as this selection is accepted, so ten files chosen at once are measured
    // against the same budget the server will apply — not each against the whole of it.
    let budgetUsed = attachedBytes;
    for (const file of files) {
      // Refused here rather than after the upload: sending a file the server is
      // certain to reject costs the applicant the whole wait on a slow connection,
      // and the limit is already known from the competition's own requirements.
      if (kind.maxBytes != null) {
        const wouldUse = kind.sharedBudget === true ? budgetUsed + file.size : file.size;
        if (wouldUse > kind.maxBytes) {
          toast.error(
            kind.sharedBudget === true
              ? `${file.name}: не помещается — уже занято ${megabytes(budgetUsed)} из ${megabytes(kind.maxBytes)}`
              : `${file.name}: ${megabytes(file.size)}, а допустимо до ${megabytes(kind.maxBytes)}`,
          );
          continue;
        }
      }
      try {
        await upload.mutateAsync({ file, attachmentType: attachmentTypeFor(kind, file) });
        budgetUsed += file.size;
      } catch (error) {
        // One bad file must not abandon the rest of the selection.
        toast.error(`${file.name}: ${refusalMessage(error, kind)}`);
      }
    }
    clearInput();
  };

  const addLabel =
    existing.length === 0 ? "Загрузить" : kind.multiple ? "Добавить ещё" : "Заменить";

  return (
    <div className="flex flex-col gap-2 rounded-md border border-border p-3">
      <div className="flex items-center justify-between gap-2">
        <div>
          <p className="text-sm font-medium">{kind.label}</p>
          <p className="text-xs text-muted-foreground">{kind.hint}</p>
        </div>
        <Button
          variant="outline"
          size="sm"
          loading={upload.isPending}
          onClick={() => inputRef.current?.click()}
        >
          {addLabel}
        </Button>
      </div>
      {existing.length === 0 ? (
        <p className="text-xs text-muted-foreground">Файл не выбран</p>
      ) : null}
      {existing.map((attachment) => (
        <div key={attachment.id} className="flex items-center justify-between gap-2">
          <Badge variant="success" className="min-w-0">
            <span className="truncate">
              {attachment.caption || fileName(attachment.fileReference)}
            </span>
          </Badge>
          <Button
            variant="ghost"
            size="xs"
            loading={remove.isPending}
            onClick={() => remove.mutate(attachment.id)}
          >
            Удалить
          </Button>
        </div>
      ))}
      <input
        ref={inputRef}
        type="file"
        accept={kind.accept}
        multiple={kind.multiple}
        className="hidden"
        aria-label={kind.label}
        onChange={(event) => void onFilesChosen(event)}
      />
    </div>
  );
}

/** Render the upload controls required for the submission's selected format. */
export function UploadControls({
  submissionId,
  submission,
  requirement,
}: {
  submissionId: string;
  submission: SubmissionResource;
  requirement: RegistrationUploadRequirement | undefined;
}): React.JSX.Element {
  const kinds = uploadKinds(requirement);
  if (kinds.length === 0) {
    return (
      <p className="text-sm text-muted-foreground">
        Для выбранного формата загрузка файлов не требуется.
      </p>
    );
  }
  return (
    <div className="flex flex-col gap-3">
      {kinds.map((kind) => (
        <UploadRow key={kind.id} submissionId={submissionId} kind={kind} submission={submission} />
      ))}
    </div>
  );
}
