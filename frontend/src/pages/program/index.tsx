import { ArrowDown, ArrowUp, Check, Play, SkipForward } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import { useParams } from "react-router";

import {
  blockLine,
  moveRowNextTo,
  moveRowTo,
  type PublicProgram,
  type PublicProgramProgress,
  type PublicProgramRow,
  rowNumber,
  useHostReorder,
  usePublicProgram,
  useSetRowProgress,
} from "@/features/public-program";
import { APP_NAME } from "@/shared/config";
import { formatClock, formatSpan } from "@/shared/lib";
import { useSeo } from "@/shared/seo";
import { Badge, Button, EmptyState, LoadingState, toast } from "@/shared/ui";
import { type MovePlacement, MoveToNumber } from "@/widgets/move-to-number";

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
 * controls to announce the day and buttons to rearrange what is still to come — a step at
 * a time with the arrows, or straight to a named number when an act has to jump the queue
 * outright — because that link is the one the organizer handed the person running the show.
 */
export function PublicProgramPage(): React.JSX.Element {
  const { slug } = useParams();
  const { data: program, isLoading, isError } = usePublicProgram(slug);
  // Reachable by anyone with the link, indexed by no one: the running order names
  // every performing child. Sharing it with the sound engineer is the purpose;
  // making it findable by a child's name is not.
  useSeo({ title: "Программа выступлений", robots: "noindex" });

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
  const tableScrollRef = useRef<HTMLDivElement>(null);

  return (
    // This page has no shell to clip for it, so it clips for itself: the table below is as
    // wide as its published columns, and the excess must scroll inside the table, never
    // sideways across the whole page.
    <div className="min-h-svh overflow-x-clip bg-background">
      {/* `min-w-0` on the column: a flex item sizes to its content by default, and the wide
          table would push the whole page sideways instead of scrolling inside itself. */}
      <div className="mx-auto flex w-full min-w-0 max-w-6xl flex-col gap-3 px-2 py-4 sm:px-4 sm:py-6">
        {/* The page is read off a phone backstage and off a screen beside it, so the
            chrome is kept to a line or two: every row of padding here is a performance
            that falls below the fold. */}
        <header className="space-y-1">
          {heading ? (
            <p className="font-medium text-muted-foreground text-xs uppercase tracking-[0.18em]">
              {heading}
            </p>
          ) : null}
          <div className="flex flex-wrap items-baseline gap-2">
            <h1 className="font-bold text-foreground text-xl tracking-tight sm:text-2xl">
              {program.name}
            </h1>
            {isHost ? <Badge variant="secondary">Управление программой</Badge> : null}
          </div>
          <p className="text-muted-foreground text-xs">
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
          <div className="flex min-w-0 flex-col gap-1">
            <TopScrollbar targetRef={tableScrollRef} />
            {/* `relative` is load-bearing, not decoration. `sr-only` is `position: absolute`,
                and the host column's screen-reader header sits at the far right of a table that
                can be 2600px wide. Without a positioned ancestor its containing block is the
                document, so this scroll container never clips it and that one 1px span drags the
                whole page's scroll width out with it. `shared/ui/DataTable` carries the same
                `relative` for the same reason. */}
            <div
              ref={tableScrollRef}
              className="scrollbar-custom relative w-full max-w-full overflow-x-auto rounded-lg border border-border"
            >
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
                        className="px-2 py-1.5 align-bottom font-medium text-muted-foreground text-[11px] uppercase tracking-wide sm:px-3"
                      >
                        {/* Capped like the cells below it: a column the organizer named
                            «Ответственный за фонограмму» would otherwise set the column's
                            width from its header alone. */}
                        <span className="block max-w-[26ch] [overflow-wrap:anywhere]">
                          {column.label}
                        </span>
                      </th>
                    ))}
                    {isHost ? (
                      <th scope="col" className="px-2 py-1.5 text-right sm:px-3">
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
          </div>
        )}

        <footer className="pt-1 text-center text-[11px] text-muted-foreground">
          Программа обновляется автоматически · «{APP_NAME}»
        </footer>
      </div>
    </div>
  );
}

/**
 * A second horizontal scrollbar, mirrored above the programme table.
 *
 * A published programme can be 2600px wide and dozens of rows long, so the table's own
 * bar sits at the bottom of something that runs well past the fold: to reach the columns
 * on the right the reader first has to scroll the page *down*, past every act, to find
 * the control that moves it. This rail is that same control, kept where the table starts.
 *
 * Desktop only. On a phone the table is dragged sideways with a finger, the bar is an
 * overlay hint that fades at rest, and a duplicate would cost a row of a page that is
 * read backstage with the next act already walking on.
 */
function TopScrollbar({
  targetRef,
}: {
  targetRef: React.RefObject<HTMLDivElement | null>;
}): React.JSX.Element {
  const railRef = useRef<HTMLDivElement>(null);
  // The table's scroll width, or 0 when it fits — a rail with nothing left to scroll is
  // hidden rather than drawn as an empty strip above a narrow programme.
  const [scrollWidth, setScrollWidth] = useState(0);

  useEffect(() => {
    const target = targetRef.current;
    if (!target) return;

    const measure = (): void => {
      setScrollWidth(target.scrollWidth > target.clientWidth ? target.scrollWidth : 0);
    };
    measure();

    const observer = new ResizeObserver(measure);
    // Both boxes: the container changes with the window, the table with the programme —
    // a poll that adds an act or widens a column moves the table without touching the
    // container around it.
    observer.observe(target);
    const table = target.firstElementChild;
    if (table) observer.observe(table);
    return () => observer.disconnect();
  }, [targetRef]);

  useEffect(() => {
    const target = targetRef.current;
    const rail = railRef.current;
    if (!target || !rail) return;

    // Each handler writes only when the two differ, which is what stops the pair from
    // echoing a scroll back and forth at each other forever.
    const follow = (from: HTMLElement, to: HTMLElement) => (): void => {
      if (to.scrollLeft !== from.scrollLeft) to.scrollLeft = from.scrollLeft;
    };
    const railToTable = follow(rail, target);
    const tableToRail = follow(target, rail);
    rail.scrollLeft = target.scrollLeft;

    rail.addEventListener("scroll", railToTable, { passive: true });
    target.addEventListener("scroll", tableToRail, { passive: true });
    return () => {
      rail.removeEventListener("scroll", railToTable);
      target.removeEventListener("scroll", tableToRail);
    };
  }, [targetRef]);

  return (
    // Hidden from assistive tech and from the tab order: it moves the same table the
    // element below it moves, and a keyboard already scrolls that one.
    //
    // Always mounted, even when there is nothing to scroll: the effect above needs the
    // element to attach to, and a rail that comes and goes with the programme's width
    // would have to re-bind its listeners on every poll.
    <div
      ref={railRef}
      aria-hidden="true"
      className={
        scrollWidth === 0
          ? "hidden"
          : "scrollbar-custom hidden w-full max-w-full overflow-x-auto overflow-y-hidden sm:block"
      }
    >
      <div className="h-px" style={{ width: scrollWidth }} />
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
  const block = isPerformance ? null : blockLine(row, columns);

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
      {block !== null ? (
        // A break is not an act with blank cells, so it is not drawn as one: one line
        // across the whole table, pinned to the left edge, where it is readable without
        // scrolling a table cut wide for the acts around it.
        <td colSpan={columns.length} className="px-2 py-1.5 sm:px-3">
          {/* Pinned at the cell's own padding, not at `left-0`: scrolled right, the line
              keeps the gap it has at rest instead of riding the table's border. */}
          <div className="sticky left-2 flex w-fit flex-wrap items-baseline gap-x-2 gap-y-0.5 sm:left-3">
            {block.time ? (
              <span className="font-semibold text-sm tabular-nums">{block.time}</span>
            ) : null}
            <span
              className={
                behindUs
                  ? "font-medium text-sm uppercase tracking-wide line-through decoration-1"
                  : "font-medium text-sm uppercase tracking-wide"
              }
            >
              {block.title || "—"}
            </span>
            {block.extras.length > 0 ? (
              <span className="text-muted-foreground text-xs">{block.extras.join(" · ")}</span>
            ) : null}
            {onStage ? <Badge variant="success">Сейчас</Badge> : null}
          </div>
        </td>
      ) : (
        row.cells.map((cell, cellIndex) => {
          const column = columns[cellIndex];
          return (
            <td
              key={column ?? String(cellIndex)}
              className={
                column === "TIME"
                  ? "whitespace-nowrap px-2 py-1.5 align-top font-semibold text-sm tabular-nums sm:px-3"
                  : "px-2 py-1.5 align-top text-sm sm:px-3"
              }
            >
              {/* The cap is what keeps the table narrow: a collective with six surnames in
                  its name, or a title that is half a sentence, wraps onto a second and a
                  third line instead of widening its column and pushing everything to the
                  right of it off the screen. `align-top` above is its other half — beside a
                  cell that wrapped, the short ones still start at the first line. */}
              <div className="flex max-w-[26ch] flex-wrap items-baseline gap-x-1.5 [overflow-wrap:anywhere]">
                <span className={behindUs ? "line-through decoration-1" : undefined}>
                  {cell || <span className="text-muted-foreground">—</span>}
                </span>
                {/* The state is announced beside the first column so it is legible from the
                    hall without hunting for a status column that may not be published. */}
                {cellIndex === 0 && onStage ? <Badge variant="success">Сейчас</Badge> : null}
              </div>
            </td>
          );
        })
      )}
      {isHost ? (
        <td className="px-2 py-1.5 sm:px-3">
          <HostControls slug={slug} row={row} rows={rows} index={index} columns={columns} />
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
  columns,
}: {
  slug: string;
  row: PublicProgramRow;
  rows: PublicProgramRow[];
  index: number;
  columns: string[];
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

  // The endpoint takes the complete new order, so send what is on screen.
  const send = (next: string[] | null) => {
    if (next !== null) {
      reorder.mutate(next, { onError: () => toast.error("Не удалось изменить порядок") });
    }
  };

  const move = (to: number) => send(moveRowTo(rows, index, to));

  /**
   * Move next to the number the host just read out, answering whether it could be done —
   * the form stays open on a number the programme does not carry, so a typo made while
   * the hall waits costs a keystroke rather than the whole move.
   */
  const placeNextTo = (number: number, placement: MovePlacement): boolean => {
    const next = moveRowNextTo(rows, columns, index, number, placement);
    if (next === null) {
      toast.error(`В программе нет №${number}`);
      return false;
    }
    send(next);
    return true;
  };

  return (
    <div className="flex items-center justify-end gap-0.5">
      <Button
        variant={row.progress === "ON_STAGE" ? "primary" : "outline"}
        size="xs"
        aria-label={`На сцене: ${label}`}
        disabled={busy}
        onClick={() => mark("ON_STAGE")}
      >
        <Play className="size-3.5" />
      </Button>
      <Button
        variant="ghost"
        size="xs"
        aria-label={`Выступил: ${label}`}
        disabled={busy}
        onClick={() => mark("PERFORMED")}
      >
        <Check className="size-3.5" />
      </Button>
      <Button
        variant="ghost"
        size="xs"
        aria-label={`Пропустить: ${label}`}
        disabled={busy}
        onClick={() => mark("SKIPPED")}
      >
        <SkipForward className="size-3.5" />
      </Button>
      <Button
        variant="ghost"
        size="xs"
        aria-label={`Вверх: ${label}`}
        disabled={busy || index === 0}
        onClick={() => move(index - 1)}
      >
        <ArrowUp className="size-3.5" />
      </Button>
      <Button
        variant="ghost"
        size="xs"
        aria-label={`Вниз: ${label}`}
        disabled={busy || index === rows.length - 1}
        onClick={() => move(index + 1)}
      >
        <ArrowDown className="size-3.5" />
      </Button>
      <MoveToNumber
        label={label}
        current={rowNumber(row, index, columns)}
        atStart={index === 0}
        atEnd={index === rows.length - 1}
        disabled={busy}
        onPlace={placeNextTo}
        onMoveToStart={() => move(0)}
        onMoveToEnd={() => move(rows.length - 1)}
      />
    </div>
  );
}
