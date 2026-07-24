import { CheckCircle2, Download, Loader2 } from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { useCompetitionsList } from "@/features/competitions";
import {
  type PrintPackageNomination,
  resolveMediaUrl,
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
} from "@/shared/ui";

function errorText(error: unknown, fallback: string): string {
  return error instanceof ApiError ? (error.problem?.detail ?? fallback) : fallback;
}

export function GenerationSection(): React.JSX.Element {
  const [competitionId, setCompetitionId] = useState("");
  const [jobId, setJobId] = useState<string | null>(null);
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [touched, setTouched] = useState(false);
  const [force, setForce] = useState(false);

  const competitionsQuery = useCompetitionsList();
  const summaryQuery = usePrintPackageSummary(competitionId || undefined);
  const startMutation = useStartPrintPackageMutation();
  const jobQuery = usePrintJob(jobId || undefined);

  // Reset the picker state when the competition changes.
  // biome-ignore lint/correctness/useExhaustiveDependencies: reset only on competition change
  useEffect(() => {
    setJobId(null);
    setSelected(new Set());
    setTouched(false);
    setForce(false);
    startMutation.reset();
  }, [competitionId]);

  const competitionOptions: SelectOption[] = useMemo(
    () => (competitionsQuery.data ?? []).map((item) => ({ value: item.id, label: item.title })),
    [competitionsQuery.data],
  );

  const nominations: PrintPackageNomination[] = summaryQuery.data?.nominations ?? [];
  // Only nominations whose template also has an uploaded PDF can be generated.
  const selectable = nominations.filter((item) => item.ready);
  // Before the user touches anything, every nomination with a template is selected.
  const effectiveSelected = touched ? selected : new Set(selectable.map((item) => item.categoryId));

  const job = jobQuery.data;
  const isRunning =
    startMutation.isPending || job?.status === "PENDING" || job?.status === "RUNNING";
  const isDone = job?.status === "COMPLETED";
  const isFailed = job?.status === "FAILED";
  const zipHref = resolveMediaUrl(job?.zipUrl);

  const selectedWillCreate = nominations
    .filter((item) => effectiveSelected.has(item.categoryId))
    .reduce((sum, item) => sum + item.willCreate, 0);
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
      { competitionId, categoryIds: [...effectiveSelected], force },
      { onSuccess: (created) => setJobId(created.jobId) },
    );
  }

  return (
    <div className="flex flex-col gap-6">
      <div className="max-w-md">
        <Select
          label="Конкурс"
          placeholder="Выберите конкурс"
          options={competitionOptions}
          value={competitionId}
          onValueChange={setCompetitionId}
          disabled={competitionsQuery.isLoading}
        />
      </div>

      {!competitionId ? (
        <p className="text-muted-foreground text-sm">
          Выберите конкурс, чтобы увидеть сводку по номинациям и сформировать комплект дипломов.
        </p>
      ) : summaryQuery.isLoading ? (
        <div className="flex justify-center py-10">
          <Spinner />
        </div>
      ) : nominations.length === 0 ? (
        <Alert variant="warning" title="Нет данных">
          У конкурса нет номинаций с выступлениями.
        </Alert>
      ) : (
        <>
          {selectable.length === 0 ? (
            <Alert variant="warning" title="Нельзя сформировать">
              Ни у одной номинации нет назначенного шаблона с загруженным PDF. Назначьте шаблон в
              разделе «Назначение» и загрузите его PDF в конструкторе.
            </Alert>
          ) : null}

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
                label="Перерисовать уже созданные дипломы"
                description="Перегенерировать печатный PDF даже для тех, что уже сформированы (например, после изменения шаблона)."
                checked={force}
                onCheckedChange={(checked) => setForce(checked === true)}
              />
              <div className="flex items-center gap-4">
                <Button
                  size="lg"
                  onClick={handleGenerate}
                  disabled={startMutation.isPending || effectiveSelected.size === 0}
                >
                  {startMutation.isPending ? (
                    <Loader2 className="size-4 animate-spin" aria-hidden="true" />
                  ) : null}
                  Сформировать комплект для печати
                </Button>
                <span className="text-muted-foreground text-sm">
                  Будет создано:{" "}
                  <span className="font-semibold text-foreground">{selectedWillCreate}</span>
                </span>
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
                  <div>
                    <Button asChild>
                      <a href={zipHref} download>
                        <Download className="size-4" aria-hidden="true" />
                        Скачать ZIP
                      </a>
                    </Button>
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
      <table className="w-full min-w-[36rem] text-sm">
        <thead className="bg-muted/40 text-muted-foreground">
          <tr>
            <th className="w-10 px-3 py-2">
              <Checkbox
                aria-label="Выбрать все номинации"
                checked={allSelected ? true : someSelected ? "indeterminate" : false}
                onCheckedChange={(checked) => onToggleAll(checked === true)}
              />
            </th>
            <th className="px-3 py-2 text-left font-medium">Номинация</th>
            <th className="px-3 py-2 text-left font-medium">Шаблон</th>
            <th className="px-3 py-2 text-right font-medium">Выступлений</th>
            <th className="px-3 py-2 text-right font-medium">Существует</th>
            <th className="px-3 py-2 text-right font-medium">Будет создано</th>
          </tr>
        </thead>
        <tbody>
          {nominations.map((item) => {
            const hasTemplate = item.templateId != null;
            return (
              <tr key={item.categoryId} className="border-border border-t">
                <td className="px-3 py-2 align-middle">
                  <Checkbox
                    aria-label={`Выбрать номинацию ${item.nomination ?? ""}`}
                    checked={selected.has(item.categoryId)}
                    disabled={!item.ready}
                    onCheckedChange={(checked) => onToggle(item.categoryId, checked === true)}
                  />
                </td>
                <td className="px-3 py-2 text-foreground">{item.nomination ?? "—"}</td>
                <td className="px-3 py-2">
                  {item.ready ? (
                    <span className="text-foreground">{item.templateName}</span>
                  ) : hasTemplate ? (
                    <span className="text-warning">{item.templateName} · PDF не загружен</span>
                  ) : (
                    <span className="text-warning">шаблон не назначен</span>
                  )}
                </td>
                <td className="px-3 py-2 text-right tabular-nums text-foreground">
                  {item.submissions}
                </td>
                <td className="px-3 py-2 text-right tabular-nums text-muted-foreground">
                  {item.existing}
                </td>
                <td className="px-3 py-2 text-right tabular-nums font-medium text-foreground">
                  {item.ready ? item.willCreate : "—"}
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
