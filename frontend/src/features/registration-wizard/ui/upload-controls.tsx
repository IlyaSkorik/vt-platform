import { useRef } from "react";

import { ApiError } from "@/shared/api";
import type { SubmissionResource } from "@/shared/api/generated/model-applications";
import type { RegistrationUploadRequirement } from "@/shared/api/generated/model-public-catalog";
import { Badge, Button, toast } from "@/shared/ui";

import { useRemoveAttachment, useUploadAttachment } from "../api/hooks";

const BYTES_PER_MB = 1024 * 1024;

type UploadKind = {
  attachmentType: "MUSIC" | "VIDEO";
  label: string;
  hint: string;
  accept: string;
  /**
   * Whether an act can bring more than one file of this kind.
   *
   * A number is not always performed to a single track — a backing track plus a
   * fanfare, a two-part routine, a separate soundcheck cut — and the sound desk is
   * handed all of them. A video is one recording of one performance.
   */
  multiple: boolean;
  /** The server's size limit, when the projection tells the client what it is. */
  maxBytes?: number;
};

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
      attachmentType: "MUSIC",
      label: requirement.musicRequired ? "Фонограммы (обязательно)" : "Фонограммы",
      hint: `${requirement.musicAllowedFormats.join(", ")} · до ${requirement.musicMaxUploadSizeMb} МБ за файл · можно несколько`,
      accept: requirement.musicAllowedFormats.map((ext) => `.${ext}`).join(",") || "audio/*",
      multiple: true,
      maxBytes: requirement.musicMaxUploadSizeMb * BYTES_PER_MB,
    });
  }
  if (requirement.videoMode === "FILE_ONLY" || requirement.videoMode === "URL_OR_FILE") {
    // The organizer's own limits now travel in the projection, so the control states
    // them and refuses an oversized file before it is uploaded — a 300 MB video that
    // only fails after the upload wastes the applicant's connection, and on a phone
    // that is the difference between entering the festival and giving up.
    kinds.push({
      attachmentType: "VIDEO",
      label: requirement.videoMode === "FILE_ONLY" ? "Видео (обязательно)" : "Видео",
      hint: `${requirement.videoAllowedFormats.join(", ")} · до ${requirement.videoMaxUploadSizeMb} МБ`,
      accept: requirement.videoAllowedFormats.map((ext) => `.${ext}`).join(",") || "video/*",
      multiple: false,
      maxBytes: requirement.videoMaxUploadSizeMb * BYTES_PER_MB,
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
  const existing = submission.attachments.filter(
    (attachment) => attachment.type === kind.attachmentType,
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
    for (const file of files) {
      // Refused here rather than after the upload: sending a file the server is
      // certain to reject costs the applicant the whole wait on a slow connection,
      // and the limit is already known from the competition's own requirements.
      if (kind.maxBytes != null && file.size > kind.maxBytes) {
        toast.error(
          `${file.name}: ${megabytes(file.size)}, а допустимо до ${megabytes(kind.maxBytes)}`,
        );
        continue;
      }
      try {
        await upload.mutateAsync({ file, attachmentType: kind.attachmentType });
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
        <UploadRow
          key={kind.attachmentType}
          submissionId={submissionId}
          kind={kind}
          submission={submission}
        />
      ))}
    </div>
  );
}
