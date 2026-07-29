import { AlertTriangle, Trash2, Upload } from "lucide-react";
import { useCallback, useMemo, useRef } from "react";

import {
  FONT_VARIANT_LABELS,
  type FontFamily,
  formatFontSize,
  missingVariants,
  type UploadedFont,
  useDeleteFont,
  useFontCatalog,
  useFontFaces,
  useUploadFont,
} from "@/features/diplomas";
import { ApiError } from "@/shared/api";
import { Badge, Button, EmptyState, IconButton, LoadingState, toast } from "@/shared/ui";

import { formatDate } from "../../lib/format";

/** The one message every failed action here falls back to. */
function failureMessage(error: unknown, fallback: string): string {
  return error instanceof ApiError ? (error.problem?.detail ?? fallback) : fallback;
}

function FamilyCard({ family }: { family: FontFamily }): React.JSX.Element {
  const missing = missingVariants(family);
  return (
    <li className="flex flex-col gap-2 rounded-lg border border-border bg-card p-4">
      <div className="flex flex-wrap items-center gap-2">
        {/* Set in itself: the quickest way to see whether a face really loaded is to read its
            own name in it. */}
        <span
          className="min-w-0 truncate font-medium text-base"
          style={{ fontFamily: `"${family.substitutedBy ?? family.family}", sans-serif` }}
        >
          {family.family}
        </span>
        <Badge variant={family.source === "UPLOADED" ? "info" : "neutral"}>
          {family.source === "UPLOADED" ? "Загружен" : "Встроен"}
        </Badge>
        {family.substitutedBy ? (
          <Badge variant="warning">Печатается как {family.substitutedBy}</Badge>
        ) : null}
      </div>
      <p className="text-muted-foreground text-sm">
        {family.variants.map((variant) => FONT_VARIANT_LABELS[variant.variant]).join(", ")}
      </p>
      {missing.length > 0 && family.substitutedBy == null ? (
        <p className="text-muted-foreground text-xs">
          Нет: {missing.map((variant) => FONT_VARIANT_LABELS[variant]).join(", ")} — вместо них
          возьмётся обычное начертание этого же шрифта.
        </p>
      ) : null}
    </li>
  );
}

/**
 * Шрифты — the library the diploma editor's font list is built from.
 *
 * The section exists because of a mismatch that used to be invisible: the editor offered seven
 * families and the renderer had files for none of them, so every diploma printed in a fallback
 * face regardless of what the organizer chose and approved. Now the list is served from the
 * files that exist — and an organizer who needs their festival's own typeface uploads it here
 * rather than waiting for a release.
 *
 * The screen is deliberately blunt about the three things that surprise people:
 *
 * - **.ttf only.** A CFF-based `.otf` is a perfectly good font that cannot be embedded in a
 *   PDF at all. Said up front, because it is the most likely upload to fail.
 * - **Cyrillic is required.** A Latin-only face renders a Russian surname as empty boxes, so it
 *   is refused at upload rather than discovered on a printed diploma.
 * - **Arial, Times New Roman and Georgia are substitutes.** No licence lets the platform ship
 *   them; each is drawn with a free face and says which.
 */
export function FontsSection(): React.JSX.Element {
  const inputRef = useRef<HTMLInputElement>(null);
  const { data, isLoading, isError } = useFontCatalog();
  // Also loads the `@font-face` rules into this document, so each name is shown in its own face.
  const families = useFontFaces();
  const upload = useUploadFont();
  const remove = useDeleteFont();

  const uploaded: UploadedFont[] = useMemo(() => data?.uploaded ?? [], [data]);

  const handleFiles = useCallback(
    async (files: FileList | null): Promise<void> => {
      if (files == null || files.length === 0) {
        return;
      }
      // One request per file, sequentially: the family and variant are read from each file, so
      // four files of one family are four independent additions and one failure must not
      // discard the others.
      let added = 0;
      for (const file of Array.from(files)) {
        try {
          await upload.mutateAsync(file);
          added += 1;
        } catch (error) {
          toast.error(`${file.name}: ${failureMessage(error, "не удалось загрузить.")}`);
        }
      }
      if (added > 0) {
        toast.success(added === 1 ? "Шрифт добавлен" : `Добавлено шрифтов: ${added}`);
      }
      if (inputRef.current != null) {
        // Cleared so choosing the same file again still fires a change event.
        inputRef.current.value = "";
      }
    },
    [upload],
  );

  const handleDelete = useCallback(
    async (font: UploadedFont): Promise<void> => {
      try {
        await remove.mutateAsync(font.id);
        toast.success("Шрифт удалён из библиотеки");
      } catch (error) {
        toast.error(failureMessage(error, "Не удалось удалить шрифт."));
      }
    },
    [remove],
  );

  return (
    <div className="flex flex-col gap-6">
      <div className="flex flex-col gap-3 rounded-lg border border-border bg-muted/40 p-4">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div className="min-w-0">
            <h3 className="font-medium text-foreground text-sm">Свой шрифт</h3>
            <p className="text-muted-foreground text-sm">
              Загрузите <strong>.ttf</strong> — по файлу на начертание. Название семейства и
              начертание читаются из самого файла, называть ничего не нужно.
            </p>
          </div>
          <Button onClick={() => inputRef.current?.click()} loading={upload.isPending}>
            <Upload className="size-4" aria-hidden="true" />
            Загрузить .ttf
          </Button>
        </div>
        <input
          ref={inputRef}
          type="file"
          accept=".ttf,font/ttf,application/x-font-ttf"
          multiple
          className="sr-only"
          onChange={(event) => void handleFiles(event.target.files)}
        />
        <p className="flex items-start gap-2 text-muted-foreground text-xs">
          <AlertTriangle className="mt-0.5 size-3.5 shrink-0" aria-hidden="true" />
          <span>
            Файлы <strong>.otf</strong> с контурами CFF в PDF встроить нельзя — почти у каждого
            шрифта есть версия .ttf. Шрифт без кириллицы отклоняется: русские имена в дипломе
            остались бы пустыми.
          </span>
        </p>
      </div>

      {isLoading ? (
        <LoadingState label="Загружаем библиотеку шрифтов…" />
      ) : isError ? (
        <EmptyState
          title="Не удалось загрузить библиотеку"
          description="Обновите страницу. Конструктор продолжит работать со шрифтами, уже указанными в шаблонах."
        />
      ) : (
        <>
          <section className="flex flex-col gap-3">
            <h3 className="font-medium text-foreground text-sm">
              Доступно в конструкторе ({families.length})
            </h3>
            {families.length === 0 ? (
              <EmptyState
                title="Библиотека пуста"
                description="Загрузите первый .ttf — до этого дипломы печатаются встроенным резервным шрифтом."
              />
            ) : (
              <ul className="grid gap-3 sm:grid-cols-2">
                {families.map((family) => (
                  <FamilyCard key={`${family.source}-${family.family}`} family={family} />
                ))}
              </ul>
            )}
          </section>

          {uploaded.length > 0 ? (
            <section className="flex flex-col gap-3">
              <h3 className="font-medium text-foreground text-sm">
                Загруженные файлы ({uploaded.length})
              </h3>
              <p className="text-muted-foreground text-sm">
                Удаление убирает шрифт из выбора. Уже выпущенные дипломы не меняются — они
                существуют как документы.
              </p>
              <ul className="rounded-lg border border-border">
                {uploaded.map((font) => (
                  <li
                    key={font.id}
                    className="flex items-center gap-3 border-border border-b px-3 py-2 text-sm last:border-b-0"
                  >
                    <div className="min-w-0 flex-1">
                      <span className="block truncate font-medium">
                        {font.family} · {FONT_VARIANT_LABELS[font.variant]}
                      </span>
                      <span className="block truncate text-muted-foreground text-xs">
                        {font.originalFilename} · {formatFontSize(font.sizeBytes)} ·{" "}
                        {formatDate(font.uploadedAt)}
                      </span>
                    </div>
                    <IconButton
                      variant="ghost"
                      size="sm"
                      aria-label={`Удалить ${font.family} ${FONT_VARIANT_LABELS[font.variant]}`}
                      icon={<Trash2 className="size-4" aria-hidden="true" />}
                      disabled={remove.isPending}
                      onClick={() => void handleDelete(font)}
                    />
                  </li>
                ))}
              </ul>
            </section>
          ) : null}
        </>
      )}
    </div>
  );
}
