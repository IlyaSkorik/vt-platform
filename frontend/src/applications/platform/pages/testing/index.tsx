import { Download, Trash2 } from "lucide-react";
import { useState } from "react";

import {
  type LoadTestRun,
  refusalMessage,
  useCleanupLoadTest,
  useLoadTestOverview,
  useStartLoadTest,
} from "@/applications/platform/api/platform-api";
import {
  Alert,
  Badge,
  Button,
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
  Checkbox,
  EmptyState,
  Input,
  LoadingState,
  Select,
  toast,
} from "@/shared/ui";

/** How a run's overall state reads, and how loud it should look. */
const STATUS: Record<
  LoadTestRun["status"],
  { label: string; variant: "neutral" | "info" | "success" | "danger" }
> = {
  PENDING: { label: "В очереди", variant: "neutral" },
  RUNNING: { label: "Генерируется", variant: "info" },
  COMPLETED: { label: "Завершён", variant: "success" },
  FAILED: { label: "Ошибка", variant: "danger" },
};

function formatDuration(seconds: number | null): string {
  if (seconds === null) return "—";
  if (seconds < 60) return `${seconds.toFixed(1)} с`;
  const minutes = Math.floor(seconds / 60);
  return `${minutes} мин ${Math.round(seconds % 60)} с`;
}

/**
 * Read a measured run against the worker's own limits.
 *
 * The projection is the point of the whole page: a festival's tirage is known
 * months in advance, and the only question worth answering here is whether that
 * tirage still fits in the hour a single job is allowed to take.
 */
function projection(run: LoadTestRun): string | null {
  if (run.msPerDiploma === null || run.status !== "COMPLETED") return null;
  const minutesForThousand = (run.msPerDiploma * 1000) / 1000 / 60;
  const overLimit = minutesForThousand > 55;
  return `При этой скорости 1000 дипломов ≈ ${minutesForThousand.toFixed(1)} мин${
    overLimit ? " — это уже у часового лимита задачи" : ""
  }`;
}

function StartForm({ maxCount }: { maxCount: number }): React.JSX.Element {
  const overview = useLoadTestOverview();
  const start = useStartLoadTest();
  const [count, setCount] = useState("500");
  const [nominations, setNominations] = useState("8");
  const [templateId, setTemplateId] = useState("");
  const [split, setSplit] = useState(false);
  const [force, setForce] = useState(false);

  const templates = overview.data?.templates ?? [];
  const parsedCount = Number.parseInt(count, 10);
  const parsedNominations = Number.parseInt(nominations, 10);
  const invalid =
    !Number.isFinite(parsedCount) ||
    parsedCount < 1 ||
    parsedCount > maxCount ||
    !Number.isFinite(parsedNominations) ||
    parsedNominations < 1 ||
    parsedNominations > parsedCount;

  const submit = (event: React.FormEvent): void => {
    event.preventDefault();
    start.mutate(
      {
        count: parsedCount,
        nominations: parsedNominations,
        ...(templateId ? { templateId } : {}),
        split,
        force,
      },
      {
        onSuccess: (run) => {
          toast.success(
            `Прогон запущен: ${run.entries} заявок, ${run.jobs.length} задач(и) в очереди`,
          );
        },
        onError: async (error) => {
          toast.error(await refusalMessage(error, "Не удалось запустить прогон"));
        },
      },
    );
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle>Новый прогон</CardTitle>
        <CardDescription>
          Создаётся синтетический фестиваль с указанным числом заявок, после чего генерация
          запускается тем же путём, что и кнопка организатора: та же задача, тот же воркер, тот же
          рендер. Номера дипломов при этом уходят в отдельную серию VT-2999-… и реальную нумерацию
          не сдвигают.
        </CardDescription>
      </CardHeader>
      <CardContent>
        <form className="grid gap-4 sm:grid-cols-2" onSubmit={submit}>
          <Input
            label="Заявок"
            inputMode="numeric"
            required
            value={count}
            onChange={(event) => setCount(event.target.value)}
            description={`Максимум ${maxCount} за один прогон`}
          />
          <Input
            label="Номинаций"
            inputMode="numeric"
            required
            value={nominations}
            onChange={(event) => setNominations(event.target.value)}
            description="Заявки распределятся по ним поровну"
          />
          <Select
            label="Шаблон диплома"
            placeholder={templates.length ? "Любой доступный" : "Нет шаблонов с PDF"}
            // Omitted rather than passed empty: Radix reserves "" for "nothing
            // selected", and handing it back as a value clears the placeholder.
            {...(templateId ? { value: templateId } : {})}
            onValueChange={setTemplateId}
            disabled={templates.length === 0}
            options={templates.map((template) => ({
              value: template.id,
              label: template.name,
            }))}
            description="Печатается поверх настоящего шаблона — от его веса зависит время рендера"
          />
          <div className="flex flex-col justify-end gap-3">
            <Checkbox
              label="Задача на каждую номинацию"
              description="Нагружает очередь, а не один воркер"
              checked={split}
              onCheckedChange={(value) => setSplit(value === true)}
            />
            <Checkbox
              label="Перерисовать существующие PDF"
              checked={force}
              onCheckedChange={(value) => setForce(value === true)}
            />
          </div>
          <div className="sm:col-span-2">
            <Button type="submit" loading={start.isPending} disabled={invalid}>
              Запустить прогон
            </Button>
          </div>
        </form>
      </CardContent>
    </Card>
  );
}

function RunCard({ run }: { run: LoadTestRun }): React.JSX.Element {
  const cleanup = useCleanupLoadTest();
  const status = STATUS[run.status];
  const failure = run.jobs.find((job) => job.error);
  const archives = run.jobs.filter((job) => job.zipUrl);
  const forecast = projection(run);

  const remove = (): void => {
    cleanup.mutate(run.competitionId, {
      onSuccess: (removed) => {
        toast.success(`Удалено: ${removed.entries} заявок, ${removed.files} файлов`);
      },
      onError: async (error) => {
        toast.error(await refusalMessage(error, "Не удалось удалить прогон"));
      },
    });
  };

  return (
    <Card>
      <CardHeader>
        <div className="flex flex-wrap items-center justify-between gap-2">
          <CardTitle className="text-base">
            {new Date(run.createdAt).toLocaleString("ru-RU")}
          </CardTitle>
          <Badge variant={status.variant}>{status.label}</Badge>
        </div>
        <CardDescription>
          {run.entries} заявок · {run.nominations} номинаций · {run.jobs.length} задач(и)
        </CardDescription>
      </CardHeader>
      <CardContent className="flex flex-col gap-4">
        <dl className="grid grid-cols-2 gap-3 sm:grid-cols-4">
          <div>
            <dt className="text-muted-foreground text-xs">Отрисовано</dt>
            <dd className="font-medium tabular-nums">
              {run.rendered} / {run.entries}
            </dd>
          </div>
          <div>
            <dt className="text-muted-foreground text-xs">Время</dt>
            <dd className="font-medium tabular-nums">{formatDuration(run.elapsedSeconds)}</dd>
          </div>
          <div>
            <dt className="text-muted-foreground text-xs">На диплом</dt>
            <dd className="font-medium tabular-nums">
              {run.msPerDiploma === null ? "—" : `${run.msPerDiploma} мс`}
            </dd>
          </div>
          <div>
            <dt className="text-muted-foreground text-xs">Дипломов в базе</dt>
            <dd className="font-medium tabular-nums">{run.diplomas}</dd>
          </div>
        </dl>

        {forecast ? <p className="text-muted-foreground text-sm">{forecast}</p> : null}

        {failure?.error ? (
          <Alert variant="danger" title="Задача упала">
            {failure.error}
          </Alert>
        ) : null}

        <div className="flex flex-wrap items-center gap-2">
          {archives.map((job) => (
            <Button key={job.jobId} variant="outline" size="sm" asChild>
              <a href={job.zipUrl ?? "#"} download>
                <Download className="size-4" aria-hidden="true" />
                Архив ({job.created + job.skipped})
              </a>
            </Button>
          ))}
          <Button
            variant="outline"
            size="sm"
            className="ml-auto text-danger"
            loading={cleanup.isPending}
            onClick={remove}
          >
            <Trash2 className="size-4" aria-hidden="true" />
            Удалить прогон
          </Button>
        </div>
      </CardContent>
    </Card>
  );
}

/**
 * The operator's test bench for diploma generation.
 *
 * A print package is one background task that renders every diploma in a loop —
 * not one task per diploma — so what this page measures is how long that single
 * loop takes on real hardware with a real template, and whether a festival's
 * tirage still fits inside the hour the worker allows a job. Everything a run
 * creates is removable from here, which is what makes it safe to point at the
 * live deployment.
 */
export function PlatformTestingPage(): React.JSX.Element {
  const overview = useLoadTestOverview();
  const cleanup = useCleanupLoadTest();
  const totals = overview.data?.totals;

  const removeAll = (): void => {
    cleanup.mutate(undefined, {
      onSuccess: (removed) => {
        toast.success(
          `Удалено прогонов: ${removed.runs} — ${removed.entries} заявок, ${removed.diplomas} дипломов, ${removed.files} файлов`,
        );
      },
      onError: async (error) => {
        toast.error(await refusalMessage(error, "Не удалось удалить данные"));
      },
    });
  };

  return (
    <div className="flex flex-col gap-6">
      <header className="flex flex-col gap-1">
        <h1 className="font-semibold text-2xl">Тестирование</h1>
        <p className="text-muted-foreground text-sm">
          Нагрузочный прогон генерации дипломов на живом стенде.
        </p>
      </header>

      <Alert variant="warning" title="Прогон пишет в рабочую базу">
        Заявки, дипломы и отрендеренные PDF создаются по-настоящему и занимают место на диске —
        каждый диплом это полная копия шаблона. Реальную нумерацию дипломов прогон не трогает, но
        всё созданное стоит удалить сразу после замера. Генерация занимает слот воркера, поэтому в
        разгар работы фестивалей лучше не запускать.
      </Alert>

      {overview.isLoading ? <LoadingState label="Загрузка стенда" /> : null}

      {overview.isError ? (
        <EmptyState
          title="Не удалось загрузить стенд"
          description="Проверьте доступ к консоли платформы и повторите попытку."
        />
      ) : null}

      {overview.data ? <StartForm maxCount={overview.data.maxCount} /> : null}

      {totals && totals.runs > 0 ? (
        <div className="flex flex-wrap items-center justify-between gap-3 rounded-lg border border-border bg-muted/20 p-4">
          <p className="text-sm">
            Сейчас в базе: <span className="font-medium">{totals.runs}</span> прогон(ов),{" "}
            <span className="font-medium">{totals.entries}</span> заявок,{" "}
            <span className="font-medium">{totals.diplomas}</span> дипломов.
          </p>
          <Button variant="outline" loading={cleanup.isPending} onClick={removeAll}>
            <Trash2 className="size-4" aria-hidden="true" />
            Удалить все прогоны
          </Button>
        </div>
      ) : null}

      {overview.data && overview.data.runs.length === 0 ? (
        <EmptyState
          title="Прогонов пока не было"
          description="Задайте параметры выше и запустите первый — результат появится здесь."
        />
      ) : null}

      <div className="grid gap-4 lg:grid-cols-2">
        {(overview.data?.runs ?? []).map((run) => (
          <RunCard key={run.competitionId} run={run} />
        ))}
      </div>
    </div>
  );
}
