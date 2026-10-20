import { Film, Trash2 } from "lucide-react";
import { useRef } from "react";

import {
  acceptsFiles,
  fileWindowClosedReason,
  useRegistration,
  useRemoveSubmissionAttachment,
  useSubmissionDetail,
  useUploadSubmissionAttachment,
} from "@/entities/application";
import { ApiError } from "@/shared/api";
import type {
  _SubmissionRef,
  ApplicationResource,
} from "@/shared/api/generated/model-applications";
import type {
  Registration,
  RegistrationUploadRequirement,
} from "@/shared/api/generated/model-public-catalog";
import {
  Alert,
  Badge,
  Button,
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
  Divider,
  toast,
} from "@/shared/ui";

const BYTES_PER_MB = 1024 * 1024;

/** Photographs, by extension — everything else in a media selection is video. */
const IMAGE_EXTENSIONS = new Set(["jpg", "jpeg", "png", "webp", "heic", "heif"]);

/** Which attachment kind a chosen file becomes. Same rule as the wizard's media row. */
function mediaKindOf(file: File): "IMAGE" | "VIDEO" {
  const extension = file.name.split(".").pop()?.toLowerCase() ?? "";
  return IMAGE_EXTENSIONS.has(extension) ? "IMAGE" : "VIDEO";
}

/** Whether this festival collects media as files at all for the given format. */
function takesFiles(requirement: RegistrationUploadRequirement | undefined): boolean {
  return requirement?.mediaMode === "FILE_ONLY" || requirement?.mediaMode === "URL_OR_FILE";
}

function megabytes(bytes: number): string {
  return `${(bytes / BYTES_PER_MB).toFixed(1).replace(".0", "")} МБ`;
}

/** The last segment of a stored file reference — what the applicant recognises. */
function fileName(reference: string): string {
  return decodeURIComponent(reference.split("/").pop() || reference);
}

/** Why the server refused an upload, in the applicant's language. */
function refusalMessage(error: unknown, hint: string, maxBytes: number | undefined): string {
  const status = error instanceof ApiError ? error.status : 0;
  if (status === 413) {
    return `Не помещается в общий лимит.${maxBytes ? ` На видео и фото вместе — ${megabytes(maxBytes)}.` : ""}`;
  }
  if (status === 415) {
    return `Такой формат файла не принимается. Нужен: ${hint}`;
  }
  if (status === 409 || status === 422) {
    // The server owns the rule and may know something the projection did not when
    // this screen loaded — a deadline that passed while it was open, or a freeze.
    return "Загрузка файлов сейчас закрыта";
  }
  return "Не удалось загрузить файл";
}

/**
 * The video and photographs of one performance: what is attached, and a way to add more.
 *
 * Per submission rather than per order, like the phonograms beside it: the material
 * belongs to the act, and an order of three numbers has three sets of it.
 */
function PerformanceMedia({
  reference,
  registration,
}: {
  reference: _SubmissionRef;
  registration: Registration | undefined;
}): React.JSX.Element | null {
  const { data: submission } = useSubmissionDetail(reference.submissionId);
  const upload = useUploadSubmissionAttachment(reference.submissionId);
  const remove = useRemoveSubmissionAttachment(reference.submissionId);
  const inputRef = useRef<HTMLInputElement>(null);

  const files = (submission?.attachments ?? []).filter(
    (attachment) => attachment.type === "VIDEO" || attachment.type === "IMAGE",
  );
  const requirement = (registration?.uploadRequirements ?? []).find(
    (entry) => entry.participationFormatId === submission?.performance?.participationFormatId,
  );
  const closed = fileWindowClosedReason(registration, "media");
  const canEdit = acceptsFiles(reference.status) && closed === null;

  if (!takesFiles(requirement) && files.length === 0) {
    // A festival that collects no media has no card to show, and one that collects it
    // only as a link has nothing to upload here.
    return null;
  }

  const formats = requirement?.mediaAllowedFormats ?? [];
  // A shared ceiling over video and photographs together — the organizer configured one
  // budget for both, so the only honest check before sending is against what is already
  // attached. Without it an applicant on a phone waits out the whole upload for a 413.
  const maxBytes = requirement ? requirement.mediaMaxTotalSizeMb * BYTES_PER_MB : undefined;
  // A zero size is an attachment stored before sizes were tracked — counted as nothing,
  // and the server still has the final word. The cast is the wizard's: the attachments
  // contract omits the field the API does send.
  const attached = files.reduce(
    (sum, file) => sum + ((file as { sizeBytes?: number }).sizeBytes ?? 0),
    0,
  );
  const hint = requirement
    ? `${formats.join(", ")} · суммарно до ${requirement.mediaMaxTotalSizeMb} МБ`
    : "видео или фотография";
  const accept = formats.length > 0 ? formats.map((ext) => `.${ext}`).join(",") : "video/*,image/*";

  /**
   * Upload every chosen file, one after the other.
   *
   * Sequential, never in parallel: the submission is one aggregate behind an optimistic
   * version check, so two uploads racing on it would have the second rejected as a
   * concurrent modification and silently lose that file.
   */
  const onFilesChosen = async (event: React.ChangeEvent<HTMLInputElement>) => {
    let budgetLeft = maxBytes != null ? maxBytes - attached : Number.POSITIVE_INFINITY;
    for (const file of [...(event.target.files ?? [])]) {
      if (file.size > budgetLeft) {
        toast.error(
          `${file.name}: ${megabytes(file.size)} — остаётся ${megabytes(Math.max(0, budgetLeft))}`,
        );
        continue;
      }
      try {
        await upload.mutateAsync({ file, attachmentType: mediaKindOf(file) });
        budgetLeft -= file.size;
        toast.success(`${file.name} — загружено`);
      } catch (error) {
        // One bad file must not abandon the rest of the selection.
        toast.error(`${file.name}: ${refusalMessage(error, hint, maxBytes)}`);
      }
    }
    if (inputRef.current) {
      inputRef.current.value = "";
    }
  };

  return (
    <div className="flex flex-col gap-2">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div className="min-w-0">
          <p className="truncate font-medium text-sm">
            {reference.performanceTitle || "Без названия"}
          </p>
          <p className="text-xs text-muted-foreground">{hint}</p>
        </div>
        {canEdit && takesFiles(requirement) ? (
          <Button
            variant="outline"
            size="sm"
            loading={upload.isPending}
            onClick={() => inputRef.current?.click()}
          >
            <Film className="size-4" />
            {files.length === 0 ? "Загрузить файлы" : "Добавить ещё"}
          </Button>
        ) : null}
      </div>

      {files.length === 0 ? (
        <p className="text-xs text-muted-foreground">Видео и фотографии не приложены.</p>
      ) : (
        <ul className="flex flex-col gap-2">
          {files.map((file) => (
            <li
              key={file.id}
              className="flex items-center justify-between gap-3 rounded-md border border-border px-3 py-2"
            >
              <div className="flex min-w-0 items-center gap-2">
                <Badge variant="secondary">{file.type === "IMAGE" ? "фото" : "видео"}</Badge>
                <span className="truncate text-sm">
                  {file.caption?.trim() || fileName(file.fileReference)}
                </span>
              </div>
              {canEdit ? (
                <Button
                  variant="ghost"
                  size="sm"
                  loading={remove.isPending}
                  onClick={() =>
                    remove.mutate(file.id, {
                      onSuccess: () => toast.success("Файл удалён"),
                      onError: () => toast.error("Не удалось удалить файл"),
                    })
                  }
                >
                  <Trash2 className="size-4" />
                </Button>
              ) : null}
            </li>
          ))}
        </ul>
      )}

      <input
        ref={inputRef}
        type="file"
        accept={accept}
        multiple
        className="hidden"
        aria-label={`Видео и фото: ${reference.performanceTitle || "выступление"}`}
        onChange={(event) => void onFilesChosen(event)}
      />
    </div>
  );
}

/**
 * The order's video and photographs, one block per performance.
 *
 * On the application card, beside the phonograms, and for the same reason: the material
 * of an act is replaced long after the entry itself is settled — a better take is filmed,
 * the right photograph is found — and the registration wizard is over by then. Until this
 * card existed those files lived only inside the wizard's editing screen, which closes
 * with the registration, so «перезалить видео» meant writing to the organizer.
 */
export function MediaCard({
  application,
}: {
  application: ApplicationResource;
}): React.JSX.Element | null {
  const { data: registration } = useRegistration(application.competitionId);
  const closed = fileWindowClosedReason(registration, "media");

  if (application.submissions.length === 0) {
    return null;
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>Видео и фото</CardTitle>
        <CardDescription>
          Материал выступления: запись номера и фотографии. Один лимит на видео и фото вместе —
          организатор назначает его на каждый номер.
        </CardDescription>
      </CardHeader>
      <CardContent className="flex flex-col gap-4">
        {closed ? <Alert variant="info">{closed}</Alert> : null}
        {application.submissions.map((reference, index) => (
          <div key={reference.submissionId} className="flex flex-col gap-4">
            {index > 0 ? <Divider /> : null}
            <PerformanceMedia reference={reference} registration={registration} />
          </div>
        ))}
      </CardContent>
    </Card>
  );
}
