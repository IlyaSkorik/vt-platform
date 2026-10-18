import { CheckCircle2, Download, Loader2 } from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { useCompetitionsList } from "@/features/competitions";
import {
  type DocumentSlot,
  type PrintPackageNomination,
  resolveMediaUrl,
  useGenerateDocumentsMutation,
  usePrintJob,
  usePrintPackageSummary,
  useStartPrintPackageMutation,
} from "@/features/diplomas";
import { ApiError } from "@/shared/api";
import {
  Alert,
  Button,
  Card,
  CardContent,
  Checkbox,
  Select,
  type SelectOption,
  Spinner,
  toast,
} from "@/shared/ui";

function errorText(error: unknown, fallback: string): string {
  return error instanceof ApiError ? (error.problem?.detail ?? fallback) : fallback;
}

/** Which thank-you action is in flight — the two share one mutation. */
type ThanksAction = "publish" | "print";

export function GenerationSection(): React.JSX.Element {
  const [competitionId, setCompetitionId] = useState("");
  const [jobId, setJobId] = useState<string | null>(null);
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [touched, setTouched] = useState(false);
  const [force, setForce] = useState(false);
  const [thanksAction, setThanksAction] = useState<ThanksAction | null>(null);
  const [thanksZipUrl, setThanksZipUrl] = useState<string | null>(null);

  const competitionsQuery = useCompetitionsList();
  const summaryQuery = usePrintPackageSummary(competitionId || undefined);
  const startMutation = useStartPrintPackageMutation();
  const generateThanks = useGenerateDocumentsMutation();
  const jobQuery = usePrintJob(jobId || undefined);

  // Reset the picker state when the competition changes.
  // biome-ignore lint/correctness/useExhaustiveDependencies: reset only on competition change
  useEffect(() => {
    setJobId(null);
    setSelected(new Set());
    setTouched(false);
    setForce(false);
    setThanksZipUrl(null);
    startMutation.reset();
  }, [competitionId]);

  const competitionOptions: SelectOption[] = useMemo(
    () => (competitionsQuery.data ?? []).map((item) => ({ value: item.id, label: item.title })),
    [competitionsQuery.data],
  );

  const nominations: PrintPackageNomination[] = summaryQuery.data?.nominations ?? [];
  // A nomination can be picked when *either* kind can be produced for it. Which
  // kind actually runs is decided per action below, from that kind's own slot.
  const selectable = nominations.filter((item) => item.diploma.ready || item.thankYou.ready);
  // Before the user touches anything, every producible nomination is selected.
  const effectiveSelected = touched ? selected : new Set(selectable.map((item) => item.categoryId));

  const job = jobQuery.data;
  const isRunning =
    startMutation.isPending || job?.status === "PENDING" || job?.status === "RUNNING";
  const isDone = job?.status === "COMPLETED";
  const isFailed = job?.status === "FAILED";
  const zipHref = resolveMediaUrl(job?.zipUrl);

  /**
   * The picked nominations that are actually ready for one kind of document.
   *
   * The gate that keeps a run from 409-ing: a nomination with a diploma template
   * and no thank-you template is a legitimate pick for the print package and not
   * a target for letters at all, so each action narrows the same selection by its
   * own slot rather than sending everything the user ticked.
   */
  function readyFor(slotOf: (item: PrintPackageNomination) => DocumentSlot): {
    categoryIds: string[];
    willCreate: number;
    skipped: number;
  } {
    const picked = nominations.filter((item) => effectiveSelected.has(item.categoryId));
    const ready = picked.filter((item) => slotOf(item).ready);
    return {
      categoryIds: ready.map((item) => item.categoryId),
      willCreate: ready.reduce((sum, item) => sum + slotOf(item).willCreate, 0),
      skipped: picked.length - ready.length,
    };
  }

  const diplomaRun = readyFor((item) => item.diploma);
  const thanksRun = readyFor((item) => item.thankYou);

  const allSelected =
    selectable.length > 0 && selectable.every((item) => effectiveSelected.has(item.categoryId));
  const someSelected = selectable.some((item) => effectiveSelected.has(item.categoryId));

  function toggle(categoryId: string, on: boolean): void {
    const next = new Set(effectiveSelected);
    if (on) {
      next.add(categoryId);
    } else {
      next.delete(categoryId);
    }
    setSelected(next);
    setTouched(true);
  }

  function toggleAll(on: boolean): void {
    setSelected(on ? new Set(selectable.map((item) => item.categoryId)) : new Set());
    setTouched(true);
  }

  function handleGenerate(): void {
    startMutation.mutate(
      { competitionId, categoryIds: diplomaRun.categoryIds, force },
      { onSuccess: (created) => setJobId(created.jobId) },
    );
  }

  /**
   * Generate thank-you letters for the nominations that have a letter template.
   *
   * A separate action, not a variant of the print package: letters are unnumbered
   * and unverifiable, so there is no job to poll — each nomination's own THANK_YOU
   * template renders straight to the participants' cabinets.
   *
   * The two actions differ in what they *do* with the result, not in what they
   * render: `publish` puts the letters in the participants' cabinets, `print` only
   * prepares them and hands back a ZIP — nothing becomes visible. A letter already
   * published by an earlier run stays published; nothing here takes one back.
   */
  async function handleGenerateThanks(action: ThanksAction): Promise<void> {
    const forPrint = action === "print";
    setThanksAction(action);
    setThanksZipUrl(null);
    try {
      const summary = await generateThanks.mutateAsync({
        competitionId,
        categoryIds: thanksRun.categoryIds,
        documentType: "THANK_YOU",
        force,
        bundle: forPrint,
        publish: !forPrint,
      });
      const skipped =
        (summary.withoutRecipient ? ` Заявок без педагога: ${summary.withoutRecipient}.` : "") +
        // Entries in a nomination that assigns no letter template, inside a genre
        // that has no default either. Named rather than quietly missing from the
        // count: the organizer is the only one who can assign the template.
        (summary.withoutTemplate ? ` Заявок без шаблона: ${summary.withoutTemplate}.` : "");
      if (forPrint) {
        setThanksZipUrl(summary.zipUrl);
        toast.success(
          summary.documents > 0
            ? `Благодарностей в архиве: ${summary.documents}. Скачайте ZIP для печати — в личных кабинетах они не опубликованы.${skipped}`
            : `Нечего печатать: благодарности не сформированы.${skipped}`,
        );
        return;
      }
      toast.success(
        summary.published > 0
          ? `Благодарностей опубликовано: ${summary.published}. Они доступны участникам в личном кабинете.${skipped}`
          : `Новых благодарностей нет: все уже опубликованы.${skipped}`,
      );
    } catch (error) {
      const message =
        error instanceof ApiError
          ? (error.problem?.detail ?? "Не удалось сформировать благодарности.")
          : "Не удалось сформировать благодарности.";
      toast.error(message);
    } finally {
      setThanksAction(null);
    }
  }

  return (
    <div className="flex flex-col gap-6">
      <div className="max-w-md">
        <Select
          label="Фестиваль"
          placeholder="Выберите фестиваль"
          options={competitionOptions}
          value={competitionId}
          onValueChange={setCompetitionId}
          disabled={competitionsQuery.isLoading}
        />
      </div>

      {!competitionId ? (
        <p className="text-muted-foreground text-sm">
          Выберите фестиваль, чтобы увидеть сводку по жанрам и сформировать комплект дипломов.
        </p>
      ) : summaryQuery.isLoading ? (
        <div className="flex justify-center py-10">
          <Spinner />
        </div>
      ) : nominations.length === 0 ? (
        <Alert variant="warning" title="Нет данных">
          У фестиваля нет жанров с выступлениями.
        </Alert>
      ) : (
        <>
          {selectable.length === 0 ? (
            <Alert variant="warning" title="Нельзя сформировать">
              Ни у одного жанра нет назначенного шаблона с загруженным PDF. Назначьте шаблон в
              разделе «Назначение» и загрузите его PDF в конструкторе.
            </Alert>
          ) : null}

          {/* Says why «Выступлений» can be smaller than the number of applications
              filed: the run only walks entries actually taken into the competition. */}
          <p className="text-muted-foreground text-sm">
            Учитываются только заявки, принятые на фестиваль: отменённые, отправленные на доработку
            и ещё не принятые документов не получают.
          </p>

          <NominationTable
            nominations={nominations}
            selected={effectiveSelected}
            allSelected={allSelected}
            someSelected={someSelected && !allSelected}
            onToggle={toggle}
            onToggleAll={toggleAll}
          />

          {startMutation.isError ? (
            <Alert variant="danger" title="Не удалось запустить генерацию">
              {errorText(startMutation.error, "Попробуйте ещё раз.")}
            </Alert>
          ) : null}

          {!jobId ? (
            <div className="flex flex-col gap-3">
              <Checkbox
                label="Перерисовать уже созданные документы"
                description="Перегенерировать PDF даже для тех, что уже сформированы (например, после изменения шаблона)."
                checked={force}
                onCheckedChange={(checked) => setForce(checked === true)}
              />
              <RunAction
                label="Сформировать комплект для печати"
                pending={startMutation.isPending}
                run={diplomaRun}
                missingHint="без шаблона диплома"
                onRun={handleGenerate}
              />
              <div className="flex flex-col gap-3 border-border border-t pt-4">
                <RunAction
                  label="Сформировать и опубликовать в ЛК"
                  variant="outline"
                  pending={thanksAction === "publish"}
                  busy={generateThanks.isPending}
                  run={thanksRun}
                  missingHint="без шаблона благодарности"
                  onRun={() => void handleGenerateThanks("publish")}
                />
                <RunAction
                  label="Сформировать и скачать для печати"
                  variant="outline"
                  pending={thanksAction === "print"}
                  busy={generateThanks.isPending}
                  run={thanksRun}
                  missingHint="без шаблона благодарности"
                  onRun={() => void handleGenerateThanks("print")}
                />
                <p className="text-muted-foreground text-sm">
                  По шаблону благодарности каждой выбранной номинации — одна благодарность на
                  педагога: сколько бы номеров он ни выставил в этом жанре, лист будет один. Первое
                  действие публикует их в личных кабинетах участников. Второе только готовит файлы и
                  отдаёт ZIP со всеми благодарностями выбранных жанров (по папкам жанров) — в
                  кабинетах они не появятся, пока не нажать «Сформировать и опубликовать в ЛК».
                </p>
                {thanksZipUrl ? (
                  <div>
                    <Button asChild variant="outline">
                      <a href={resolveMediaUrl(thanksZipUrl) ?? "#"} download>
                        <Download className="size-4" aria-hidden="true" />
                        Скачать ZIP с благодарностями
                      </a>
                    </Button>
                  </div>
                ) : null}
              </div>
            </div>
          ) : null}

          {jobId && isRunning ? (
            <Card>
              <CardContent className="flex flex-col gap-3 p-5">
                <div className="flex items-center gap-2 text-foreground text-sm">
                  <Loader2 className="size-4 animate-spin text-primary" aria-hidden="true" />
                  Подготавливаем комплект дипломов…
                </div>
                <div
                  className="h-2 w-full overflow-hidden rounded-full bg-muted"
                  role="progressbar"
                  aria-label="Генерация дипломов"
                >
                  <div className="h-full w-1/2 animate-pulse rounded-full bg-primary" />
                </div>
              </CardContent>
            </Card>
          ) : null}

          {isDone && job ? (
            <Card>
              <CardContent className="flex flex-col gap-4 p-5">
                <div className="flex items-center gap-2 font-medium text-foreground">
                  <CheckCircle2 className="size-5 text-success" aria-hidden="true" />
                  Комплект дипломов готов
                </div>
                <div className="flex gap-6 text-sm">
                  <span className="text-muted-foreground">
                    Создано: <span className="font-semibold text-foreground">{job.created}</span>
                  </span>
                  <span className="text-muted-foreground">
                    Пропущено: <span className="font-semibold text-foreground">{job.skipped}</span>
                  </span>
                </div>
                {zipHref ? (
                  <div className="flex flex-col gap-2">
                    <div>
                      <Button asChild>
                        <a href={zipHref} download>
                          <Download className="size-4" aria-hidden="true" />
                          Скачать ZIP
                        </a>
                      </Button>
                    </div>
                    {/* The archive's shape is a printing instruction, so it is stated
                        next to the download rather than discovered after unzipping. */}
                    <p className="text-muted-foreground text-sm">
                      Внутри — папка на каждый шаблон: всё, что печатается на одной подложке, лежит
                      вместе, а листы со степенями для допечатки — в подпапке «МЕСТА» этого же
                      шаблона.
                    </p>
                  </div>
                ) : null}
              </CardContent>
            </Card>
          ) : null}

          {isFailed && job ? (
            <Alert variant="danger" title="Генерация не удалась">
              {job.error ?? "Во время формирования комплекта произошла ошибка."}
            </Alert>
          ) : null}
        </>
      )}
    </div>
  );
}

/**
 * One generation button plus what the current selection means for it.
 *
 * States what will be produced and what is being left out, so a selection that
 * only partly fits this kind of document is visible before the click rather than
 * as an error after it.
 */
function RunAction({
  label,
  variant,
  pending,
  busy,
  run,
  missingHint,
  onRun,
}: {
  label: string;
  variant?: "outline";
  /** This action is the one running — it shows the spinner. */
  pending: boolean;
  /** Some action sharing the same run is in flight, so this one waits its turn. */
  busy?: boolean;
  run: { categoryIds: string[]; willCreate: number; skipped: number };
  missingHint: string;
  onRun: () => void;
}): React.JSX.Element {
  return (
    <div className="flex flex-wrap items-center gap-x-4 gap-y-2">
      <Button
        size="lg"
        variant={variant}
        onClick={onRun}
        disabled={pending || busy || run.categoryIds.length === 0}
      >
        {pending ? <Loader2 className="size-4 animate-spin" aria-hidden="true" /> : null}
        {label}
      </Button>
      <span className="text-muted-foreground text-sm">
        Жанров: <span className="font-semibold text-foreground">{run.categoryIds.length}</span> ·
        будет создано: <span className="font-semibold text-foreground">{run.willCreate}</span>
        {run.skipped > 0 ? (
          <span className="text-warning">
            {" "}
            · пропущено {run.skipped} {missingHint}
          </span>
        ) : null}
      </span>
    </div>
  );
}

function NominationTable({
  nominations,
  selected,
  allSelected,
  someSelected,
  onToggle,
  onToggleAll,
}: {
  nominations: PrintPackageNomination[];
  selected: Set<string>;
  allSelected: boolean;
  someSelected: boolean;
  onToggle: (categoryId: string, on: boolean) => void;
  onToggleAll: (on: boolean) => void;
}): React.JSX.Element {
  return (
    <div className="overflow-x-auto rounded-lg border border-border">
      <table className="w-full min-w-[48rem] text-sm">
        <thead className="bg-muted/40 text-muted-foreground">
          <tr>
            <th className="w-10 px-3 py-2">
              <Checkbox
                aria-label="Выбрать все жанры"
                checked={allSelected ? true : someSelected ? "indeterminate" : false}
                onCheckedChange={(checked) => onToggleAll(checked === true)}
              />
            </th>
            <th className="px-3 py-2 text-left font-medium">Жанр</th>
            <th className="px-3 py-2 text-right font-medium">Выступлений</th>
            <th className="px-3 py-2 text-left font-medium">Диплом</th>
            {/* Not a run of its own: individual diplomas are issued to the named
                members of a collective when the protocol is published. The column is
                here so an organizer can see the template is in place — and how many
                sheets that publication will produce — before it happens. */}
            <th className="px-3 py-2 text-left font-medium">Индивидуальные</th>
            <th className="px-3 py-2 text-left font-medium">Благодарность</th>
          </tr>
        </thead>
        <tbody>
          {nominations.map((item) => (
            <tr key={item.categoryId} className="border-border border-t">
              <td className="px-3 py-2 align-top">
                <Checkbox
                  aria-label={`Выбрать жанр ${item.nomination ?? ""}`}
                  checked={selected.has(item.categoryId)}
                  disabled={!item.diploma.ready && !item.thankYou.ready}
                  onCheckedChange={(checked) => onToggle(item.categoryId, checked === true)}
                />
              </td>
              <td className="px-3 py-2 align-top text-foreground">{item.nomination ?? "—"}</td>
              <td className="px-3 py-2 text-right align-top tabular-nums text-foreground">
                {item.submissions}
              </td>
              <td className="px-3 py-2 align-top">
                <SlotCell slot={item.diploma} />
              </td>
              <td className="px-3 py-2 align-top">
                <SlotCell slot={item.individualDiploma} atPublication />
              </td>
              <td className="px-3 py-2 align-top">
                <SlotCell slot={item.thankYou} />
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

/**
 * One genre's template and forecast for a single kind of document.
 *
 * `atPublication` marks a kind no run on this page issues: individual diplomas are
 * created when the protocol is published, so the forecast is what that publication will
 * produce rather than what a button here would. Saying so is the difference between a
 * count an organizer can act on and one they wait for in vain.
 *
 * A genre whose nominations print on templates of their own shows them under its
 * own, and says how many entries nothing can be printed for — a single genre-wide
 * template name would otherwise promise sheets for nominations that have none.
 */
function SlotCell({
  slot,
  atPublication = false,
}: {
  slot: DocumentSlot;
  atPublication?: boolean;
}): React.JSX.Element {
  const perNomination =
    slot.disciplines.length > 0 ? (
      <span className="text-muted-foreground text-xs">
        {slot.disciplines
          .map(
            (item) =>
              `${item.discipline ?? "номинация"} · ${item.templateName}${item.ready ? "" : " (PDF не загружен)"}`,
          )
          .join(" · ")}
      </span>
    ) : null;

  if (slot.templateId == null && !slot.ready) {
    return (
      <div className="flex flex-col">
        <span className="text-warning">шаблон не назначен</span>
        {perNomination}
      </div>
    );
  }
  if (slot.templateId != null && !slot.ready) {
    return (
      <div className="flex flex-col">
        <span className="text-warning">{slot.templateName} · PDF не загружен</span>
        {perNomination}
      </div>
    );
  }
  return (
    <div className="flex flex-col">
      <span className="text-foreground">{slot.templateName ?? "по номинациям"}</span>
      {perNomination}
      <span className="text-muted-foreground text-xs tabular-nums">
        {atPublication ? "при публикации: " : "будет создано: "}
        {slot.willCreate} · уже есть: {slot.existing}
        {slot.withoutRecipient > 0 ? ` · без педагога: ${slot.withoutRecipient}` : ""}
      </span>
      {slot.withoutTemplate > 0 ? (
        <span className="text-warning text-xs tabular-nums">
          без шаблона: {slot.withoutTemplate}
        </span>
      ) : null}
    </div>
  );
}
