import {
  ArrowDown,
  ArrowUp,
  Ban,
  Check,
  EyeOff,
  MoreHorizontal,
  NotebookPen,
  Play,
  SkipForward,
  UserCheck,
} from "lucide-react";
import { useEffect, useRef, useState } from "react";
import { useParams } from "react-router";

import {
  blockLine,
  moveRowNextTo,
  moveRowTo,
  type PublicProgram,
  type PublicProgramColumn,
  type PublicProgramProgress,
  type PublicProgramRow,
  rowNumber,
  useHostReorder,
  usePublicProgram,
  useSetRowBackstage,
  useSetRowNote,
  useSetRowProgress,
} from "@/features/public-program";
import { APP_NAME } from "@/shared/config";
import { cn, formatClock, formatSpan } from "@/shared/lib";
import { useSeo } from "@/shared/seo";
import {
  Badge,
  Button,
  EmptyState,
  LoadingState,
  Popover,
  PopoverContent,
  PopoverTrigger,
  Textarea,
  toast,
} from "@/shared/ui";
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
 *
 * Her edition carries one more thing: a layer that is hers alone. Who has turned up
 * behind the stage, and whatever she wrote to herself about an act, are marks the backend
 * renders into no other edition's payload — and the columns that are about somebody who
 * is not on stage stay covered until she taps them, because backstage is a corridor and
 * she is not the only person reading her phone.
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
              Отмечайте номера по ходу программы — участники и экран у сцены видят это сразу. «За
              сценой», пометки и скрытые ячейки видны только по вашей ссылке.
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
                      columns={program.columns}
                      columnKeys={columnKeys}
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
  columnKeys,
  isHost,
}: {
  slug: string;
  row: PublicProgramRow;
  rows: PublicProgramRow[];
  index: number;
  columns: PublicProgramColumn[];
  columnKeys: string[];
  isHost: boolean;
}): React.JSX.Element {
  const isPerformance = row.kind === "PERFORMANCE";
  const onStage = row.progress === "ON_STAGE";
  const cancelled = row.progress === "CANCELLED";
  const behindUs = row.progress === "PERFORMED" || row.progress === "SKIPPED" || cancelled;
  const block = isPerformance ? null : blockLine(row, columnKeys);
  // The background half of the row's tone, repeated on the pinned cells. They need an
  // opaque layer of their own — the cells sliding underneath a pinned one are painted
  // below it, and a 10%-tint cell would show every one of them through itself.
  const tint = onStage ? "bg-primary/10" : behindUs || isPerformance ? "" : "bg-muted/40";
  const tone = onStage
    ? "bg-primary/10"
    : behindUs
      ? "text-muted-foreground"
      : isPerformance
        ? ""
        : "bg-muted/40";
  // Where this row's state is announced: the first column wide enough to hold a word.
  //
  // Not «№», which is pinned on the host's screen and must stay two characters wide, and
  // not «Время», which is four: a «Номер отменён» dropped into either one overflows it,
  // gets clipped by the column beside it, and takes the clock down with it. Both were
  // tried on a real seven-column host edition, and both looked exactly as broken as that
  // sounds. The participant's name is the first column with room, and it is also where a
  // reader looking for *which* act this is already is.
  const badgeAt = Math.max(
    0,
    columns.findIndex((column) => column.key !== "POSITION" && column.key !== "TIME"),
  );
  const note = isHost ? (row.note ?? "") : "";

  const badges = (
    <>
      {onStage ? <Badge variant="success">Сейчас</Badge> : null}
      {/* Said in words, not left to a strikethrough. An act pulled on the morning —
          ill, stuck on the road — reads the same as one that merely has not happened
          yet if all that marks it is a line through the name. */}
      {cancelled ? <Badge variant="danger">Номер отменён</Badge> : null}
      {row.backstage ? <Badge variant="info">За сценой</Badge> : null}
    </>
  );

  return (
    <>
      <tr
        data-testid="program-row"
        data-progress={row.progress}
        className={cn(tone, note ? "" : "border-border border-b last:border-0")}
      >
        {block !== null ? (
          // A break is not an act with blank cells, so it is not drawn as one: one line
          // across the whole table, pinned to the left edge, where it is readable without
          // scrolling a table cut wide for the acts around it.
          <td colSpan={columnKeys.length} className="px-2 py-1.5 sm:px-3">
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
              {badges}
            </div>
          </td>
        ) : (
          row.cells.map((cell, cellIndex) => (
            <ProgramCell
              key={columns[cellIndex]?.key ?? String(cellIndex)}
              cell={cell}
              column={columns[cellIndex]}
              // The first column travels with the reader on the host's screen: a
              // programme cut for backstage is wider than any phone, and a row scrolled
              // two columns to the right is a row she can no longer name.
              pinned={isHost && cellIndex === 0}
              maskable={isHost}
              tint={tint}
              struck={behindUs}
            >
              {/* The state is announced beside the first column the host can read without
                  scrolling, so it is legible at a glance without hunting for a status
                  column that may not be published at all. */}
              {cellIndex === badgeAt ? badges : null}
            </ProgramCell>
          ))
        )}
        {isHost ? (
          <PinnedCell tint={tint} className="right-0 border-border border-l px-2 py-1.5 sm:px-3">
            <HostControls slug={slug} row={row} rows={rows} index={index} columns={columnKeys} />
          </PinnedCell>
        ) : null}
      </tr>
      {note ? (
        // A line of its own rather than a cell: the note is the host's working surface
        // and runs to a sentence, and a sentence inside a 26-character column is six
        // lines of two words. Pinned left like a break, so it is readable wherever the
        // table happens to be scrolled to.
        <tr data-testid="program-note" className={cn(tone, "border-border border-b last:border-0")}>
          <td colSpan={columnKeys.length + 1} className="px-2 pb-1.5 sm:px-3">
            <div className="sticky left-2 flex w-fit max-w-[60ch] items-start gap-1.5 text-xs sm:left-3">
              <NotebookPen className="mt-0.5 size-3.5 shrink-0" aria-hidden="true" />
              <span className="[overflow-wrap:anywhere]">{note}</span>
            </div>
          </td>
        </tr>
      ) : null}
    </>
  );
}

/**
 * One cell of an act's row: its text, whatever badge belongs beside it, and the two
 * things the host's edition does differently — the first column is pinned, and a column
 * about somebody off the stage arrives covered.
 */
function ProgramCell({
  cell,
  column,
  pinned,
  maskable,
  tint,
  struck,
  children,
}: {
  cell: string;
  column: PublicProgramColumn | undefined;
  pinned: boolean;
  /** Whether a sensitive column should be covered here — the host's edition only. */
  maskable: boolean;
  tint: string;
  struck: boolean;
  children: React.ReactNode;
}): React.JSX.Element {
  const padding =
    column?.key === "TIME"
      ? "whitespace-nowrap px-2 py-1.5 align-top font-semibold text-sm tabular-nums sm:px-3"
      : "px-2 py-1.5 align-top text-sm sm:px-3";
  const body = (
    // The cap is what keeps the table narrow: a collective with six surnames in its name,
    // or a title that is half a sentence, wraps onto a second and a third line instead of
    // widening its column and pushing everything to the right of it off the screen.
    // `align-top` above is its other half — beside a cell that wrapped, the short ones
    // still start at the first line.
    <div className="flex max-w-[26ch] flex-wrap items-baseline gap-x-1.5 [overflow-wrap:anywhere]">
      {maskable && column?.sensitive && cell.trim() !== "" ? (
        <SensitiveCell value={cell} label={column.label} struck={struck} />
      ) : (
        <span className={struck ? "line-through decoration-1" : undefined}>
          {cell || <span className="text-muted-foreground">—</span>}
        </span>
      )}
      {children}
    </div>
  );

  if (pinned) {
    return (
      <PinnedCell tint={tint} className={cn("left-0 border-border border-r", padding)}>
        {body}
      </PinnedCell>
    );
  }
  return <td className={padding}>{body}</td>;
}

/**
 * A table cell that stays put while the rest of the table scrolls under it.
 *
 * The tint is painted by an overlay rather than by the cell's own background, because
 * the cell's background has to be opaque: a pinned cell is a positioned element, every
 * other cell in the row is painted below it, and a background at 10% would show the
 * participant's name sliding through the number pinned on top of it.
 */
function PinnedCell({
  tint,
  className,
  children,
}: {
  tint: string;
  className?: string;
  children: React.ReactNode;
}): React.JSX.Element {
  return (
    <td className={cn("sticky z-10 bg-background align-top", className)}>
      {tint ? (
        <span aria-hidden="true" className={cn("pointer-events-none absolute inset-0", tint)} />
      ) : null}
      <div className="relative">{children}</div>
    </td>
  );
}

/**
 * A cell the host has to ask for: a phone number, a comment about a child.
 *
 * Backstage is a corridor, and the programme is read there with other people's parents
 * standing behind her. The organizer published these columns to the host because she
 * genuinely needs them — to ring a teacher who is not in the hall, to know that a child
 * answers to a different name — and none of that is a reason for the row behind her to
 * read a phone number over her shoulder. So the cell is covered until it is wanted and
 * goes back under cover with a second tap.
 *
 * Covered, not withheld: the value is in the payload, and anybody who opens the network
 * tab has it. This is proof against a glance, which is the threat that actually happens.
 */
function SensitiveCell({
  value,
  label,
  struck,
}: {
  value: string;
  label: string;
  struck: boolean;
}): React.JSX.Element {
  const [shown, setShown] = useState(false);

  if (!shown) {
    return (
      <Button
        variant="outline"
        size="xs"
        iconOnly
        className="size-6"
        aria-label={`Показать «${label}»`}
        onClick={() => setShown(true)}
      >
        <MoreHorizontal className="size-3.5" />
      </Button>
    );
  }
  // Revealed, the value is text and not a control: a button around it carries the
  // button's own `shrink-0` and `inline-flex`, which in a column cut for a phone number
  // makes the sentence wider than its column and lets the pinned column beside it eat
  // the overflow. The cover goes back on from the icon next to it.
  return (
    <>
      <span className={cn("[overflow-wrap:anywhere]", struck && "line-through decoration-1")}>
        {value}
      </span>
      <Button
        variant="ghost"
        size="xs"
        iconOnly
        className="size-5 text-muted-foreground"
        aria-label={`Скрыть «${label}»`}
        onClick={() => setShown(false)}
      >
        <EyeOff className="size-3" />
      </Button>
    </>
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
  const setBackstage = useSetRowBackstage(slug);
  const setNote = useSetRowNote(slug);
  const reorder = useHostReorder(slug);
  const busy =
    setProgress.isPending || setBackstage.isPending || setNote.isPending || reorder.isPending;
  const label = row.cells.find((cell) => cell.trim().length > 0) ?? "пункт";
  const itemId = row.id ?? "";
  const cancelled = row.progress === "CANCELLED";
  const backstage = row.backstage === true;

  const mark = (progress: PublicProgramProgress) =>
    setProgress.mutate(
      { itemId, progress },
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
    // A fixed width that wraps rather than one long bar: this column is pinned to the
    // right of the screen now, and nine controls in a line would pin a third of a phone
    // with it. Five and four, in the order the day uses them.
    <div className="flex w-[150px] flex-wrap items-center justify-end gap-0.5">
      <Button
        variant={row.progress === "ON_STAGE" ? "primary" : "outline"}
        size="xs"
        iconOnly
        aria-label={`На сцене: ${label}`}
        disabled={busy}
        onClick={() => mark("ON_STAGE")}
      >
        <Play className="size-3.5" />
      </Button>
      <Button
        variant="ghost"
        size="xs"
        iconOnly
        aria-label={`Выступил: ${label}`}
        disabled={busy}
        onClick={() => mark("PERFORMED")}
      >
        <Check className="size-3.5" />
      </Button>
      <Button
        variant="ghost"
        size="xs"
        iconOnly
        aria-label={`Пропустить: ${label}`}
        disabled={busy}
        onClick={() => mark("SKIPPED")}
      >
        <SkipForward className="size-3.5" />
      </Button>
      {/* Both ways round. An act is pulled because somebody is ill and reinstated because
          they turned up after all, and the second happens often enough that the only road
          back must not be «на сцене». */}
      <Button
        variant={cancelled ? "danger" : "ghost"}
        size="xs"
        iconOnly
        aria-label={cancelled ? `Вернуть в программу: ${label}` : `Отменить номер: ${label}`}
        disabled={busy}
        onClick={() => mark(cancelled ? "PENDING" : "CANCELLED")}
      >
        <Ban className="size-3.5" />
      </Button>
      {/* Hers alone, and the answer to a question the running order cannot hold: «кто
          уже здесь». Nothing is published by it and no other screen changes. */}
      <Button
        variant={backstage ? "secondary" : "ghost"}
        size="xs"
        iconOnly
        aria-label={backstage ? `Снять «за сценой»: ${label}` : `За сценой: ${label}`}
        disabled={busy}
        onClick={() =>
          setBackstage.mutate(
            { itemId, backstage: !backstage },
            { onError: () => toast.error("Не удалось отметить, кто за сценой") },
          )
        }
      >
        <UserCheck className="size-3.5" />
      </Button>
      <HostNoteField
        label={label}
        note={row.note ?? ""}
        disabled={busy}
        onSave={(note) =>
          setNote.mutate(
            { itemId, note },
            { onError: () => toast.error("Не удалось сохранить пометку") },
          )
        }
      />
      <Button
        variant="ghost"
        size="xs"
        iconOnly
        aria-label={`Вверх: ${label}`}
        disabled={busy || index === 0}
        onClick={() => move(index - 1)}
      >
        <ArrowUp className="size-3.5" />
      </Button>
      <Button
        variant="ghost"
        size="xs"
        iconOnly
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

/**
 * «Пометка» — what the host writes to herself against one act.
 *
 * The platform had nowhere to put this, so until now it went on a printed programme in
 * biro — «зовут Алиса, не Алла», «папа подойдёт к сцене», «поёт вторым, не первым» — and
 * the printed programme gets left on a chair. It lives on her link instead: she can lose
 * the phone and open the same link on another one, and nobody else's edition has a field
 * for it.
 *
 * The draft is local until she saves, and resyncs with the row whenever the form is shut:
 * a note written on her other phone arrives on the next poll, and must not be masked by
 * a box she opened and walked away from.
 */
function HostNoteField({
  label,
  note,
  disabled,
  onSave,
}: {
  label: string;
  note: string;
  disabled: boolean;
  onSave: (note: string) => void;
}): React.JSX.Element {
  const [open, setOpen] = useState(false);
  const [draft, setDraft] = useState(note);

  useEffect(() => {
    if (!open) {
      setDraft(note);
    }
  }, [note, open]);

  const save = (value: string) => {
    onSave(value);
    setOpen(false);
  };

  return (
    <Popover open={open} onOpenChange={setOpen}>
      <PopoverTrigger asChild>
        <Button
          variant={note ? "secondary" : "ghost"}
          size="xs"
          iconOnly
          aria-label={note ? `Изменить пометку: ${label}` : `Пометка: ${label}`}
          disabled={disabled}
        >
          <NotebookPen className="size-3.5" />
        </Button>
      </PopoverTrigger>
      <PopoverContent align="end" className="w-72">
        <form
          className="flex flex-col gap-3"
          onSubmit={(event) => {
            event.preventDefault();
            save(draft.trim());
          }}
        >
          <Textarea
            label="Пометка для себя"
            description="Видна только по вашей ссылке."
            rows={3}
            maxLength={500}
            value={draft}
            onChange={(event) => setDraft(event.target.value)}
          />
          <div className="flex gap-2">
            <Button
              type="button"
              size="sm"
              variant="outline"
              className="flex-1"
              disabled={note === "" || disabled}
              onClick={() => save("")}
            >
              Очистить
            </Button>
            <Button
              type="submit"
              size="sm"
              className="flex-1"
              disabled={disabled || draft.trim() === note}
            >
              Сохранить
            </Button>
          </div>
        </form>
      </PopoverContent>
    </Popover>
  );
}
