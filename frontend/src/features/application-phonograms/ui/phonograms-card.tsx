import { Music, Trash2 } from "lucide-react";
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
import type { RegistrationUploadRequirement } from "@/shared/api/generated/model-public-catalog";
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

/** The last segment of a stored file reference — what the applicant recognises. */
function fileName(reference: string): string {
  return decodeURIComponent(reference.split("/").pop() || reference);
}

function megabytes(bytes: number): string {
  return `${(bytes / BYTES_PER_MB).toFixed(1).replace(".0", "")} МБ`;
}

/** Why the server refused an upload, in the applicant's language. */
function refusalMessage(error: unknown, hint: string, maxBytes: number | undefined): string {
  const status = error instanceof ApiError ? error.status : 0;
  if (status === 413) {
    return `Файл слишком большой.${maxBytes ? ` Допустимо до ${megabytes(maxBytes)}.` : ""}`;
  }
  if (status === 415) {
    return `Такой формат файла не принимается. Нужен: ${hint}`;
  }
  if (status === 409 || status === 422) {
    return "Загрузка фонограмм для этого конкурса сейчас закрыта";
  }
  return "Не удалось загрузить фонограмму";
}

/**
 * The phonograms of one performance: what is attached, and a way to attach more.
 *
 * Its own component because the files hang off the *submission*, not the order — each
 * number is performed to its own music — and each one needs its own queries.
 */
function PerformancePhonograms({
  reference,
  requirements,
  closed,
  explain,
}: {
  reference: _SubmissionRef;
  requirements: RegistrationUploadRequirement[];
  /** Why the window is shut, or ``null`` while a track may still be sent. */
  closed: string | null;
  /**
   * Whether this row says the reason itself.
   *
   * ``false`` when every number of the order gives the same answer and the card has
   * already said it once above the list. Separate from ``closed`` because the two
   * are different questions: whether the controls are offered is never "already
   * mentioned", and conflating them is how the buttons came back on a frozen genre.
   */
  explain: boolean;
}): React.JSX.Element {
  const { data: submission } = useSubmissionDetail(reference.submissionId);
  const upload = useUploadSubmissionAttachment(reference.submissionId);
  const remove = useRemoveSubmissionAttachment(reference.submissionId);
  const inputRef = useRef<HTMLInputElement>(null);

  const tracks = (submission?.attachments ?? []).filter(
    (attachment) => attachment.type === "MUSIC",
  );
  const canEdit = acceptsFiles(reference.status) && closed === null;
  const requirement = requirements.find(
    (entry) => entry.participationFormatId === submission?.performance?.participationFormatId,
  );
  const formats = requirement?.musicAllowedFormats ?? [];
  const maxBytes = requirement ? requirement.musicMaxUploadSizeMb * BYTES_PER_MB : undefined;
  const hint = requirement
    ? `${formats.join(", ")} · до ${requirement.musicMaxUploadSizeMb} МБ за файл`
    : "аудиофайл";
  const accept = formats.length > 0 ? formats.map((ext) => `.${ext}`).join(",") : "audio/*";

  /**
   * Upload every chosen file, one after the other.
   *
   * Sequential, never in parallel: the submission is one aggregate behind an optimistic
   * version check, so two uploads racing on it would have the second rejected as a
   * concurrent modification and silently lose that track.
   */
  const onFilesChosen = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const files = [...(event.target.files ?? [])];
    for (const file of files) {
      if (maxBytes != null && file.size > maxBytes) {
        toast.error(`${file.name}: ${megabytes(file.size)}, а допустимо до ${megabytes(maxBytes)}`);
        continue;
      }
      try {
        await upload.mutateAsync({ file, attachmentType: "MUSIC" });
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

  const inputLabel = `Фонограммы: ${reference.performanceTitle || "выступление"}`;

  return (
    <div className="flex flex-col gap-2">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div className="min-w-0">
          <p className="truncate font-medium text-sm">
            {reference.performanceTitle || "Без названия"}
          </p>
          <p className="text-xs text-muted-foreground">{hint}</p>
          {/* Под своим номером, а не общей плашкой: сюда попадают только причины,
              которые у номеров разные — иначе карточка сказала бы это один раз. */}
          {explain && closed ? <p className="text-xs text-muted-foreground">{closed}</p> : null}
        </div>
        {canEdit ? (
          <Button
            variant="outline"
            size="sm"
            loading={upload.isPending}
            onClick={() => inputRef.current?.click()}
          >
            <Music className="size-4" />
            {tracks.length === 0 ? "Загрузить фонограмму" : "Добавить ещё"}
          </Button>
        ) : null}
      </div>

      {tracks.length === 0 ? (
        <p className="text-xs text-muted-foreground">Фонограммы не приложены.</p>
      ) : (
        <ul className="flex flex-col gap-2">
          {tracks.map((track, index) => (
            <li
              key={track.id}
              className="flex items-center justify-between gap-3 rounded-md border border-border px-3 py-2"
            >
              <div className="flex min-w-0 items-center gap-2">
                {/* Numbered: an act performed to several tracks is performed to them
                    in an order, and the sound desk plays them in the order shown. */}
                <Badge variant="secondary">{index + 1}</Badge>
                <span className="truncate text-sm">
                  {track.caption?.trim() || fileName(track.fileReference)}
                </span>
              </div>
              {canEdit ? (
                <Button
                  variant="ghost"
                  size="sm"
                  loading={remove.isPending}
                  onClick={() =>
                    remove.mutate(track.id, {
                      onSuccess: () => toast.success("Фонограмма удалена"),
                      onError: () => toast.error("Не удалось удалить фонограмму"),
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
        aria-label={inputLabel}
        onChange={(event) => void onFilesChosen(event)}
      />
    </div>
  );
}

/**
 * The order's phonograms, one block per performance.
 *
 * Lives on the application card rather than only in the registration wizard because a
 * track arrives late: the entry is submitted, accepted and given a slot long before
 * anybody has settled which cut is being danced to. This is the screen an applicant
 * comes back to, and the organizer's programme archive is assembled from exactly these
 * files.
 */
export function PhonogramsCard({
  application,
}: {
  application: ApplicationResource;
}): React.JSX.Element | null {
  const { data: registration } = useRegistration(application.competitionId);
  // Per entry, not once above the list: the freeze is a genre's now, so two numbers
  // of the same order legitimately differ. Said once only when every number gives
  // the same answer — otherwise it is the same sentence three times, which was the
  // reason it used to live above the list.
  const reasons = application.submissions.map((reference) =>
    fileWindowClosedReason(registration, "music", reference.nominationId),
  );
  const shared = reasons.every((reason) => reason !== null && reason === reasons[0])
    ? reasons[0]
    : null;

  if (application.submissions.length === 0) {
    return null;
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>Фонограммы</CardTitle>
        <CardDescription>
          Музыка, под которую исполняется номер. К одному выступлению можно приложить несколько
          файлов — они попадут к звукорежиссёру в том же порядке.
        </CardDescription>
      </CardHeader>
      <CardContent className="flex flex-col gap-4">
        {shared ? <Alert variant="info">{shared}</Alert> : null}
        {application.submissions.map((reference, index) => (
          <div key={reference.submissionId} className="flex flex-col gap-4">
            {index > 0 ? <Divider /> : null}
            <PerformancePhonograms
              reference={reference}
              requirements={registration?.uploadRequirements ?? []}
              closed={reasons[index] ?? null}
              explain={shared === null}
            />
          </div>
        ))}
      </CardContent>
    </Card>
  );
}
