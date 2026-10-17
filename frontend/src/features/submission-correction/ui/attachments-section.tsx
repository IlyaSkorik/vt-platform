/**
 * Файлы номера в форме исправления — те, что организатор догружает за участника.
 *
 * Зачем это здесь. Фонограмма доезжает до фестиваля как угодно: сообщением ночью,
 * флешкой на репетиции, письмом утром — то есть мимо формы и после того, как приём
 * закрылся. До сих пор это кончалось просьбой «зайдите в кабинет и загрузите сами»:
 * участнику — искать заявку, организатору — ждать, звукорежиссёру — тоже.
 *
 * Показывается ровно то, что фестиваль просил у участника по этой форме участия:
 * просили фонограммы — есть строка фонограмм, просили медиа — есть медиа. Ничего
 * сверх того: организатор догружает за участника, а не открывает себе отдельный
 * склад. Форма участия, по которой файлов не просили вовсе, не даёт здесь ни строки.
 *
 * Файлы сохраняются сразу, в отличие от остальной формы: загрузка — это и есть
 * действие, откладывать её до «Сохранить» значило бы держать байты в вкладке.
 */
import { useRef } from "react";

import { resolveMediaUrl } from "@/shared/lib";
import { Button, toast } from "@/shared/ui";

import {
  type CorrectableAttachment,
  type CorrectableUploadRequirement,
  useOrganizerRemoveAttachment,
  useOrganizerUploadAttachment,
} from "../api/hooks";

const BYTES_PER_MB = 1024 * 1024;

/** Типы вложений, которыми живёт эта форма; одна строка может держать несколько. */
type AttachmentKind = "MUSIC" | "VIDEO" | "IMAGE";

type UploadRow = {
  id: "MUSIC" | "MEDIA";
  /** Какие типы строка показывает и чем считает занятый объём. */
  types: readonly AttachmentKind[];
  label: string;
  hint: string;
  accept: string;
  maxBytes: number;
  /** Медиа делят один лимит на всё: несколько фото и видео — обычный случай. */
  sharedBudget: boolean;
};

/** Фотографии — по расширению; всё остальное в медиастроке едет как видео. */
const IMAGE_EXTENSIONS = new Set(["jpg", "jpeg", "png", "webp", "heic", "heif"]);

function attachmentTypeFor(row: UploadRow, file: File): AttachmentKind {
  if (row.id === "MUSIC") {
    return "MUSIC";
  }
  const extension = file.name.split(".").pop()?.toLowerCase() ?? "";
  return IMAGE_EXTENSIONS.has(extension) ? "IMAGE" : "VIDEO";
}

function megabytes(bytes: number): string {
  return `${(bytes / BYTES_PER_MB).toFixed(1).replace(".0", "")} МБ`;
}

/** Последний сегмент ссылки на файл — то, что организатор по нему и узнаёт. */
function fileName(reference: string): string {
  return decodeURIComponent(reference.split("/").pop() || reference);
}

/**
 * Какие строки загрузки показать — по тому же правилу, что и в мастере подачи.
 *
 * Ровно те, что видел участник: иначе организатор догрузил бы к номеру то, чего
 * фестиваль по нему не просил и, возможно, не ждёт ни на одном рабочем месте.
 */
export function uploadRows(
  requirement: CorrectableUploadRequirement | null | undefined,
): UploadRow[] {
  if (!requirement) {
    return [];
  }
  const rows: UploadRow[] = [];
  if (requirement.musicRequired || requirement.musicAllowedFormats.length > 0) {
    rows.push({
      id: "MUSIC",
      types: ["MUSIC"],
      label: "Фонограммы",
      hint: `${requirement.musicAllowedFormats.join(", ")} · до ${requirement.musicMaxUploadSizeMb} МБ за файл`,
      accept: requirement.musicAllowedFormats.map((ext) => `.${ext}`).join(",") || "audio/*",
      maxBytes: requirement.musicMaxUploadSizeMb * BYTES_PER_MB,
      sharedBudget: false,
    });
  }
  if (requirement.mediaMode === "FILE_ONLY" || requirement.mediaMode === "URL_OR_FILE") {
    rows.push({
      id: "MEDIA",
      types: ["VIDEO", "IMAGE"],
      label: "Видео и фото",
      hint: `${requirement.mediaAllowedFormats.join(", ")} · суммарно до ${requirement.mediaMaxTotalSizeMb} МБ`,
      accept:
        requirement.mediaAllowedFormats.map((ext) => `.${ext}`).join(",") || "video/*,image/*",
      maxBytes: requirement.mediaMaxTotalSizeMb * BYTES_PER_MB,
      sharedBudget: true,
    });
  }
  return rows;
}

function FileRow({
  submissionId,
  row,
  attachments,
}: {
  submissionId: string;
  row: UploadRow;
  attachments: CorrectableAttachment[];
}): React.JSX.Element {
  const inputRef = useRef<HTMLInputElement>(null);
  const upload = useOrganizerUploadAttachment(submissionId);
  const remove = useOrganizerRemoveAttachment(submissionId);
  const existing = attachments.filter((file) => row.types.includes(file.type as AttachmentKind));
  const attachedBytes = existing.reduce((total, file) => total + (file.sizeBytes ?? 0), 0);

  /**
   * Загрузить выбранное — по одному файлу за раз.
   *
   * Последовательно и не параллельно: заявка — один агрегат с проверкой версии, и
   * две загрузки наперегонки кончились бы отказом второй как конкурентной правке.
   */
  const onFilesChosen = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const files = [...(event.target.files ?? [])];
    let budgetUsed = attachedBytes;
    for (const file of files) {
      // Отказ здесь, а не после отправки: лимит известен заранее, и ждать загрузку
      // ради предсказуемого отказа — потерянные минуты в день фестиваля.
      const wouldUse = row.sharedBudget ? budgetUsed + file.size : file.size;
      if (wouldUse > row.maxBytes) {
        toast.error(
          row.sharedBudget
            ? `${file.name}: не помещается — занято ${megabytes(budgetUsed)} из ${megabytes(row.maxBytes)}`
            : `${file.name}: ${megabytes(file.size)}, а допустимо до ${megabytes(row.maxBytes)}`,
        );
        continue;
      }
      try {
        await upload.mutateAsync({ file, attachmentType: attachmentTypeFor(row, file) });
        budgetUsed += file.size;
      } catch (error) {
        // Один неподошедший файл не отменяет остальной выбор.
        toast.error(`${file.name}: ${error instanceof Error ? error.message : "не загрузился"}`);
      }
    }
    if (inputRef.current) {
      inputRef.current.value = "";
    }
  };

  return (
    <div className="flex flex-col gap-2 rounded-md border border-border p-3">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div className="min-w-0">
          <p className="font-medium text-sm">{row.label}</p>
          <p className="text-muted-foreground text-xs">{row.hint}</p>
        </div>
        <Button
          type="button"
          size="sm"
          variant="outline"
          loading={upload.isPending}
          onClick={() => inputRef.current?.click()}
        >
          {existing.length === 0 ? "Загрузить" : "Добавить ещё"}
        </Button>
      </div>
      {existing.length === 0 ? (
        <p className="text-muted-foreground text-xs">Файлов нет</p>
      ) : (
        existing.map((file) => {
          const href = resolveMediaUrl(file.fileReference);
          const name = file.caption || fileName(file.fileReference);
          return (
            <div key={file.id} className="flex items-center justify-between gap-2">
              {href ? (
                <a
                  href={href}
                  target="_blank"
                  rel="noreferrer"
                  className="min-w-0 truncate text-primary text-sm hover:underline"
                >
                  {name}
                </a>
              ) : (
                <span className="min-w-0 truncate text-sm">{name}</span>
              )}
              <Button
                type="button"
                size="xs"
                variant="outline"
                loading={remove.isPending}
                onClick={() => remove.mutate(file.id)}
              >
                Удалить
              </Button>
            </div>
          );
        })
      )}
      <input
        ref={inputRef}
        type="file"
        accept={row.accept}
        multiple
        className="hidden"
        aria-label={row.label}
        onChange={(event) => void onFilesChosen(event)}
      />
    </div>
  );
}

export function AttachmentsSection({
  submissionId,
  attachments,
  requirement,
}: {
  submissionId: string;
  attachments: CorrectableAttachment[];
  requirement: CorrectableUploadRequirement | null | undefined;
}): React.JSX.Element | null {
  const rows = uploadRows(requirement);
  if (rows.length === 0) {
    return null;
  }
  return (
    <section aria-label="Файлы" className="space-y-3">
      <div>
        <p className="font-medium text-sm">Файлы</p>
        <p className="text-muted-foreground text-xs">
          Загружаются сразу, не дожидаясь «Сохранить». Срок приёма файлов на организатора не
          распространяется — можно догрузить то, что участник прислал вам позже.
        </p>
      </div>
      {rows.map((row) => (
        <FileRow key={row.id} submissionId={submissionId} row={row} attachments={attachments} />
      ))}
    </section>
  );
}
