import {
  ArrowDown,
  ArrowLeft,
  ArrowRight,
  ArrowUp,
  Clapperboard,
  Columns3,
  Copy,
  FileDown,
  GripVertical,
  Link2,
  ListOrdered,
  Music,
  PanelLeftClose,
  PanelLeftOpen,
  Plus,
  Send,
  Trash2,
  Wand2,
} from "lucide-react";
import { useEffect, useMemo, useState } from "react";

import { useCompetitionDetail, useCompetitionsList } from "@/features/competitions";
import {
  BUFFER_PRESETS,
  type ColumnKey,
  DEFAULT_EXPORT_COLUMNS,
  DEFAULT_SHARE_COLUMNS,
  downloadProgramMedia,
  downloadProgramMusic,
  downloadProgramPdf,
  GROUPING_AXES,
  GROUPING_AXIS_LABELS,
  type GroupingAxis,
  groupRuns,
  ITEM_KIND_LABELS,
  itemCell,
  itemNumber,
  moveBlock,
  moveItem,
  moveItemNextTo,
  PROGRESS_LABELS,
  type Program,
  type ProgramColumn,
  type ProgramColumnKey,
  type ProgramGroup,
  type ProgramItem,
  type ProgramShare,
  useAddBlock,
  useAddColumn,
  useAddPerformance,
  useAnnounceShare,
  useArrangeProgram,
  useCreateProgram,
  useCreateShare,
  useEditItem,
  useFillCells,
  useFillProgram,
  useProgram,
  useProgramCandidates,
  usePrograms,
  useRemoveColumn,
  useRemoveItem,
  useRemoveShare,
  useRenameColumn,
  useRenumberItems,
  useReorderItems,
  useUpdateProgram,
} from "@/features/program-builder";
import { ArrangeProgramDialog } from "@/features/program-builder/ui/arrange-dialog";
import {
  festivalInputToIso,
  formatClock,
  formatDuration,
  formatSpan,
  isoToFestivalInput,
} from "@/shared/lib";
import {
  Alert,
  Badge,
  Button,
  Card,
  CardContent,
  Checkbox,
  DateTimePicker,
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  Divider,
  EmptyState,
  Input,
  LoadingState,
  PageContainer,
  PageContent,
  PageDescription,
  PageHeader,
  PageTitle,
  Popover,
  PopoverContent,
  PopoverTrigger,
  Select,
  Textarea,
  toast,
} from "@/shared/ui";
import { type MovePlacement, MoveToNumber } from "@/widgets/move-to-number";

/**
 * `/staff/program` — the programme constructor.
 *
 * Three columns of work: pick the competition and the programme (left), arrange the
 * running order and watch the times recompute (middle), publish links for the people
 * who run the day (right).
 *
 * Reordering is deliberately buttons-and-not-drag: the endpoint takes the complete new
 * order, so every move sends exactly what the organizer sees, and drag & drop between
 * programmes is explicitly a later step.
 */
export function StaffProgramPage(): React.JSX.Element {
  const competitions = useCompetitionsList();
  const [competitionId, setCompetitionId] = useState<string>("");
  const [programId, setProgramId] = useState<string | null>(null);
  //: Whether the festival/programme column is shown. Closed, the table has the page.
  const [asideOpen, setAsideOpen] = useState(true);

  // Default to the first competition once the list arrives, so the page is never
  // an empty shell for an organizer who has exactly one festival.
  useEffect(() => {
    if (!competitionId && competitions.data && competitions.data.length > 0) {
      setCompetitionId(competitions.data[0]?.id ?? "");
    }
  }, [competitionId, competitions.data]);

  const programs = usePrograms(competitionId || undefined);
  const competition = useCompetitionDetail(competitionId || undefined);

  useEffect(() => {
    // Selecting another competition must not leave a foreign programme open.
    if (programId && programs.data && !programs.data.some((program) => program.id === programId)) {
      setProgramId(null);
    }
  }, [programId, programs.data]);

  const nominations = useMemo(
    () =>
      (competition.data?.categories ?? [])
        .slice()
        .sort((a, b) => a.sortOrder - b.sortOrder)
        .map((category) => ({ value: category.id, label: category.name })),
    [competition.data],
  );

  return (
    // `full`, not the usual `max-w-5xl`: the programme is a thirteen-column table and the
    // default container left it permanently sideways-scrolling on a screen that had room
    // for it. Every descendant down to the scroll container still carries `min-w-0`, so a
    // table wider than even this scrolls inside itself rather than moving the page.
    <PageContainer size="full">
      <PageHeader>
        <PageTitle>Программа фестиваля</PageTitle>
        <PageDescription>
          Конструктор программы: порядок выступлений, перерывы, служебные блоки и публичные ссылки
          для звукорежиссёра, ведущего, жюри и экрана у сцены.
        </PageDescription>
      </PageHeader>

      <PageContent className="gap-4">
        <div className="grid gap-3 sm:grid-cols-2 lg:max-w-2xl">
          <Select
            label="Фестиваль"
            placeholder="Выберите фестиваль"
            options={(competitions.data ?? []).map((item) => ({
              value: item.id,
              label: `${item.title} · ${item.season}`,
            }))}
            value={competitionId}
            onValueChange={(value: string) => {
              setCompetitionId(value);
              setProgramId(null);
            }}
          />
        </div>

        {competitions.isLoading ? <LoadingState label="Загружаем фестивали…" size="sm" /> : null}

        {/* `minmax(0,1fr)` in both cases, and `min-w-0` on the children: without them a grid
            or flex track sizes to its content, and the wide programme table would push the
            whole page sideways instead of scrolling inside itself. */}
        {competitionId ? (
          <div
            className={
              asideOpen
                ? "grid grid-cols-[minmax(0,1fr)] gap-4 lg:grid-cols-[320px_minmax(0,1fr)]"
                : "grid grid-cols-[minmax(0,1fr)] gap-4"
            }
          >
            {asideOpen ? (
              <div className="flex min-w-0 flex-col gap-4">
                <div className="flex items-center justify-between gap-2">
                  <p className="font-medium text-sm">Программы</p>
                  <Button
                    variant="ghost"
                    size="xs"
                    aria-label="Свернуть список программ"
                    onClick={() => setAsideOpen(false)}
                  >
                    <PanelLeftClose className="size-4" />
                  </Button>
                </div>
                <ProgramList
                  programs={programs.data ?? []}
                  isLoading={programs.isLoading}
                  selectedId={programId}
                  onSelect={setProgramId}
                />
                <CreateProgramCard
                  competitionId={competitionId}
                  nominations={nominations}
                  onCreated={setProgramId}
                />
              </div>
            ) : null}

            <div className="flex min-w-0 flex-col gap-3">
              {/* Collapsing the list is the cheap way to give the table the whole page —
                  on a forty-row programme with ten columns the 320px of festival admin
                  beside it is the difference between reading the day and scrolling it. */}
              {asideOpen ? null : (
                <div>
                  <Button variant="outline" size="sm" onClick={() => setAsideOpen(true)}>
                    <PanelLeftOpen className="size-4" /> Программы
                  </Button>
                </div>
              )}
              {programId ? (
                <ProgramWorkspace programId={programId} />
              ) : (
                <EmptyState
                  title="Программа не выбрана"
                  description="Выберите программу слева или создайте новую — например, отдельный на каждый жанр."
                />
              )}
            </div>
          </div>
        ) : null}
      </PageContent>
    </PageContainer>
  );
}

function ProgramList({
  programs,
  isLoading,
  selectedId,
  onSelect,
}: {
  programs: readonly {
    id: string;
    name: string;
    itemCount: number;
    totalSeconds: number;
    shareCount: number;
  }[];
  isLoading: boolean;
  selectedId: string | null;
  onSelect: (id: string) => void;
}): React.JSX.Element {
  if (isLoading) {
    return <LoadingState label="Загружаем программы…" size="sm" />;
  }
  if (programs.length === 0) {
    return (
      <EmptyState
        title="Программ пока нет"
        description="Создайте первую программу — обычно по одной на жанр."
      />
    );
  }
  return (
    <div className="flex flex-col gap-2">
      {programs.map((program) => (
        <button
          key={program.id}
          type="button"
          aria-current={program.id === selectedId}
          onClick={() => onSelect(program.id)}
          className={
            program.id === selectedId
              ? "rounded-md border border-primary bg-primary/5 p-3 text-left"
              : "cursor-pointer rounded-md border border-border p-3 text-left hover:bg-muted/50"
          }
        >
          <p className="font-medium text-sm">{program.name}</p>
          <p className="text-muted-foreground text-xs">
            Пунктов: {program.itemCount} · {formatSpan(program.totalSeconds)}
            {program.shareCount > 0 ? ` · Ссылок: ${program.shareCount}` : ""}
          </p>
        </button>
      ))}
    </div>
  );
}

function CreateProgramCard({
  competitionId,
  nominations,
  onCreated,
}: {
  competitionId: string;
  nominations: { value: string; label: string }[];
  onCreated: (programId: string) => void;
}): React.JSX.Element {
  const create = useCreateProgram();
  const [name, setName] = useState("");
  const [nominationId, setNominationId] = useState("");
  const [startsAt, setStartsAt] = useState("");

  const submit = () => {
    create.mutate(
      {
        competitionId,
        name: name.trim(),
        nominationId: nominationId || null,
        // "2026-08-01T10:00" is the time on the wall in the hall, not on this laptop:
        // it is read in the festival's zone, which is the zone every copy of the
        // programme is rendered back in.
        startsAt: festivalInputToIso(startsAt),
      },
      {
        onSuccess: (program) => {
          setName("");
          setStartsAt("");
          onCreated(program.id);
          toast.success("Программа создана");
        },
        onError: () => toast.error("Не удалось создать программу"),
      },
    );
  };

  return (
    <Card>
      <CardContent className="flex flex-col gap-3 p-4">
        <p className="font-medium text-sm">Новая программа</p>
        <Input
          label="Название программы"
          placeholder="Вокал, 1 отделение"
          value={name}
          onChange={(event) => setName(event.target.value)}
        />
        <Select
          label="Жанр"
          placeholder="Весь фестиваль"
          options={nominations}
          value={nominationId}
          onValueChange={setNominationId}
        />
        <DateTimePicker label="Начало" value={startsAt} onChange={setStartsAt} />
        <Button onClick={submit} loading={create.isPending} disabled={name.trim().length === 0}>
          Создать программу
        </Button>
      </CardContent>
    </Card>
  );
}

function ProgramWorkspace({ programId }: { programId: string }): React.JSX.Element {
  const { data: program, isLoading } = useProgram(programId);
  if (isLoading || !program) {
    return <LoadingState label="Загружаем программу…" size="sm" />;
  }
  return <ProgramWorkspaceInner key={programId} program={program} />;
}

function ProgramWorkspaceInner({ program }: { program: Program }): React.JSX.Element {
  return (
    // `min-w-0` all the way down to the scroll container, or the table's width wins.
    <div className="flex min-w-0 flex-col gap-4">
      <ProgramSettings program={program} />
      <Divider />
      <RunningOrder program={program} />
      <Divider />
      <ExportPanel program={program} />
      <Divider />
      <CandidateList program={program} />
      <Divider />
      <PublicLinks program={program} />
    </div>
  );
}

function ProgramSettings({ program }: { program: Program }): React.JSX.Element {
  const update = useUpdateProgram(program.id);
  const setBuffer = (bufferSeconds: number) =>
    update.mutate({ bufferSeconds }, { onError: () => toast.error("Не удалось изменить буфер") });
  return (
    <div className="flex flex-col gap-3">
      <div className="flex flex-wrap items-baseline justify-between gap-2">
        <h2 className="font-semibold text-lg">{program.name}</h2>
        <p className="text-muted-foreground text-sm">
          {formatClock(program.startsAt)} – {formatClock(program.endsAt)} ·{" "}
          {formatSpan(program.totalSeconds)}
        </p>
      </div>
      <div className="grid gap-3 sm:grid-cols-2 lg:max-w-xl">
        <Select
          label="Буфер между выступлениями"
          options={BUFFER_PRESETS.map((seconds) => ({
            value: String(seconds),
            label: bufferLabel(seconds),
          }))}
          value={String(program.bufferSeconds)}
          onValueChange={(value: string) => setBuffer(Number(value))}
          description="Добавляется к каждому выступлению при расчёте расписания и не меняет длительность номера."
        />
        <ProgramStart program={program} />
      </div>
    </div>
  );
}

/**
 * «Буфер» in words, not on a stopwatch.
 *
 * {@link formatDuration} renders `m:ss`, which is right in the «Хронометраж» column of a
 * three-minute act and ambiguous here: a buffer shown as «1:30» was read as an hour and
 * a half at least as often as the minute and a half it is. The unit is spelled out
 * because this control is answered once per programme — there is nothing to keep compact.
 */
function bufferLabel(seconds: number): string {
  if (seconds === 0) {
    return "Без буфера";
  }
  const minutes = Math.floor(seconds / 60);
  const rest = seconds % 60;
  if (minutes === 0) {
    return `${rest} сек`;
  }
  return rest === 0 ? `${minutes} мин` : `${minutes} мин ${rest} сек`;
}

/**
 * «Начало программы» — the one field here that is typed into rather than chosen from.
 *
 * Which is why it keeps a draft instead of saving every change the picker reports. The
 * picker reports one on nearly every keystroke: typing «1047» passes through `10:4`,
 * which *is* a valid time (10:04), so a field edited straight into the mutation sent two
 * PATCHes for one correction and left whichever reply happened to land second on screen.
 * That is the «дата ставится неправильно» organizers reported — and clearing the time to
 * retype it reported midnight on the way past, which is the «потом она пропадает».
 *
 * So: a local draft, saved once the typing stops, and never saved half-finished. A date
 * with no time yet is not an instant and waits; an emptied date *is* an answer («у этой
 * программы пока нет времени») and clears the start, which is the only way back to an
 * untimed running order.
 */
function ProgramStart({ program }: { program: Program }): React.JSX.Element {
  const update = useUpdateProgram(program.id);
  const saved = isoToFestivalInput(program.startsAt);
  const [draft, setDraft] = useState(saved);

  // Follow the programme when it changes underneath — a reply landing, another tab, a
  // different programme opened into the same form — but never over an unsaved edit.
  useEffect(() => setDraft(saved), [saved]);

  // `update` is deliberately not a dependency: it is a fresh object on every render, so
  // depending on it would restart the timer forever and nothing would ever be saved.
  // biome-ignore lint/correctness/useExhaustiveDependencies: see above.
  useEffect(() => {
    if (draft === saved) {
      return;
    }
    const [date = "", time = ""] = draft.split("T");
    // Half an answer: the day is chosen and the hour is still being typed. Waiting costs
    // nothing — the next keystroke restarts this timer anyway.
    if (date !== "" && time.length < 5) {
      return;
    }
    const timer = setTimeout(() => {
      update.mutate(
        { startsAt: festivalInputToIso(draft) },
        { onError: () => toast.error("Не удалось изменить время начала") },
      );
    }, START_SAVE_DELAY_MS);
    return () => clearTimeout(timer);
  }, [draft, saved]);

  // `timeLabel` is overridden because the table below has a «Время» column: two things
  // called «Время» on one screen is one too many for anybody reading it out loud.
  return (
    <DateTimePicker
      label="Начало программы"
      timeLabel="Время начала"
      value={draft}
      onChange={setDraft}
    />
  );
}

/**
 * How long the start time waits after the last keystroke before it is saved.
 *
 * Long enough to cover the pause between the hour and the minutes, short enough that
 * nobody navigates away from a change they thought they had made.
 */
const START_SAVE_DELAY_MS = 900;

/**
 * The running order: the table the whole constructor exists to arrange.
 *
 * Three ways to move something, because they answer three different questions. The arrows
 * are a correction ("этот номер на строку выше"). {@link MoveToNumber} is a jump ("этот
 * номер — сразу после №12"), which the arrows cannot make across forty rows. And dragging
 * is the one the day is actually planned with: a whole genre picked up by its header and
 * dropped above another one, which is forty moves done as one.
 *
 * The reorder endpoint takes the complete new order rather than a move instruction, so
 * every one of them ends in the same place — the order the organizer is looking at.
 */
function RunningOrder({ program }: { program: Program }): React.JSX.Element {
  const reorder = useReorderItems(program.id);
  const remove = useRemoveItem(program.id);
  const items = program.items;

  /** Which axis the rows are grouped under on screen, or {@link UNGROUPED}. */
  const [groupBy, setGroupBy] = useState<GroupingAxis | typeof UNGROUPED>(UNGROUPED);
  /** Columns the organizer has hidden from *this screen* — exports choose their own. */
  const [hidden, setHidden] = useState<readonly ColumnKey[]>([]);
  /** The run being dragged, and where it would land — both indexes into `items`. */
  const [drag, setDrag] = useState<{ start: number; count: number } | null>(null);
  const [dropAt, setDropAt] = useState<number | null>(null);

  const send = (next: ProgramItem[]) => {
    reorder.mutate(
      next.map((item) => item.id),
      { onError: () => toast.error("Не удалось изменить порядок") },
    );
  };

  const move = (from: number, to: number) => send(moveItem(items, from, to));

  /**
   * Move a slot next to the one numbered `number`, answering whether it could be done —
   * the form keeps itself open on a number nobody in the programme carries, so the
   * organizer can correct a typo instead of retyping the whole move.
   */
  const moveNextTo = (from: number, number: number, placement: MovePlacement): boolean => {
    const next = moveItemNextTo(items, from, number, placement);
    if (next === null) {
      toast.error(`В программе нет №${number}`);
      return false;
    }
    send(next);
    return true;
  };

  const busy = reorder.isPending || remove.isPending;
  const columns = program.availableColumns.filter((column) => !hidden.includes(column.key));
  const groups = groupBy === UNGROUPED ? null : groupRuns(items, groupBy);

  /** Finish a drag: the run goes where the indicator was, and the state is cleared. */
  const drop = () => {
    if (drag !== null && dropAt !== null) {
      send(moveBlock(items, drag.start, drag.count, dropAt));
    }
    setDrag(null);
    setDropAt(null);
  };

  /**
   * Where a pointer over a row means the run should land.
   *
   * The top half of a row means "before it", the bottom half "after it" — which is how
   * every list with a drop line behaves, and the only way to express "в самый конец"
   * without a separate target under the last row.
   */
  const hoverRow = (event: React.DragEvent, index: number) => {
    if (drag === null) {
      return;
    }
    event.preventDefault();
    const box = event.currentTarget.getBoundingClientRect();
    setDropAt(event.clientY > box.top + box.height / 2 ? index + 1 : index);
  };

  /** Move a whole group past its neighbour — the keyboard's way to do what a drag does. */
  const moveGroup = (position: number, by: -1 | 1) => {
    if (groups === null) {
      return;
    }
    const group = groups[position];
    const neighbour = groups[position + by];
    if (group === undefined || neighbour === undefined) {
      return;
    }
    send(
      moveBlock(
        items,
        group.start,
        group.items.length,
        by === -1 ? neighbour.start : neighbour.start + neighbour.items.length,
      ),
    );
  };

  // Once published, numbers stay with their participants, so a rearranged programme reads
  // 2, 3, 5, 4. Saying so out loud beats letting an organizer wonder whether it is a bug.
  // Counted over the numbered slots only — the breaks between them carry no number and
  // would otherwise make every programme with a lunch in it look rearranged.
  const outOfSequence =
    program.numbersFrozen &&
    items
      .filter((item) => itemNumber(item) !== null)
      .some((item, index) => itemNumber(item) !== index + 1);

  const rowProps = (index: number) => ({
    dragging: drag !== null && index >= drag.start && index < drag.start + drag.count,
    dropBefore: dropAt === index,
    dropAfter: dropAt === index + 1 && index === items.length - 1,
    onDragStart: () => setDrag({ start: index, count: 1 }),
    onDragEnd: () => {
      setDrag(null);
      setDropAt(null);
    },
    onDragOver: (event: React.DragEvent) => hoverRow(event, index),
    onDrop: (event: React.DragEvent) => {
      event.preventDefault();
      drop();
    },
  });

  const row = (item: ProgramItem, index: number) => (
    <ProgramItemRow
      key={item.id}
      item={item}
      columns={columns}
      index={index}
      total={items.length}
      busy={busy}
      onUp={() => move(index, index - 1)}
      onDown={() => move(index, index + 1)}
      onMoveTo={(to) => move(index, to)}
      onMoveNextTo={(number, placement) => moveNextTo(index, number, placement)}
      onRemove={() =>
        remove.mutate(item.id, {
          onError: () => toast.error("Не удалось удалить пункт"),
        })
      }
      programId={program.id}
      {...rowProps(index)}
    />
  );

  return (
    <div className="flex min-w-0 flex-col gap-3">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div className="flex flex-wrap items-baseline gap-2">
          <p className="font-medium text-sm">Программа</p>
          {/* Which phase the programme is in is the difference between "the numbers will
              settle later" and "these numbers are what participants were told". */}
          {!program.numbersFrozen ? (
            <span className="text-muted-foreground text-xs">
              номера идут по порядку и зафиксируются после первой публикации
            </span>
          ) : outOfSequence ? (
            <span className="text-muted-foreground text-xs">номера сохранены за участниками</span>
          ) : null}
        </div>
        <div className="flex flex-wrap items-end gap-2">
          <ArrangeControls program={program} />
          {outOfSequence ? <RenumberButton programId={program.id} /> : null}
          <AddColumnControls programId={program.id} />
          <AddBreakControls programId={program.id} />
        </div>
      </div>

      {items.length === 0 ? (
        <EmptyState
          title="Программа пуста"
          description="Соберите её автоматически по правилам, добавьте выступления из списка ниже или вставьте служебный блок."
        />
      ) : (
        <>
          <div className="flex flex-wrap items-end justify-between gap-2">
            <GroupByControl
              columns={program.availableColumns}
              value={groupBy}
              onChange={setGroupBy}
            />
            <VisibleColumnsControl
              columns={program.availableColumns}
              hidden={hidden}
              onChange={setHidden}
            />
          </div>

          {/* The programme is a table, and it fits — however many columns are on. `relative`
              is load-bearing for a different reason: it makes this the containing block for
              absolutely positioned descendants, `sr-only` labels above all, so a 1px span at
              the right edge cannot set the whole document's scroll width. `overflow-x-auto`
              stays as the net under a table too narrow even for this. See the public page. */}
          <div className="scrollbar-custom relative w-full max-w-full overflow-x-auto rounded-md border border-border">
            {/* `table-fixed w-full`: the columns are laid out from the widths below rather
                than from their contents, which is the whole of "it always fits". */}
            <table className="w-full table-fixed border-collapse text-left">
              <caption className="sr-only">Программа: {program.name}</caption>
              <colgroup>
                <col style={{ width: HANDLE_WIDTH }} />
                {columnWidths(columns).map((width, index) => (
                  // The key is the column's own, not the index: `columns` is reordered and
                  // filtered by the visibility control above.
                  <col key={columns[index]?.key ?? index} style={{ width }} />
                ))}
                <col style={{ width: ACTIONS_WIDTH }} />
              </colgroup>
              <thead>
                <tr className="border-border border-b bg-muted/50">
                  <th scope="col" className="px-1 py-2">
                    <span className="sr-only">Перетащить</span>
                  </th>
                  {columns.map((column) => (
                    <th
                      key={column.key}
                      scope="col"
                      className="break-words px-2 py-2 align-bottom font-medium text-muted-foreground text-xs uppercase tracking-wide"
                    >
                      {column.custom ? (
                        <CustomColumnHeader programId={program.id} column={column} />
                      ) : (
                        column.label
                      )}
                    </th>
                  ))}
                  <th scope="col" className="px-2 py-2 text-right">
                    <span className="sr-only">Действия</span>
                  </th>
                </tr>
              </thead>
              {groups === null ? (
                <tbody>{items.map((item, index) => row(item, index))}</tbody>
              ) : (
                groups.map((group: ProgramGroup, position: number) => (
                  // One `tbody` per group: it is the grouping, as far as a screen reader
                  // and the browser's own table model are concerned.
                  <tbody key={group.key}>
                    {group.standalone ? null : (
                      <GroupHeaderRow
                        group={group}
                        span={columns.length + 2}
                        busy={busy}
                        atStart={position === 0}
                        atEnd={position === groups.length - 1}
                        dragging={
                          drag !== null &&
                          drag.start === group.start &&
                          drag.count === group.items.length
                        }
                        onDragStart={() =>
                          setDrag({ start: group.start, count: group.items.length })
                        }
                        onDragEnd={() => {
                          setDrag(null);
                          setDropAt(null);
                        }}
                        onDragOver={(event) => hoverRow(event, group.start)}
                        onDrop={(event) => {
                          event.preventDefault();
                          drop();
                        }}
                        dropBefore={dropAt === group.start}
                        onUp={() => moveGroup(position, -1)}
                        onDown={() => moveGroup(position, 1)}
                      />
                    )}
                    {group.items.map((item: ProgramItem, offset: number) =>
                      row(item, group.start + offset),
                    )}
                  </tbody>
                ))
              )}
            </table>
          </div>
        </>
      )}
    </div>
  );
}

/**
 * How wide each column of the running order is.
 *
 * **The table fits the screen, always.** Thirteen built-in columns plus whatever the
 * organizer added is far more than any laptop has room for, and the old answer — let the
 * table be as wide as its contents and scroll it sideways — meant the organizer dragged a
 * row while the «№» it was going to was off-screen. Turning columns off helped and was
 * the wrong thing to have to do: the columns are on because they are being read.
 *
 * So the widths are stated rather than measured ({@link ProgramColumn} layout is `fixed`),
 * and they are stated in two kinds:
 *
 * * **{@link FIXED_COLUMN_WIDTHS}** — columns whose content has one known size. «10:04» is
 *   five characters whether the table shows four columns or twenty, and giving it a share
 *   of the width would make it grow for no reason and then shrink below legibility.
 * * **{@link FLEXIBLE_COLUMN_WEIGHTS}** — columns of prose, which share whatever is left
 *   in proportion to how much they typically need. A name needs more room than an age
 *   band; a note needs more than either.
 *
 * Everything the columns cannot use is reserved first: the drag handle and the row's
 * buttons. Those are controls, not data — they have a size and keeping it is the point.
 */
const FIXED_COLUMN_WIDTHS: Partial<Record<ProgramColumnKey, string>> = {
  POSITION: "2.5rem",
  TIME: "3.5rem",
  DURATION: "4.75rem",
  PARTICIPANT_COUNT: "3.5rem",
};

const FLEXIBLE_COLUMN_WEIGHTS: Partial<Record<ProgramColumnKey, number>> = {
  PARTICIPANT: 1.6,
  TITLE: 2,
  NOMINATION: 1.2,
  DISCIPLINE: 1.2,
  PARTICIPANT_GROUP: 1,
  AGE_CATEGORY: 1,
  PARTICIPATION_FORMAT: 1,
  TEACHERS: 1.4,
  ORGANIZATION: 1.4,
  CONTACTS: 1.1,
  COMMENT: 1.6,
};

/** What a column the organizer added gets: a plain share, same as an age band. */
const DEFAULT_COLUMN_WEIGHT = 1;

/** The drag handle: one icon, and never anything else. */
const HANDLE_WIDTH = "2rem";

/**
 * The row's buttons: up, down, «после №», delete, and a block's own minutes field.
 *
 * Sized for the four icon buttons on one line — 4 × 1.75rem, three gaps and the cell's
 * own padding — and barely more: everything left over is width the programme wants.
 * Capped as a *share* as well, because on a phone a fixed 8.75rem is a third of the
 * screen handed to four icons; there they wrap onto a second line inside the cell and
 * give way to the running order, which is what `flex-wrap` on the row is for.
 */
const ACTIONS_WIDTH = "min(8.75rem, 26%)";

/**
 * The widths of the data columns, in the order they are shown.
 *
 * Returned as CSS rather than numbers so the arithmetic happens in the browser, at the
 * width the table actually has: no measuring, no resize observer, and a column that is
 * right the moment the sidebar is collapsed rather than one frame later.
 */
function columnWidths(columns: ProgramColumn[]): string[] {
  const fixed = columns.map((column) =>
    column.custom ? undefined : FIXED_COLUMN_WIDTHS[column.key as ProgramColumnKey],
  );
  const weights = columns.map((column, index) =>
    fixed[index] !== undefined
      ? 0
      : ((column.custom ? undefined : FLEXIBLE_COLUMN_WEIGHTS[column.key as ProgramColumnKey]) ??
        DEFAULT_COLUMN_WEIGHT),
  );
  const total = weights.reduce((sum, weight) => sum + weight, 0);
  const reserved = [HANDLE_WIDTH, ACTIONS_WIDTH, ...fixed.filter((width) => width !== undefined)];
  const free = `calc(100% - ${reserved.join(" - ")})`;
  return columns.map((_, index) => {
    const own = fixed[index];
    if (own !== undefined) {
      return own;
    }
    // Six places, not four: eleven columns rounded to four would sum to 100.02% of the
    // free space, and a fixed-layout table whose widths overshoot is one the container
    // can scroll after all. `total` cannot be 0 here — this branch only runs for a
    // column that carries a weight.
    return `calc(${free} * ${((weights[index] ?? 0) / total).toFixed(6)})`;
  });
}

/**
 * «Группировать» — a reading of the running order, not a rearrangement of it.
 *
 * The labels come from the programme's own columns rather than a second list of words:
 * the platform renamed what it calls these things once already (NOMINATION is «Жанр» on
 * screen), and a dropdown with its own copy of the vocabulary is how the two drift apart.
 *
 * «Без группировки» is an option rather than a placeholder because a placeholder cannot be
 * chosen: there would be no way back to the plain running order once an axis was picked.
 */
function GroupByControl({
  columns,
  value,
  onChange,
}: {
  columns: ProgramColumn[];
  value: GroupingAxis | typeof UNGROUPED;
  onChange: (next: GroupingAxis | typeof UNGROUPED) => void;
}): React.JSX.Element {
  const labels = new Map(columns.map((column) => [column.key, column.label]));
  const options = [
    { value: UNGROUPED, label: "Без группировки" },
    ...GROUPING_AXES.filter((axis) => labels.has(axis)).map((axis) => ({
      value: axis,
      label: labels.get(axis) ?? GROUPING_AXIS_LABELS[axis],
    })),
  ];
  return (
    <div className="w-56">
      <Select
        label="Группировать"
        options={options}
        value={value}
        onValueChange={(next: string) => onChange(next as GroupingAxis | typeof UNGROUPED)}
      />
    </div>
  );
}

/** The "no grouping" choice. A real value, because a Radix option cannot carry an empty one. */
const UNGROUPED = "NONE";

/**
 * Which columns this screen shows.
 *
 * A programme can carry thirteen columns plus whatever the organizer added, and all of
 * them at once is a table nobody can read without scrolling sideways past the thing they
 * were looking at. Hiding one here changes *this screen only* — what a link publishes and
 * what a PDF prints are separate decisions, made in their own panels.
 */
function VisibleColumnsControl({
  columns,
  hidden,
  onChange,
}: {
  columns: ProgramColumn[];
  hidden: readonly ColumnKey[];
  onChange: (next: readonly ColumnKey[]) => void;
}): React.JSX.Element {
  const shown = columns.length - hidden.length;
  const toggle = (key: ColumnKey, visible: boolean) =>
    onChange(visible ? hidden.filter((item) => item !== key) : [...hidden, key]);
  return (
    <Popover>
      <PopoverTrigger asChild>
        <Button variant="outline" size="sm">
          <Columns3 className="size-4" /> Колонки на экране: {shown}
        </Button>
      </PopoverTrigger>
      <PopoverContent align="end" className="flex w-64 flex-col gap-2">
        {/* `min-w-0`: a `fieldset` has a built-in `min-width: min-content` that ignores
            its container, so a long column name would widen the popover. */}
        <fieldset className="flex max-h-80 min-w-0 flex-col gap-2 overflow-y-auto">
          <legend className="sr-only">Колонки на экране</legend>
          {columns.map((column) => (
            <Checkbox
              key={column.key}
              label={column.label}
              checked={!hidden.includes(column.key)}
              onCheckedChange={(checked: boolean) => toggle(column.key, checked)}
            />
          ))}
        </fieldset>
        <Divider />
        <Button variant="ghost" size="sm" onClick={() => onChange([])}>
          Показать все
        </Button>
      </PopoverContent>
    </Popover>
  );
}

/**
 * The header of one group, and the handle the whole group is dragged by.
 *
 * This row is the feature: picking up «Эстрадный вокал» and dropping it above «Народный»
 * is one gesture for what the arrows would take forty of. The buttons beside it do the
 * same move from the keyboard, because a drag is not reachable without a pointer.
 */
function GroupHeaderRow({
  group,
  span,
  busy,
  atStart,
  atEnd,
  dragging,
  dropBefore,
  onDragStart,
  onDragEnd,
  onDragOver,
  onDrop,
  onUp,
  onDown,
}: {
  group: ProgramGroup;
  span: number;
  busy: boolean;
  atStart: boolean;
  atEnd: boolean;
  dragging: boolean;
  dropBefore: boolean;
  onDragStart: () => void;
  onDragEnd: () => void;
  onDragOver: (event: React.DragEvent) => void;
  onDrop: (event: React.DragEvent) => void;
  onUp: () => void;
  onDown: () => void;
}): React.JSX.Element {
  return (
    <tr
      data-testid="program-group"
      onDragOver={onDragOver}
      onDrop={onDrop}
      className={[
        "border-border border-b bg-muted/70",
        dragging ? "opacity-50" : "",
        dropBefore ? "border-primary border-t-2" : "",
      ]
        .filter(Boolean)
        .join(" ")}
    >
      <td
        draggable={!busy}
        onDragStart={onDragStart}
        onDragEnd={onDragEnd}
        aria-label={`Перетащить группу: ${group.label}`}
        className="cursor-grab px-1 py-1.5 align-middle active:cursor-grabbing"
      >
        <GripVertical className="size-4 text-muted-foreground" />
      </td>
      <td colSpan={span - 2} className="px-2 py-1.5">
        <span className="flex flex-wrap items-baseline gap-2">
          <span className="font-semibold text-sm">{group.label}</span>
          <span className="text-muted-foreground text-xs">
            {group.items.length} {plural(group.items.length, "номер", "номера", "номеров")}
          </span>
        </span>
      </td>
      <td className="px-2 py-1.5">
        <div className="flex items-center justify-end gap-1">
          <Button
            variant="ghost"
            size="xs"
            aria-label={`Группу выше: ${group.label}`}
            disabled={atStart || busy}
            onClick={onUp}
          >
            <ArrowUp className="size-4" />
          </Button>
          <Button
            variant="ghost"
            size="xs"
            aria-label={`Группу ниже: ${group.label}`}
            disabled={atEnd || busy}
            onClick={onDown}
          >
            <ArrowDown className="size-4" />
          </Button>
        </div>
      </td>
    </tr>
  );
}

/** `2 → "номера"`. Russian needs three forms, and a count beside a noun needs the right one. */
function plural(count: number, one: string, few: string, many: string): string {
  const mod100 = count % 100;
  if (mod100 >= 11 && mod100 <= 14) {
    return many;
  }
  const mod10 = count % 10;
  if (mod10 === 1) {
    return one;
  }
  return mod10 >= 2 && mod10 <= 4 ? few : many;
}

function ProgramItemRow({
  item,
  columns,
  index,
  total,
  busy,
  onUp,
  onDown,
  onMoveTo,
  onMoveNextTo,
  onRemove,
  programId,
  dragging,
  dropBefore,
  dropAfter,
  onDragStart,
  onDragEnd,
  onDragOver,
  onDrop,
}: {
  item: ProgramItem;
  columns: ProgramColumn[];
  index: number;
  total: number;
  busy: boolean;
  onUp: () => void;
  onDown: () => void;
  onMoveTo: (to: number) => void;
  onMoveNextTo: (number: number, placement: MovePlacement) => boolean;
  onRemove: () => void;
  programId: string;
  /** This row is part of the run currently being dragged. */
  dragging: boolean;
  /** The drop indicator sits above / below this row. */
  dropBefore: boolean;
  dropAfter: boolean;
  onDragStart: () => void;
  onDragEnd: () => void;
  onDragOver: (event: React.DragEvent) => void;
  onDrop: (event: React.DragEvent) => void;
}): React.JSX.Element {
  const isPerformance = item.kind === "PERFORMANCE";
  const format = { clock: formatClock, duration: formatDuration };
  const onStage = item.progress === "ON_STAGE";
  const behindUs = item.progress === "PERFORMED" || item.progress === "SKIPPED";
  return (
    <tr
      data-testid="program-item"
      data-progress={item.progress}
      onDragOver={onDragOver}
      onDrop={onDrop}
      className={[
        "border-border border-b last:border-0",
        onStage ? "bg-primary/10" : behindUs ? "text-muted-foreground" : "",
        isPerformance ? "" : "bg-muted/40",
        dragging ? "opacity-50" : "",
        dropBefore ? "border-primary border-t-2" : "",
        dropAfter ? "border-primary border-b-2 last:border-b-2" : "",
      ]
        .filter(Boolean)
        .join(" ")}
    >
      {/* The handle is its own cell rather than `draggable` on the row: a draggable row
          swallows text selection and makes the hand-filled cells inside it unusable. */}
      <td
        draggable={!busy}
        onDragStart={onDragStart}
        onDragEnd={onDragEnd}
        aria-label={`Перетащить: ${item.title}`}
        className="cursor-grab px-1 py-2 align-middle active:cursor-grabbing"
      >
        <GripVertical className="size-4 text-muted-foreground" />
      </td>
      {columns.map((column) => (
        <td
          key={column.key}
          // `break-words` and `align-top` are what make a fixed-width table readable: a
          // name longer than its column wraps inside it instead of pushing the column
          // wider, and every cell of a row that wrapped starts at the same line.
          className={
            column.key === "TIME" || column.key === "POSITION"
              ? "whitespace-nowrap px-2 py-2 align-top font-semibold text-sm tabular-nums"
              : "break-words px-2 py-2 align-top text-sm"
          }
        >
          {column.custom ? (
            <CustomCell programId={programId} item={item} columnKey={column.key} />
          ) : column.key === "TITLE" ? (
            <span className="flex flex-wrap items-baseline gap-1.5">
              {/* A block's title is the organizer's own words and is edited where it is
                  read; an act's comes from its entry and is not theirs to retype here. */}
              {isPerformance ? (
                <span>{itemCell(item, column.key, format)}</span>
              ) : (
                <BlockTitle programId={programId} item={item} />
              )}
              {/* The badge names the kind; a break literally titled "Перерыв" needs no
                  second label saying so. */}
              {isPerformance || item.title === ITEM_KIND_LABELS[item.kind] ? null : (
                <Badge variant="secondary">{ITEM_KIND_LABELS[item.kind]}</Badge>
              )}
              {item.missingPerformance ? <Badge variant="warning">Номер снят</Badge> : null}
              {/* What the host has announced, so the organizer's own table is live too. */}
              {item.progress !== "PENDING" ? (
                <Badge variant={onStage ? "success" : "secondary"}>
                  {PROGRESS_LABELS[item.progress]}
                </Badge>
              ) : null}
            </span>
          ) : column.key === "DURATION" ? (
            <span className="whitespace-nowrap tabular-nums">
              {itemCell(item, column.key, format)}
              {item.schedule.slotSeconds !== item.durationSeconds
                ? ` (+${formatDuration(item.schedule.slotSeconds - item.durationSeconds)})`
                : ""}
            </span>
          ) : column.key === "COMMENT" ? (
            <span className="whitespace-pre-line text-muted-foreground text-xs">
              {itemCell(item, column.key, format)}
            </span>
          ) : (
            itemCell(item, column.key, format) || <span className="text-muted-foreground">—</span>
          )}
        </td>
      ))}

      {/* `px-1`, not `px-2`: the padding is width this cell does not have to spare, and
          the buttons already carry their own. `flex-wrap` is the backstop — a block row
          also holds its minutes field, and a second line inside the cell beats a row of
          buttons sitting on top of the comment beside it. */}
      <td className="px-1 py-2 align-top">
        <div className="flex flex-wrap items-center justify-end gap-1">
          {isPerformance ? null : <EditBlockDuration programId={programId} item={item} />}
          <Button
            variant="ghost"
            size="xs"
            iconOnly
            aria-label={`Вверх: ${item.title}`}
            disabled={index === 0 || busy}
            onClick={onUp}
          >
            <ArrowUp className="size-4" />
          </Button>
          <Button
            variant="ghost"
            size="xs"
            iconOnly
            aria-label={`Вниз: ${item.title}`}
            disabled={index === total - 1 || busy}
            onClick={onDown}
          >
            <ArrowDown className="size-4" />
          </Button>
          <MoveToNumber
            label={item.title}
            current={itemNumber(item)}
            atStart={index === 0}
            atEnd={index === total - 1}
            disabled={busy}
            onPlace={onMoveNextTo}
            onMoveToStart={() => onMoveTo(0)}
            onMoveToEnd={() => onMoveTo(total - 1)}
          />
          <Button
            variant="ghost"
            size="xs"
            iconOnly
            aria-label={`Удалить: ${item.title}`}
            disabled={busy}
            onClick={onRemove}
          >
            <Trash2 className="size-4" />
          </Button>
        </div>
      </td>
    </tr>
  );
}

/**
 * A block's own name, editable in place.
 *
 * «Перерыв» is what the generator calls one, and it is almost never what the day calls
 * it: «Обед», «Перерыв 15 минут», «Технический перерыв — смена рояля», «Антракт». The
 * name goes out on every public link and onto the printed programme, so it is the
 * organizer's to write — and this is the cell everyone already looks at to read it.
 *
 * Saved on blur, like every other hand-filled cell in this table, and a title rubbed out
 * entirely is refused rather than saved: a nameless block is a gap in the running order
 * nobody can account for. The old name comes back, which says so without a message.
 */
function BlockTitle({
  programId,
  item,
}: {
  programId: string;
  item: ProgramItem;
}): React.JSX.Element {
  const edit = useEditItem(programId);
  const [title, setTitle] = useState(item.title);

  // Follow the slot when it changes underneath — a rebuild, another tab — but never
  // over what is being typed here.
  useEffect(() => setTitle(item.title), [item.title]);

  return (
    <Input
      aria-label={`Название: ${item.title}`}
      // `min-w-0`, emphatically: a minimum wider than the column leaves the field
      // sitting on top of the next one, which is what a fixed-width table cannot
      // absorb. It is as wide as its column and no wider.
      className="h-7 w-full min-w-0 text-sm"
      value={title}
      onChange={(event) => setTitle(event.target.value)}
      onBlur={() => {
        const next = title.trim();
        if (next === "") {
          setTitle(item.title);
          return;
        }
        if (next !== item.title) {
          edit.mutate(
            { itemId: item.id, title: next },
            { onError: () => toast.error("Не удалось переименовать блок") },
          );
        }
      }}
    />
  );
}

function EditBlockDuration({
  programId,
  item,
}: {
  programId: string;
  item: ProgramItem;
}): React.JSX.Element {
  const edit = useEditItem(programId);
  const [minutes, setMinutes] = useState(String(Math.round(item.durationSeconds / 60)));
  return (
    <div className="flex items-center gap-1">
      <Input
        aria-label={`Минуты: ${item.title}`}
        type="number"
        min={1}
        className="h-7 w-14"
        value={minutes}
        onChange={(event) => setMinutes(event.target.value)}
        onBlur={() => {
          const seconds = Math.max(1, Number(minutes) || 0) * 60;
          if (seconds !== item.durationSeconds) {
            edit.mutate(
              { itemId: item.id, durationSeconds: seconds },
              { onError: () => toast.error("Не удалось изменить длительность") },
            );
          }
        }}
      />
      <span className="text-muted-foreground text-xs">мин</span>
    </div>
  );
}

function AddColumnControls({ programId }: { programId: string }): React.JSX.Element {
  const addColumn = useAddColumn(programId);
  const [title, setTitle] = useState("");

  const submit = () =>
    addColumn.mutate(title.trim(), {
      onSuccess: () => {
        setTitle("");
        toast.success("Колонка добавлена");
      },
      onError: () => toast.error("Не удалось добавить колонку"),
    });

  return (
    <div className="flex flex-wrap items-end gap-2">
      <Input
        aria-label="Название колонки"
        placeholder="Своя колонка"
        className="h-9 w-40"
        value={title}
        onChange={(event) => setTitle(event.target.value)}
      />
      <Button
        variant="outline"
        size="sm"
        loading={addColumn.isPending}
        disabled={title.trim().length === 0}
        onClick={submit}
      >
        <Columns3 className="size-4" /> Колонка
      </Button>
    </div>
  );
}

/**
 * A custom column's header: rename it in place, or drop it.
 *
 * Renaming keeps the column's id, and so every value already filled into it — which is
 * why it is offered here rather than making the organizer recreate the column.
 */
function CustomColumnHeader({
  programId,
  column,
}: {
  programId: string;
  column: ProgramColumn;
}): React.JSX.Element {
  const rename = useRenameColumn(programId);
  const remove = useRemoveColumn(programId);
  const [title, setTitle] = useState(column.label);
  const columnId = column.key.replace("custom:", "");

  return (
    <div className="flex items-center gap-1">
      <Input
        aria-label={`Колонка: ${column.label}`}
        className="h-7 w-28 text-xs"
        value={title}
        onChange={(event) => setTitle(event.target.value)}
        onBlur={() => {
          const next = title.trim();
          if (next.length > 0 && next !== column.label) {
            rename.mutate(
              { columnId, title: next },
              { onError: () => toast.error("Не удалось переименовать колонку") },
            );
          } else if (next.length === 0) {
            setTitle(column.label);
          }
        }}
      />
      <Button
        variant="ghost"
        size="xs"
        aria-label={`Удалить колонку: ${column.label}`}
        loading={remove.isPending}
        onClick={() =>
          remove.mutate(columnId, { onError: () => toast.error("Не удалось удалить колонку") })
        }
      >
        <Trash2 className="size-3.5" />
      </Button>
    </div>
  );
}

/** One hand-filled cell: typed in place, saved on blur, blank to clear. */
function CustomCell({
  programId,
  item,
  columnKey,
}: {
  programId: string;
  item: ProgramItem;
  columnKey: string;
}): React.JSX.Element {
  const fill = useFillCells(programId);
  const stored = item.customValues[columnKey] ?? "";
  const [value, setValue] = useState(stored);

  return (
    <Input
      aria-label={`Значение: ${item.title}`}
      className="h-7 w-full min-w-0 text-xs"
      value={value}
      onChange={(event) => setValue(event.target.value)}
      onBlur={() => {
        if (value.trim() !== stored) {
          fill.mutate(
            { itemId: item.id, values: { [columnKey]: value.trim() } },
            { onError: () => toast.error("Не удалось сохранить значение") },
          );
        }
      }}
    />
  );
}

/**
 * «Собрать программу» и «Пересобрать» — автосоставление (VT-86).
 *
 * Две кнопки, потому что это два разных действия: первое открывает правила, второе
 * повторяет те, по которым программа уже стоит. Пересобирают чаще, чем собирают впервые,
 * — заявки идут до последнего дня, — и ради этого правила и живут на программе.
 *
 * После публикации обе выключены: пересборка выдаёт слоты заново, а номера уже названы
 * участникам. Сервер откажет и сам, но кнопка, которая заведомо упрётся в ошибку, —
 * это ошибка, показанная вместо объяснения.
 */
function ArrangeControls({ program }: { program: Program }): React.JSX.Element {
  const [open, setOpen] = useState(false);
  const arrange = useArrangeProgram(program.id);

  const run = (input?: Parameters<typeof arrange.mutate>[0]) =>
    arrange.mutate(input, {
      onSuccess: (next) => {
        setOpen(false);
        toast.success(`Программа собрана: ${next.items.length} строк`);
      },
      onError: () => toast.error("Не удалось собрать программу"),
    });

  return (
    <>
      <Button
        variant="outline"
        size="sm"
        disabled={program.numbersFrozen}
        onClick={() => setOpen(true)}
      >
        <Wand2 className="size-4" /> Собрать программу
      </Button>
      {program.arrangement && !program.numbersFrozen ? (
        <Button
          variant="ghost"
          size="sm"
          loading={arrange.isPending}
          onClick={() => run(undefined)}
        >
          Пересобрать
        </Button>
      ) : null}
      <ArrangeProgramDialog
        open={open}
        onOpenChange={setOpen}
        saved={program.arrangement}
        pending={arrange.isPending}
        onSubmit={(input) => run(input)}
      />
    </>
  );
}

function RenumberButton({ programId }: { programId: string }): React.JSX.Element {
  const renumber = useRenumberItems(programId);
  return (
    <Button
      variant="outline"
      size="sm"
      loading={renumber.isPending}
      // Destructive in the sense that matters here: it invalidates numbers already told
      // to participants, so it says what it does rather than being an icon.
      onClick={() =>
        renumber.mutate(undefined, {
          onSuccess: () => toast.success("Номера пересчитаны по порядку"),
          onError: () => toast.error("Не удалось пересчитать номера"),
        })
      }
    >
      <ListOrdered className="size-4" /> Пересчитать номера
    </Button>
  );
}

function AddBreakControls({ programId }: { programId: string }): React.JSX.Element {
  const addBlock = useAddBlock(programId);
  const [title, setTitle] = useState("Перерыв");
  const [minutes, setMinutes] = useState("15");

  return (
    <div className="flex flex-wrap items-end gap-2">
      <Input
        aria-label="Название перерыва"
        placeholder="Перерыв"
        className="h-9 w-40"
        value={title}
        onChange={(event) => setTitle(event.target.value)}
      />
      <Input
        aria-label="Длительность перерыва, минут"
        type="number"
        min={1}
        className="h-9 w-20"
        value={minutes}
        onChange={(event) => setMinutes(event.target.value)}
      />
      <Button
        variant="outline"
        size="sm"
        loading={addBlock.isPending}
        disabled={title.trim().length === 0 || (Number(minutes) || 0) < 1}
        onClick={() =>
          addBlock.mutate(
            { title: title.trim(), durationSeconds: (Number(minutes) || 0) * 60 },
            {
              onSuccess: () => toast.success("Блок добавлен"),
              onError: () => toast.error("Не удалось добавить блок"),
            },
          )
        }
      >
        <Plus className="size-4" /> Вставить блок
      </Button>
    </div>
  );
}

/**
 * Print the programme: tick the columns, get a PDF.
 *
 * The same column-picking shape as publishing a link, because it is the same decision —
 * which of the table's columns this particular audience needs. Defaults to the columns a
 * printed running order almost always wants, rather than to everything, since a thirteen-
 * column page is unreadable.
 *
 * Their order is the organizer's too, and only here: a published edition keeps the
 * canonical order so a column sits in the same place on every screen, while a page is
 * printed for one job — the number and the act first for the sound desk, the organization
 * first for the register — and the eye reads left to right whatever the table thinks.
 */
function ExportPanel({ program }: { program: Program }): React.JSX.Element {
  const [columns, setColumns] = useState<ColumnKey[]>(DEFAULT_EXPORT_COLUMNS);
  const [busy, setBusy] = useState(false);
  const [musicBusy, setMusicBusy] = useState(false);
  const [mediaBusy, setMediaBusy] = useState(false);

  // A column the organizer has since deleted would still be ticked here and would fail
  // the export; dropping it keeps the strip below readable and the request valid.
  const available = new Map(program.availableColumns.map((column) => [column.key, column.label]));
  const chosen = columns.filter((key) => available.has(key));

  const toggle = (key: ColumnKey, checked: boolean) => {
    // A newly ticked column goes last, which is where somebody adding one expects it.
    setColumns((current) =>
      checked
        ? [...current.filter((item) => item !== key), key]
        : current.filter((item) => item !== key),
    );
  };

  const shift = (key: ColumnKey, by: -1 | 1) => {
    setColumns((current) => {
      const from = current.indexOf(key);
      return moveItem(current, from, from + by);
    });
  };

  const download = async () => {
    setBusy(true);
    try {
      await downloadProgramPdf(program.id, chosen, program.name);
    } catch {
      toast.error("Не удалось сформировать PDF");
    } finally {
      setBusy(false);
    }
  };

  /**
   * One archive download, with the wait said out loud.
   *
   * The server assembles the whole ZIP before the first byte leaves it — a festival's
   * backing tracks are hundreds of files and gigabytes — so there is a minutes-long
   * stretch where a spinner is the only sign anything is happening. An organizer who
   * reads that as "сломалось" clicks again, and the second click rebuilds the archive
   * from scratch alongside the first.
   */
  const collect = async (
    fetchArchive: () => Promise<void>,
    setPending: (pending: boolean) => void,
    failure: string,
  ) => {
    setPending(true);
    const waiting = toast.loading("Собираем архив — на большой программе это несколько минут");
    try {
      await fetchArchive();
      toast.success("Архив готов", { id: waiting });
    } catch {
      toast.error(failure, { id: waiting });
    } finally {
      setPending(false);
    }
  };

  const downloadMusic = () =>
    collect(
      () => downloadProgramMusic(program.id, program.name),
      setMusicBusy,
      "Не удалось собрать архив фонограмм",
    );

  const downloadMedia = () =>
    collect(
      () => downloadProgramMedia(program.id, program.name),
      setMediaBusy,
      "Не удалось собрать архив медиафайлов",
    );

  return (
    <div className="flex min-w-0 flex-col gap-3">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <p className="font-medium text-sm">Печать и экспорт</p>
        <div className="flex flex-wrap gap-2">
          <Button
            variant="outline"
            size="sm"
            loading={musicBusy}
            onClick={() => void downloadMusic()}
          >
            <Music className="size-4" /> Скачать фонограммы
          </Button>
          {/* Beside the music, not merged with it: one archive per desk, so the screen
              operator is not handed phonograms and the sound desk is not handed video. */}
          <Button
            variant="outline"
            size="sm"
            loading={mediaBusy}
            onClick={() => void downloadMedia()}
          >
            <Clapperboard className="size-4" /> Скачать видеоматериалы
          </Button>
          <Button
            variant="outline"
            size="sm"
            loading={busy}
            disabled={chosen.length === 0}
            onClick={() => void download()}
          >
            <FileDown className="size-4" /> Скачать PDF
          </Button>
        </div>
      </div>

      {/* `min-w-0`: a `fieldset` has a built-in `min-width: min-content` that ignores its
          container, so a row of column names can widen the layout unless it is overridden. */}
      <fieldset className="flex min-w-0 flex-wrap gap-x-4 gap-y-2 rounded-md border border-border p-3">
        <legend className="px-1 text-muted-foreground text-xs">Колонки в PDF</legend>
        {program.availableColumns.map((column) => (
          <Checkbox
            key={column.key}
            label={column.label}
            checked={columns.includes(column.key)}
            onCheckedChange={(checked) => toggle(column.key, checked === true)}
          />
        ))}
      </fieldset>
      {chosen.length > 1 ? (
        // Order, not selection: the strip reads left to right exactly as the printed page
        // will, so what is being arranged is the page itself rather than a list of names.
        <div className="flex min-w-0 flex-wrap items-center gap-2">
          <span className="text-muted-foreground text-xs">Порядок слева направо:</span>
          {chosen.map((key, index) => (
            <span
              key={key}
              className="flex items-center gap-0.5 rounded-md border border-border py-0.5 pr-0.5 pl-2 text-xs"
            >
              {available.get(key)}
              <Button
                variant="ghost"
                size="xs"
                aria-label={`Левее: ${available.get(key)}`}
                disabled={index === 0}
                onClick={() => shift(key, -1)}
              >
                <ArrowLeft className="size-3.5" />
              </Button>
              <Button
                variant="ghost"
                size="xs"
                aria-label={`Правее: ${available.get(key)}`}
                disabled={index === chosen.length - 1}
                onClick={() => shift(key, 1)}
              >
                <ArrowRight className="size-3.5" />
              </Button>
            </span>
          ))}
        </div>
      ) : null}
      <p className="text-muted-foreground text-xs">
        Таблица печатается на A4 в альбомной ориентации, заголовок повторяется на каждой странице.
      </p>
    </div>
  );
}

function CandidateList({ program }: { program: Program }): React.JSX.Element {
  const { data: candidates, isLoading } = useProgramCandidates(program.id);
  const add = useAddPerformance(program.id);
  const fill = useFillProgram(program.id);

  return (
    <div className="flex flex-col gap-3">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <p className="font-medium text-sm">
          Выступления вне программы
          {candidates ? (
            <span className="ml-2 font-normal text-muted-foreground text-xs">
              ({candidates.length})
            </span>
          ) : null}
        </p>
        <Button
          variant="outline"
          size="sm"
          loading={fill.isPending}
          disabled={!candidates || candidates.length === 0}
          onClick={() =>
            fill.mutate(undefined, {
              onSuccess: () => toast.success("Выступления добавлены"),
              onError: () => toast.error("Не удалось добавить выступления"),
            })
          }
        >
          Добавить все
        </Button>
      </div>

      {isLoading ? <LoadingState label="Загружаем выступления…" size="sm" /> : null}

      {candidates && candidates.length === 0 ? (
        <p className="text-muted-foreground text-xs">Все допущенные выступления уже в программе.</p>
      ) : null}

      {(candidates ?? []).map((candidate) => (
        <div
          key={candidate.submissionId}
          data-testid="program-candidate"
          className="flex flex-wrap items-baseline justify-between gap-2 rounded-md border border-border p-3"
        >
          <div className="min-w-0">
            <p className="font-medium text-sm">{candidate.title}</p>
            <p className="text-muted-foreground text-xs">
              {[candidate.participants[0], candidate.organization].filter(Boolean).join(" · ")}
            </p>
            {/* The composition and the age band decide where an act can go in the day,
                so they belong on the card the organizer picks from — not one click away. */}
            <p className="mt-1 flex flex-wrap gap-1.5 text-xs">
              {[
                candidate.nomination,
                candidate.discipline,
                candidate.participantGroup,
                candidate.ageCategory,
                candidate.participationFormat,
              ]
                .filter((value): value is string => Boolean(value))
                .map((value) => (
                  <Badge key={value} variant="secondary">
                    {value}
                  </Badge>
                ))}
            </p>
          </div>
          <div className="flex items-center gap-2">
            <span className="text-muted-foreground text-xs tabular-nums">
              {formatDuration(candidate.durationSeconds)}
            </span>
            <Button
              variant="outline"
              size="xs"
              loading={add.isPending}
              onClick={() =>
                add.mutate(
                  { submissionId: candidate.submissionId },
                  { onError: () => toast.error("Не удалось добавить выступление") },
                )
              }
            >
              В программу
            </Button>
          </div>
        </div>
      ))}
    </div>
  );
}

function PublicLinks({ program }: { program: Program }): React.JSX.Element {
  const create = useCreateShare(program.id);
  const remove = useRemoveShare(program.id);
  const [name, setName] = useState("");
  const [columns, setColumns] = useState<ColumnKey[]>(DEFAULT_SHARE_COLUMNS);
  const [from, setFrom] = useState("");
  const [to, setTo] = useState("");
  const [controls, setControls] = useState(false);

  const toggle = (key: ColumnKey, checked: boolean) => {
    setColumns((current) =>
      checked
        ? [...current.filter((item) => item !== key), key]
        : current.filter((item) => item !== key),
    );
  };

  const publish = () => {
    // Numbers are what an organizer talks in ("пункты 25-40") and what the table shows;
    // ids are what the API takes, so the range is resolved here against the numbers on
    // screen — not against row indexes, which drift from them after a reorder.
    const start = Number(from) || 0;
    const end = Number(to) || 0;
    const selected =
      start > 0 && end >= start
        ? program.items
            .filter((item) => item.number >= start && item.number <= end)
            .map((item) => item.id)
        : [];
    create.mutate(
      { name: name.trim(), columns, itemIds: selected, controlsRunningOrder: controls },
      {
        onSuccess: () => {
          setName("");
          setColumns(DEFAULT_SHARE_COLUMNS);
          setFrom("");
          setTo("");
          setControls(false);
          toast.success("Публичная программа создана");
        },
        onError: () => toast.error("Не удалось создать публичную программу"),
      },
    );
  };

  return (
    <div className="flex flex-col gap-3">
      <p className="font-medium text-sm">Публичные программы</p>
      <p className="text-muted-foreground text-xs">
        Отметьте колонки, которые нужно показать по ссылке: звукорежиссёру — время, номер и
        комментарий; экрану у сцены — время, участника и номер. Неотмеченные колонки по ссылке не
        передаются вообще.
      </p>

      <div className="flex flex-wrap items-end gap-2">
        <Input
          label="Название ссылки"
          placeholder="Программа звукорежиссёра"
          className="w-56"
          value={name}
          onChange={(event) => setName(event.target.value)}
        />
        <Input
          label="Номера с"
          aria-label="Пункты с"
          type="number"
          min={1}
          className="w-24"
          value={from}
          onChange={(event) => setFrom(event.target.value)}
        />
        <Input
          label="по"
          aria-label="Пункты по"
          type="number"
          min={1}
          className="w-24"
          value={to}
          onChange={(event) => setTo(event.target.value)}
        />
        <Button
          loading={create.isPending}
          disabled={name.trim().length === 0 || columns.length === 0}
          onClick={publish}
        >
          <Link2 className="size-4" /> Создать ссылку
        </Button>
      </div>

      {/* `min-w-0` for the same reason as the export picker's fieldset above. */}
      <fieldset className="flex min-w-0 flex-wrap gap-x-4 gap-y-2 rounded-md border border-border p-3">
        <legend className="px-1 text-muted-foreground text-xs">Колонки для публикации</legend>
        {program.availableColumns.map((column) => (
          <Checkbox
            key={column.key}
            label={column.label}
            checked={columns.includes(column.key)}
            onCheckedChange={(checked) => toggle(column.key, checked === true)}
          />
        ))}
      </fieldset>
      <div className="flex flex-col gap-1">
        <Checkbox
          label="Программа ведущего — можно отмечать номера и менять порядок по ссылке"
          checked={controls}
          onCheckedChange={(checked) => setControls(checked === true)}
        />
        <p className="text-muted-foreground text-xs">
          Такую ссылку давайте только ведущему: любой, у кого она есть, сможет вести программу.
          Остальные ссылки только для чтения.
        </p>
      </div>
      <p className="text-muted-foreground text-xs">
        Оставьте диапазон пунктов пустым, чтобы опубликовать всю программу — такая ссылка сама
        подхватывает новые пункты.
      </p>

      {program.shares.length === 0 ? (
        <p className="text-muted-foreground text-xs">Пока нет публичных программ.</p>
      ) : (
        program.shares.map((share) => (
          <div
            key={share.id}
            className="flex flex-wrap items-center justify-between gap-2 rounded-md border border-border p-3"
          >
            <div className="min-w-0">
              <p className="font-medium text-sm">{share.name}</p>
              <p className="truncate text-muted-foreground text-xs">
                {share.path} ·{" "}
                {share.coversWholeProgram ? "вся программа" : `пунктов: ${share.itemCount}`}
              </p>
              <p className="text-muted-foreground text-xs">
                Колонки: {share.columns.map((column) => column.label).join(", ")}
              </p>
              {share.controlsRunningOrder ? (
                <Badge variant="warning">Ведущий: управляет программой</Badge>
              ) : null}
            </div>
            <div className="flex items-center gap-1">
              <Button
                variant="outline"
                size="xs"
                onClick={() => {
                  void navigator.clipboard
                    ?.writeText(`${window.location.origin}${share.path}`)
                    .then(() => toast.success("Ссылка скопирована"))
                    .catch(() => toast.error("Не удалось скопировать ссылку"));
                }}
              >
                <Copy className="size-4" /> Копировать
              </Button>
              <Button variant="ghost" size="xs" asChild>
                <a href={share.path} target="_blank" rel="noreferrer">
                  Открыть
                </a>
              </Button>
              <AnnounceShare programId={program.id} share={share} />
              <Button
                variant="ghost"
                size="xs"
                aria-label={`Отозвать: ${share.name}`}
                loading={remove.isPending}
                onClick={() =>
                  remove.mutate(share.id, {
                    onError: () => toast.error("Не удалось отозвать ссылку"),
                  })
                }
              >
                <Trash2 className="size-4" />
              </Button>
            </div>
          </div>
        ))
      )}

      {program.items.some((item) => item.missingPerformance) ? (
        <Alert variant="warning">
          В программе есть пункты, номера которых больше не участвуют в фестивале. Проверьте их
          перед публикацией.
        </Alert>
      ) : null}
    </div>
  );
}

/**
 * «Разослать участникам» — the letter that closes the gap between publishing a
 * programme and anyone knowing it exists.
 *
 * It hangs off **one link** rather than off the programme, because the link is the
 * decision: a programme may carry one edition for the hall screen, one for the sound
 * desk and one for participants, and only the organizer knows which of them is the one
 * to send. The edition also settles who hears — one cut to the second отделение writes
 * to the second отделение.
 *
 * Behind a dialog, and the dialog says how many letters it is about to send before it
 * sends them: this is the one action in the constructor that reaches people outside it,
 * and it cannot be taken back.
 */
function AnnounceShare({
  programId,
  share,
}: {
  programId: string;
  share: ProgramShare;
}): React.JSX.Element {
  const announce = useAnnounceShare(programId);
  const [open, setOpen] = useState(false);
  const [note, setNote] = useState("");

  const send = () => {
    announce.mutate(
      { shareId: share.id, ...(note.trim() ? { note: note.trim() } : {}) },
      {
        onSuccess: (result) => {
          setOpen(false);
          setNote("");
          // The skipped acts are named out loud rather than quietly left out of the
          // count: they are the ones the organizer now has to reach some other way.
          toast.success(
            `Разослано писем: ${result.notified}` +
              (result.skipped > 0 ? ` · без адреса: ${result.skipped}` : ""),
          );
        },
        onError: () => toast.error("Не удалось разослать программу"),
      },
    );
  };

  return (
    <>
      <Button
        variant="ghost"
        size="xs"
        aria-label={`Разослать участникам: ${share.name}`}
        onClick={() => setOpen(true)}
      >
        <Send className="size-4" /> Разослать
      </Button>
      <Dialog open={open} onOpenChange={setOpen}>
        <DialogContent className="max-w-lg">
          <DialogHeader>
            <DialogTitle>Разослать программу участникам</DialogTitle>
            <DialogDescription>
              Каждому, кто подал заявку на выступление из этой ссылки, уйдёт письмо с его номером,
              временем и ссылкой на программу. Одно письмо на заявителя, даже если у него несколько
              номеров.
            </DialogDescription>
          </DialogHeader>

          <div className="space-y-3">
            <p className="text-sm">
              Ссылка: <span className="font-medium">{share.name}</span> ·{" "}
              {share.coversWholeProgram ? "вся программа" : `пунктов в ней: ${share.itemCount}`}
            </p>
            <Textarea
              label="Что добавить от себя"
              placeholder="Сбор за час до начала, вход со двора."
              description="Необязательно. Эта строка встанет в письме над ссылкой."
              maxLength={500}
              value={note}
              onChange={(event) => setNote(event.target.value)}
            />
            <Alert variant="warning">
              Письма уйдут сразу и их нельзя отозвать. Проверьте порядок и время перед отправкой.
            </Alert>
          </div>

          <DialogFooter>
            <Button variant="ghost" onClick={() => setOpen(false)}>
              Отмена
            </Button>
            <Button onClick={send} loading={announce.isPending}>
              <Send className="size-4" /> Разослать
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </>
  );
}
