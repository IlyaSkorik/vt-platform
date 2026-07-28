import { ArrowDown, ArrowUp, Copy, Link2, Plus, Trash2 } from "lucide-react";
import { useEffect, useMemo, useState } from "react";

import { useCompetitionDetail, useCompetitionsList } from "@/features/competitions";
import {
  BUFFER_PRESETS,
  ITEM_KIND_LABELS,
  moveItem,
  type Program,
  type ProgramItem,
  useAddBlock,
  useAddPerformance,
  useCreateProgram,
  useCreateShare,
  useEditItem,
  useFillProgram,
  useProgram,
  useProgramCandidates,
  usePrograms,
  useRemoveItem,
  useRemoveShare,
  useReorderItems,
  useUpdateProgram,
} from "@/features/program-builder";
import { formatClock, formatDuration, formatSpan } from "@/shared/lib";
import {
  Alert,
  Badge,
  Button,
  Card,
  CardContent,
  Divider,
  EmptyState,
  Input,
  LoadingState,
  PageContainer,
  PageContent,
  PageDescription,
  PageHeader,
  PageTitle,
  Select,
  toast,
} from "@/shared/ui";

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
    <PageContainer>
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

        {competitionId ? (
          <div className="grid gap-4 lg:grid-cols-[320px_minmax(0,1fr)]">
            <div className="flex flex-col gap-4">
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

            {programId ? (
              <ProgramWorkspace programId={programId} />
            ) : (
              <EmptyState
                title="Программа не выбрана"
                description="Выберите программу слева или создайте новую — например, отдельную на каждую номинацию."
              />
            )}
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
        description="Создайте первую программу — обычно по одной на номинацию."
      />
    );
  }
  return (
    <div className="flex flex-col gap-2">
      <p className="font-medium text-sm">Программы</p>
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
        // A local "2026-08-01T10:00" is what the organizer typed in their own zone;
        // the Date round-trip is what turns it into the instant the backend stores.
        startsAt: startsAt ? new Date(startsAt).toISOString() : null,
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
          label="Номинация"
          placeholder="Весь фестиваль"
          options={nominations}
          value={nominationId}
          onValueChange={setNominationId}
        />
        <Input
          label="Начало"
          type="datetime-local"
          value={startsAt}
          onChange={(event) => setStartsAt(event.target.value)}
        />
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
    <div className="flex flex-col gap-4">
      <ProgramSettings program={program} />
      <Divider />
      <RunningOrder program={program} />
      <Divider />
      <CandidateList program={program} />
      <Divider />
      <PublicLinks program={program} />
    </div>
  );
}

function ProgramSettings({ program }: { program: Program }): React.JSX.Element {
  const update = useUpdateProgramSettings(program.id);
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
            label: seconds === 0 ? "Без буфера" : formatDuration(seconds),
          }))}
          value={String(program.bufferSeconds)}
          onValueChange={(value: string) => update.setBuffer(Number(value))}
          description="Добавляется к каждому выступлению при расчёте расписания и не меняет длительность номера."
        />
        <Input
          label="Начало программы"
          type="datetime-local"
          value={toLocalInput(program.startsAt)}
          onChange={(event) => update.setStart(event.target.value)}
        />
      </div>
    </div>
  );
}

/** The two program-level settings, as one small hook so the form stays declarative. */
function useUpdateProgramSettings(programId: string) {
  const update = useUpdateProgram(programId);
  return {
    setBuffer: (bufferSeconds: number) =>
      update.mutate({ bufferSeconds }, { onError: () => toast.error("Не удалось изменить буфер") }),
    setStart: (localValue: string) =>
      update.mutate(
        { startsAt: localValue ? new Date(localValue).toISOString() : null },
        { onError: () => toast.error("Не удалось изменить время начала") },
      ),
  };
}

function RunningOrder({ program }: { program: Program }): React.JSX.Element {
  const reorder = useReorderItems(program.id);
  const remove = useRemoveItem(program.id);
  const items = program.items;

  const move = (from: number, to: number) => {
    const next = moveItem(items, from, to).map((item) => item.id);
    reorder.mutate(next, { onError: () => toast.error("Не удалось изменить порядок") });
  };

  return (
    <div className="flex flex-col gap-3">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <p className="font-medium text-sm">Программа</p>
        <AddBreakControls programId={program.id} />
      </div>

      {items.length === 0 ? (
        <EmptyState
          title="Программа пуста"
          description="Добавьте выступления из списка ниже или вставьте служебный блок."
        />
      ) : (
        <ol className="flex flex-col gap-2">
          {items.map((item, index) => (
            <ProgramItemRow
              key={item.id}
              item={item}
              index={index}
              total={items.length}
              busy={reorder.isPending || remove.isPending}
              onUp={() => move(index, index - 1)}
              onDown={() => move(index, index + 1)}
              onRemove={() =>
                remove.mutate(item.id, { onError: () => toast.error("Не удалось удалить пункт") })
              }
              programId={program.id}
            />
          ))}
        </ol>
      )}
    </div>
  );
}

function ProgramItemRow({
  item,
  index,
  total,
  busy,
  onUp,
  onDown,
  onRemove,
  programId,
}: {
  item: ProgramItem;
  index: number;
  total: number;
  busy: boolean;
  onUp: () => void;
  onDown: () => void;
  onRemove: () => void;
  programId: string;
}): React.JSX.Element {
  const isPerformance = item.kind === "PERFORMANCE";
  return (
    <li
      data-testid="program-item"
      className={
        isPerformance
          ? "flex flex-wrap items-baseline gap-3 rounded-md border border-border p-3"
          : "flex flex-wrap items-baseline gap-3 rounded-md border border-border border-dashed bg-muted/40 p-3"
      }
    >
      <span className="w-14 shrink-0 font-semibold text-sm tabular-nums">
        {formatClock(item.schedule.startsAt)}
      </span>
      <span className="w-6 shrink-0 text-muted-foreground text-xs tabular-nums">
        {item.schedule.position}
      </span>

      <div className="min-w-0 flex-1 space-y-1">
        <div className="flex flex-wrap items-baseline gap-2">
          <p className="font-medium text-sm">{item.title}</p>
          {/* The badge names the kind; a break literally titled "Перерыв" needs no
              second label saying so. */}
          {isPerformance || item.title === ITEM_KIND_LABELS[item.kind] ? null : (
            <Badge variant="secondary">{ITEM_KIND_LABELS[item.kind]}</Badge>
          )}
          {item.missingPerformance ? <Badge variant="warning">Номер снят</Badge> : null}
        </div>
        {item.leadParticipant ? (
          <p className="text-muted-foreground text-xs">
            {item.leadParticipant}
            {item.organization ? ` · ${item.organization}` : ""}
            {item.nomination ? ` · ${item.nomination}` : ""}
          </p>
        ) : null}
        {item.comment ? (
          <p className="whitespace-pre-line text-muted-foreground text-xs">{item.comment}</p>
        ) : null}
      </div>

      <span className="shrink-0 text-muted-foreground text-xs tabular-nums">
        {formatDuration(item.durationSeconds)}
        {item.schedule.slotSeconds !== item.durationSeconds
          ? ` (+${formatDuration(item.schedule.slotSeconds - item.durationSeconds)})`
          : ""}
      </span>

      <div className="flex shrink-0 items-center gap-1">
        {isPerformance ? null : <EditBlockDuration programId={programId} item={item} />}
        <Button
          variant="ghost"
          size="xs"
          aria-label={`Вверх: ${item.title}`}
          disabled={index === 0 || busy}
          onClick={onUp}
        >
          <ArrowUp className="size-4" />
        </Button>
        <Button
          variant="ghost"
          size="xs"
          aria-label={`Вниз: ${item.title}`}
          disabled={index === total - 1 || busy}
          onClick={onDown}
        >
          <ArrowDown className="size-4" />
        </Button>
        <Button
          variant="ghost"
          size="xs"
          aria-label={`Удалить: ${item.title}`}
          disabled={busy}
          onClick={onRemove}
        >
          <Trash2 className="size-4" />
        </Button>
      </div>
    </li>
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
        className="h-8 w-16"
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
          className="flex flex-wrap items-baseline justify-between gap-2 rounded-md border border-border p-3"
        >
          <div className="min-w-0">
            <p className="font-medium text-sm">{candidate.title}</p>
            <p className="text-muted-foreground text-xs">
              {[candidate.participants[0], candidate.nomination, candidate.discipline]
                .filter(Boolean)
                .join(" · ")}
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
  const [from, setFrom] = useState("");
  const [to, setTo] = useState("");

  const publish = () => {
    // Positions are what an organizer talks in ("пункты 25-40"); ids are what the API
    // takes, so the range is resolved here against the order on screen.
    const start = Number(from) || 0;
    const end = Number(to) || 0;
    const selected =
      start > 0 && end >= start
        ? program.items
            .filter((item) => item.schedule.position >= start && item.schedule.position <= end)
            .map((item) => item.id)
        : [];
    create.mutate(
      { name: name.trim(), itemIds: selected },
      {
        onSuccess: () => {
          setName("");
          setFrom("");
          setTo("");
          toast.success("Публичная программа создана");
        },
        onError: () => toast.error("Не удалось создать публичную программу"),
      },
    );
  };

  return (
    <div className="flex flex-col gap-3">
      <p className="font-medium text-sm">Публичные программы</p>

      <div className="flex flex-wrap items-end gap-2">
        <Input
          label="Название ссылки"
          placeholder="Программа звукорежиссёра"
          className="w-56"
          value={name}
          onChange={(event) => setName(event.target.value)}
        />
        <Input
          label="Пункты с"
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
        <Button loading={create.isPending} disabled={name.trim().length === 0} onClick={publish}>
          <Link2 className="size-4" /> Создать ссылку
        </Button>
      </div>
      <p className="text-muted-foreground text-xs">
        Оставьте диапазон пустым, чтобы опубликовать всю программу — такая ссылка сама подхватывает
        новые пункты.
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

/** ISO instant → the value a ``datetime-local`` input expects, in the local zone. */
function toLocalInput(iso: string | null): string {
  if (!iso) {
    return "";
  }
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) {
    return "";
  }
  const pad = (value: number) => String(value).padStart(2, "0");
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}T${pad(date.getHours())}:${pad(date.getMinutes())}`;
}
