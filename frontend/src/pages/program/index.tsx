import { ArrowDown, ArrowUp, Check, Play, SkipForward } from "lucide-react";
import { useParams } from "react-router";

import {
  type PublicProgram,
  type PublicProgramProgress,
  type PublicProgramRow,
  useHostReorder,
  usePublicProgram,
  useSetRowProgress,
} from "@/features/public-program";
import { APP_NAME } from "@/shared/config";
import { formatClock, formatSpan } from "@/shared/lib";
import { Badge, Button, EmptyState, LoadingState, toast } from "@/shared/ui";

/**
 * `/program/:slug` — a published programme, as handed to a sound engineer, a host, the
 * jury, or a display beside the stage.
 *
 * Unauthenticated by design: the slug in the URL is the only input and the only
 * credential. The page renders whatever columns the organizer published — it does not
 * know or care which ones those are, which is exactly why an unpublished column cannot
 * appear here.
 *
 * One page, two capabilities. Every screen shows what is on stage right now and greys out
 * what is behind us. On the *host's* edition — and only there — each row also carries
 * controls to announce the day and buttons to rearrange what is still to come, because
 * that link is the one the organizer handed the person running the show.
 */
export function PublicProgramPage(): React.JSX.Element {
  const { slug } = useParams();
  const { data: program, isLoading, isError } = usePublicProgram(slug);

  if (isLoading) {
    return (
      <div className="flex min-h-svh items-center justify-center bg-background p-6">
        <LoadingState label="Загружаем программу…" />
      </div>
    );
  }

  if (isError || !program) {
    return (
      <div className="flex min-h-svh items-center justify-center bg-background p-6">
        <div className="w-full max-w-md">
          <EmptyState
            title="Программа не найдена"
            description="Ссылка недействительна или программа больше не опубликована. Попросите организатора прислать актуальную ссылку."
          />
        </div>
      </div>
    );
  }

  return <PublicProgramTable slug={slug ?? ""} program={program} />;
}

function PublicProgramTable({
  slug,
  program,
}: {
  slug: string;
  program: PublicProgram;
}): React.JSX.Element {
  const heading = [program.competitionTitle, program.nomination].filter(Boolean).join(" · ");
  const isHost = program.controlsRunningOrder;
  const columnKeys = program.columns.map((column) => column.key);

  return (
    // This page has no shell to clip for it, so it clips for itself: the table below is as
    // wide as its published columns, and the excess must scroll inside the table, never
    // sideways across the whole page.
    <div className="min-h-svh overflow-x-clip bg-background">
      {/* `min-w-0` on the column: a flex item sizes to its content by default, and the wide
          table would push the whole page sideways instead of scrolling inside itself. */}
      <div className="mx-auto flex w-full min-w-0 max-w-6xl flex-col gap-6 px-4 py-8 sm:px-6 md:py-12">
        <header className="space-y-2">
          {heading ? (
            <p className="font-medium text-muted-foreground text-xs uppercase tracking-[0.18em]">
              {heading}
            </p>
          ) : null}
          <div className="flex flex-wrap items-baseline gap-2">
            <h1 className="font-bold text-3xl text-foreground tracking-tight sm:text-4xl">
              {program.name}
            </h1>
            {isHost ? <Badge variant="secondary">Управление программой</Badge> : null}
          </div>
          <p className="text-muted-foreground text-sm">
            {program.rows.length > 0
              ? `Пунктов: ${program.rows.length} · Продолжительность: ${formatSpan(program.totalSeconds)}`
              : "Пока ни один пункт не опубликован"}
            {program.startsAt ? ` · Начало: ${formatClock(program.startsAt)}` : ""}
          </p>
          {isHost ? (
            <p className="text-muted-foreground text-xs">
              Отмечайте номера по ходу программы — участники и экран у сцены видят это сразу.
            </p>
          ) : null}
        </header>

        {program.rows.length === 0 ? (
          <EmptyState
            title="Программа пуста"
            description="Организатор ещё не добавил пункты в эту программу."
          />
        ) : (
          // `relative` is load-bearing, not decoration. `sr-only` is `position: absolute`,
          // and the host column's screen-reader header sits at the far right of a table that
          // can be 2600px wide. Without a positioned ancestor its containing block is the
          // document, so this scroll container never clips it and that one 1px span drags the
          // whole page's scroll width out with it. `shared/ui/DataTable` carries the same
          // `relative` for the same reason.
          <div className="scrollbar-custom relative w-full max-w-full overflow-x-auto rounded-lg border border-border">
            {/* `w-max min-w-full`: may exceed the container (that is what scrolls) but never
                leaves it narrower than the space available. */}
            <table className="w-max min-w-full border-collapse text-left">
              <caption className="sr-only">{program.name}</caption>
              <thead>
                <tr className="border-border border-b bg-muted/50">
                  {program.columns.map((column) => (
                    <th
                      key={column.key}
                      scope="col"
                      className="whitespace-nowrap px-3 py-2.5 font-medium text-muted-foreground text-xs uppercase tracking-wide"
                    >
                      {column.label}
                    </th>
                  ))}
                  {isHost ? (
                    <th scope="col" className="px-3 py-2.5 text-right">
                      <span className="sr-only">Управление</span>
                    </th>
                  ) : null}
                </tr>
              </thead>
              <tbody>
                {program.rows.map((row, index) => (
                  <ProgramTableRow
                    // A public row carries no id unless this is the host's edition, so its
                    // own published content identifies it. Safe here: the table is
                    // re-rendered whole from each poll.
                    key={row.id ?? `${row.kind}${row.cells.join("")}`}
                    slug={slug}
                    row={row}
                    rows={program.rows}
                    index={index}
                    columns={columnKeys}
                    isHost={isHost}
                  />
                ))}
              </tbody>
            </table>
          </div>
        )}

        <footer className="pt-4 text-center text-muted-foreground text-xs">
          Программа обновляется автоматически · «{APP_NAME}»
        </footer>
      </div>
    </div>
  );
}

function ProgramTableRow({
  slug,
  row,
  rows,
  index,
  columns,
  isHost,
}: {
  slug: string;
  row: PublicProgramRow;
  rows: PublicProgramRow[];
  index: number;
  columns: string[];
  isHost: boolean;
}): React.JSX.Element {
  const isPerformance = row.kind === "PERFORMANCE";
  const onStage = row.progress === "ON_STAGE";
  const behindUs = row.progress === "PERFORMED" || row.progress === "SKIPPED";

  return (
    <tr
      data-testid="program-row"
      data-progress={row.progress}
      className={
        onStage
          ? "border-border border-b bg-primary/10 last:border-0"
          : behindUs
            ? "border-border border-b text-muted-foreground last:border-0"
            : isPerformance
              ? "border-border border-b last:border-0"
              : "border-border border-b bg-muted/40 last:border-0"
      }
    >
      {row.cells.map((cell, cellIndex) => {
        const column = columns[cellIndex];
        const emphasise = column === "TIME" || (column === "TITLE" && !isPerformance);
        return (
          <td
            key={column ?? String(cellIndex)}
            className={
              emphasise
                ? "whitespace-nowrap px-3 py-3 font-semibold text-base tabular-nums"
                : "px-3 py-3 text-sm"
            }
          >
            <span className={behindUs ? "line-through decoration-1" : undefined}>
              {cell || <span className="text-muted-foreground">—</span>}
            </span>
            {/* The state is announced beside the first column so it is legible from the
                hall without hunting for a status column that may not be published. */}
            {cellIndex === 0 && onStage ? (
              <Badge variant="success" className="ml-2">
                Сейчас
              </Badge>
            ) : null}
          </td>
        );
      })}
      {isHost ? (
        <td className="px-3 py-3">
          <HostControls slug={slug} row={row} rows={rows} index={index} />
        </td>
      ) : null}
    </tr>
  );
}

function HostControls({
  slug,
  row,
  rows,
  index,
}: {
  slug: string;
  row: PublicProgramRow;
  rows: PublicProgramRow[];
  index: number;
}): React.JSX.Element {
  const setProgress = useSetRowProgress(slug);
  const reorder = useHostReorder(slug);
  const busy = setProgress.isPending || reorder.isPending;
  const label = row.cells.find((cell) => cell.trim().length > 0) ?? "пункт";

  const mark = (progress: PublicProgramProgress) =>
    setProgress.mutate(
      { itemId: row.id ?? "", progress },
      { onError: () => toast.error("Не удалось отметить номер") },
    );

  const move = (to: number) => {
    // The endpoint takes the complete new order, so send what is on screen.
    const ids = rows.map((item) => item.id ?? "");
    if (to < 0 || to >= ids.length || ids.some((id) => !id)) {
      return;
    }
    const next = [...ids];
    const [moved] = next.splice(index, 1);
    next.splice(to, 0, moved as string);
    reorder.mutate(next, { onError: () => toast.error("Не удалось изменить порядок") });
  };

  return (
    <div className="flex items-center justify-end gap-1">
      <Button
        variant={row.progress === "ON_STAGE" ? "primary" : "outline"}
        size="xs"
        aria-label={`На сцене: ${label}`}
        disabled={busy}
        onClick={() => mark("ON_STAGE")}
      >
        <Play className="size-4" />
      </Button>
      <Button
        variant="ghost"
        size="xs"
        aria-label={`Выступил: ${label}`}
        disabled={busy}
        onClick={() => mark("PERFORMED")}
      >
        <Check className="size-4" />
      </Button>
      <Button
        variant="ghost"
        size="xs"
        aria-label={`Пропустить: ${label}`}
        disabled={busy}
        onClick={() => mark("SKIPPED")}
      >
        <SkipForward className="size-4" />
      </Button>
      <Button
        variant="ghost"
        size="xs"
        aria-label={`Вверх: ${label}`}
        disabled={busy || index === 0}
        onClick={() => move(index - 1)}
      >
        <ArrowUp className="size-4" />
      </Button>
      <Button
        variant="ghost"
        size="xs"
        aria-label={`Вниз: ${label}`}
        disabled={busy || index === rows.length - 1}
        onClick={() => move(index + 1)}
      >
        <ArrowDown className="size-4" />
      </Button>
    </div>
  );
}
