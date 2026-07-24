import { CheckCircle2, Download, FilePlus2, FileStack, Loader2, Users } from "lucide-react";
import { useMemo, useState } from "react";
import { useCompetitionsList } from "@/features/competitions";
import {
  type DiplomaAssignment,
  resolveMediaUrl,
  useDiplomaAssignments,
  useDiplomaRegistry,
  usePreviewApplications,
  usePrintJob,
  useStartPrintPackageMutation,
} from "@/features/diplomas";
import { ApiError } from "@/shared/api";
import { Alert, Button, Card, CardContent, Select, type SelectOption, Spinner } from "@/shared/ui";

function StatCard({
  icon,
  label,
  value,
  accent,
}: {
  icon: React.ReactNode;
  label: string;
  value: React.ReactNode;
  accent?: boolean;
}): React.JSX.Element {
  return (
    <Card>
      <CardContent className="flex items-center gap-3 p-4">
        <span
          className={
            accent
              ? "flex size-9 shrink-0 items-center justify-center rounded-md bg-primary/10 text-primary"
              : "flex size-9 shrink-0 items-center justify-center rounded-md bg-accent text-accent-foreground"
          }
        >
          {icon}
        </span>
        <div className="min-w-0">
          <p className="text-muted-foreground text-xs">{label}</p>
          <p className="truncate font-semibold text-foreground text-lg">{value}</p>
        </div>
      </CardContent>
    </Card>
  );
}

function assignedTemplate(
  assignments: DiplomaAssignment[] | undefined,
  competitionId: string,
): DiplomaAssignment | undefined {
  return (assignments ?? []).find((assignment) => assignment.competitionId === competitionId);
}

export function GenerationSection(): React.JSX.Element {
  const [competitionId, setCompetitionId] = useState("");
  const [jobId, setJobId] = useState<string | null>(null);

  const competitionsQuery = useCompetitionsList();
  const assignmentsQuery = useDiplomaAssignments();
  const applicationsQuery = usePreviewApplications(competitionId || undefined);
  const registryQuery = useDiplomaRegistry(competitionId || undefined);
  const startMutation = useStartPrintPackageMutation();
  const jobQuery = usePrintJob(jobId || undefined);

  const competitionOptions: SelectOption[] = useMemo(
    () => (competitionsQuery.data ?? []).map((item) => ({ value: item.id, label: item.title })),
    [competitionsQuery.data],
  );

  const template = competitionId
    ? assignedTemplate(assignmentsQuery.data, competitionId)
    : undefined;
  const submissions = applicationsQuery.data?.length ?? 0;
  const existing = registryQuery.data?.length ?? 0;
  const willCreate = Math.max(0, submissions - existing);

  const summaryLoading =
    Boolean(competitionId) &&
    (assignmentsQuery.isLoading || applicationsQuery.isLoading || registryQuery.isLoading);

  const job = jobQuery.data;
  const isRunning =
    startMutation.isPending || job?.status === "PENDING" || job?.status === "RUNNING";
  const isDone = job?.status === "COMPLETED";
  const isFailed = job?.status === "FAILED";
  const zipHref = resolveMediaUrl(job?.zipUrl);

  function handleCompetitionChange(value: string): void {
    setCompetitionId(value);
    setJobId(null);
    startMutation.reset();
  }

  function handleGenerate(): void {
    if (!template) {
      return;
    }
    startMutation.mutate(
      { competitionId, templateId: template.templateId },
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
          onValueChange={handleCompetitionChange}
          disabled={competitionsQuery.isLoading}
        />
      </div>

      {!competitionId ? (
        <p className="text-muted-foreground text-sm">
          Выберите конкурс, чтобы увидеть сводку и сформировать комплект дипломов.
        </p>
      ) : summaryLoading ? (
        <div className="flex justify-center py-10">
          <Spinner />
        </div>
      ) : (
        <>
          {template ? (
            <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
              <StatCard
                accent
                icon={<FileStack className="size-4" aria-hidden="true" />}
                label="Назначенный шаблон"
                value={template.templateName}
              />
              <StatCard
                icon={<Users className="size-4" aria-hidden="true" />}
                label="Выступлений"
                value={submissions}
              />
              <StatCard
                icon={<FileStack className="size-4" aria-hidden="true" />}
                label="Дипломов уже существует"
                value={existing}
              />
              <StatCard
                icon={<FilePlus2 className="size-4" aria-hidden="true" />}
                label="Будет создано"
                value={willCreate}
              />
            </div>
          ) : (
            <Alert variant="warning" title="Шаблон не назначен">
              Для конкурса не назначен шаблон диплома. Назначьте его в разделе «Назначение», чтобы
              сформировать комплект.
            </Alert>
          )}

          {startMutation.isError ? (
            <Alert variant="danger" title="Не удалось запустить генерацию">
              {startMutation.error instanceof ApiError
                ? (startMutation.error.problem?.detail ?? "Попробуйте ещё раз.")
                : "Попробуйте ещё раз."}
            </Alert>
          ) : null}

          {/* Idle: the main action. */}
          {template && !jobId ? (
            <div>
              <Button size="lg" onClick={handleGenerate} disabled={startMutation.isPending}>
                {startMutation.isPending ? (
                  <Loader2 className="size-4 animate-spin" aria-hidden="true" />
                ) : null}
                Сформировать комплект для печати
              </Button>
            </div>
          ) : null}

          {/* Working. */}
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

          {/* Done. */}
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

          {/* Failed. */}
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
