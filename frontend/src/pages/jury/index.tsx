import { Check, CircleDot, Lock } from "lucide-react";
import { useEffect, useMemo, useRef, useState } from "react";
import { useParams } from "react-router";

import {
  formatScore,
  type JuryTask,
  scoreToNumber,
  useJurySeats,
  useJuryTasks,
  useSubmitScorecard,
} from "@/features/judging";
import { ApiError } from "@/shared/api";
import { cn } from "@/shared/lib";
import { useSeo } from "@/shared/seo";
import {
  Alert,
  Badge,
  Button,
  Card,
  CardContent,
  EmptyState,
  LoadingState,
  Select,
  type SelectOption,
  Textarea,
  toast,
} from "@/shared/ui";

/**
 * `/jury/:competitionId` — a judge's own screen.
 *
 * Built for a tablet held in a dark hall by somebody who is also watching a stage, so
 * the marks are buttons rather than a numeric field: typing "9" on a soft keyboard while
 * an act is finishing is how a 9 becomes a 99.
 *
 * The act the host has opened is pinned at the top and the whole list stays below it,
 * because a judge who missed a number has to be able to go back to it — that is the
 * arrangement the organizer chose. What they cannot do is write to a closed act; the
 * server refuses, and the card says so before they try.
 *
 * No participant names anywhere: the number, the act, its genre and the studio. That is
 * ADR-0013, and it is kept at the server's boundary rather than here — there is no name
 * in the payload to leak.
 *
 * The festival list comes from the judge's own seats, never from the organizer's
 * festival endpoint — that one is staff-only and answers a jury member with a 403,
 * which is precisely how this screen used to end up with an empty picker and nothing
 * to score.
 */

function SheetEditor({
  task,
  competitionId,
}: {
  task: JuryTask;
  competitionId: string;
}): React.JSX.Element {
  const submit = useSubmitScorecard(competitionId);
  const [scores, setScores] = useState<Record<string, string>>({});
  const [comment, setComment] = useState("");

  useEffect(() => {
    setScores(Object.fromEntries(task.myScores.map((item) => [item.criterionId, item.score])));
    setComment(task.myComment ?? "");
  }, [task.myScores, task.myComment]);

  const running = task.criteria.reduce(
    (total, criterion) =>
      total + scoreToNumber(scores[criterion.id] ?? "0") * scoreToNumber(criterion.weight),
    0,
  );

  const handleSubmit = async (): Promise<void> => {
    try {
      await submit.mutateAsync({
        competitionId,
        submissionId: task.submissionId,
        scores: Object.fromEntries(
          task.criteria.map((criterion) => [criterion.id, scores[criterion.id] ?? "0"]),
        ),
        comment: comment.trim() || null,
      });
      toast.success("Оценка отправлена");
    } catch (error) {
      toast.error(error instanceof ApiError ? error.message : "Не удалось отправить оценку");
    }
  };

  if (task.criteria.length === 0) {
    return (
      <Alert variant="warning" title="Для этого жанра нет критериев">
        Организатор ещё не задал, по чему оценивать. Сообщите ему — без критериев лист не заполнить.
      </Alert>
    );
  }

  return (
    <div className="space-y-4">
      {task.criteria.map((criterion) => {
        const maximum = Math.round(scoreToNumber(criterion.maxScore));
        const current = scores[criterion.id];
        // One button per whole point, which is how a jury actually marks. A festival
        // scoring out of more than 25 gets a scrollable row rather than a wall.
        const steps = Array.from({ length: maximum + 1 }, (_, index) => index);
        return (
          <div key={criterion.id} className="space-y-1.5">
            <div className="flex flex-wrap items-baseline justify-between gap-2">
              <p className="font-medium text-sm">{criterion.name}</p>
              <p className="text-muted-foreground text-xs">
                до {formatScore(criterion.maxScore)}
                {criterion.weight !== "1.00" && criterion.weight !== "1"
                  ? ` · вес ${formatScore(criterion.weight)}`
                  : ""}
              </p>
            </div>
            {criterion.description != null ? (
              <p className="text-muted-foreground text-xs">{criterion.description}</p>
            ) : null}
            <div className="scrollbar-custom -mx-1 flex gap-1.5 overflow-x-auto px-1 py-1">
              {steps.map((step) => {
                const value = String(step);
                const selected = current != null && scoreToNumber(current) === step;
                return (
                  <button
                    key={step}
                    type="button"
                    disabled={!task.canScore}
                    aria-pressed={selected}
                    aria-label={`${criterion.name}: ${step}`}
                    className={cn(
                      "size-12 shrink-0 rounded-lg border font-semibold text-base tabular-nums transition-colors",
                      selected
                        ? "border-primary bg-primary text-primary-foreground"
                        : "border-border bg-background hover:bg-muted",
                      !task.canScore && "cursor-not-allowed opacity-50",
                    )}
                    onClick={() =>
                      setScores((previous) => ({ ...previous, [criterion.id]: value }))
                    }
                  >
                    {step}
                  </button>
                );
              })}
            </div>
          </div>
        );
      })}

      <Textarea
        label="Комментарий организатору"
        description="Видит только организатор. Участнику не показывается и в протокол не попадает."
        rows={2}
        value={comment}
        disabled={!task.canScore}
        onChange={(event) => setComment(event.target.value)}
      />

      <div className="flex flex-wrap items-center gap-3">
        <Button
          type="button"
          size="lg"
          className="flex-1"
          disabled={!task.canScore}
          loading={submit.isPending}
          onClick={() => void handleSubmit()}
        >
          {task.submittedAt != null ? "Изменить оценку" : "Отправить оценку"}
        </Button>
        <span className="font-semibold text-lg tabular-nums">
          {running.toFixed(2).replace(".", ",")}
          <span className="ml-1 font-normal text-muted-foreground text-sm">
            / {formatScore(task.maxTotal)}
          </span>
        </span>
      </div>

      {!task.canScore ? (
        <p className="text-muted-foreground text-xs">
          {task.status === "CLOSED"
            ? "Ведущий закрыл это выступление — оценка зафиксирована."
            : "Выступление ещё не открыто для оценки."}
        </p>
      ) : null}
    </div>
  );
}

/** «12 мая» — the one thing that tells two festivals of the same name apart. */
function formatSeatDate(value: string): string {
  const parsed = new Date(value);
  return Number.isNaN(parsed.getTime())
    ? value
    : parsed.toLocaleDateString("ru-RU", { day: "numeric", month: "long" });
}

function TaskCard({
  task,
  competitionId,
  expanded,
  onToggle,
}: {
  task: JuryTask;
  competitionId: string;
  expanded: boolean;
  onToggle: () => void;
}): React.JSX.Element {
  return (
    <Card className={cn("shadow-none", task.status === "OPEN" && "border-primary")}>
      <CardContent className="p-0">
        <button
          type="button"
          className="flex w-full flex-wrap items-center gap-3 p-3 text-left"
          onClick={onToggle}
          aria-expanded={expanded}
        >
          <span className="w-9 shrink-0 text-center font-semibold text-lg text-muted-foreground tabular-nums">
            {task.number || "—"}
          </span>
          <span className="min-w-0 flex-1">
            <span className="block truncate font-medium">{task.title}</span>
            <span className="block truncate text-muted-foreground text-xs">
              {[task.categoryName, task.disciplineName, task.ageCategoryName, task.organization]
                .filter(Boolean)
                .join(" · ")}
            </span>
          </span>
          {task.status === "OPEN" ? (
            <Badge variant="success">
              <CircleDot className="size-3" aria-hidden="true" />
              идёт
            </Badge>
          ) : task.status === "CLOSED" ? (
            <Badge variant="secondary">
              <Lock className="size-3" aria-hidden="true" />
              закрыто
            </Badge>
          ) : null}
          {task.submittedAt != null ? (
            <Badge variant="success">
              <Check className="size-3" aria-hidden="true" />
              {formatScore(task.myTotal)}
            </Badge>
          ) : null}
        </button>
        {expanded ? (
          <div className="border-border border-t p-3">
            <SheetEditor task={task} competitionId={competitionId} />
          </div>
        ) : null}
      </CardContent>
    </Card>
  );
}

export function JuryScoringPage(): React.JSX.Element {
  const { competitionId: routeCompetitionId } = useParams();
  const [chosen, setChosen] = useState(routeCompetitionId ?? "");
  const [expanded, setExpanded] = useState<string | null>(null);

  const seatsQuery = useJurySeats();
  const seats = useMemo(() => seatsQuery.data ?? [], [seatsQuery.data]);

  // A judge on one panel — which is most of them — never sees a picker. Making them
  // choose from a list of one is a step between the invitation and the marks that
  // earns nothing.
  const selected =
    chosen !== "" ? chosen : ((seats.length === 1 ? seats[0]?.competitionId : "") ?? "");
  const tasksQuery = useJuryTasks(selected || undefined);

  useSeo({ title: "Оценка выступлений", robots: "noindex" });

  const options: SelectOption[] = useMemo(
    () =>
      seats.map((item) => ({
        value: item.competitionId,
        label:
          item.startsOn != null ? `${item.title} · ${formatSeatDate(item.startsOn)}` : item.title,
      })),
    [seats],
  );

  const tasks = tasksQuery.data ?? [];
  const current = tasks.find((task) => task.status === "OPEN");

  /**
   * The act this screen has already followed the host to.
   *
   * Kept so the follow happens **once per act** rather than on every poll: a judge who
   * collapses the open card would otherwise have it spring open again four seconds
   * later, and one who went back to a missed number would be yanked forward mid-mark.
   */
  const followed = useRef<string | null>(null);

  useEffect(() => {
    if (current != null && followed.current !== current.submissionId) {
      followed.current = current.submissionId;
      setExpanded(current.submissionId);
    }
  }, [current]);

  return (
    <div className="mx-auto flex w-full max-w-3xl flex-col gap-4 p-4">
      <header className="space-y-1">
        <h1 className="font-semibold text-2xl">Оценка выступлений</h1>
        <p className="text-muted-foreground text-sm">
          Ведущий открывает номер — он появится здесь. Пока номер открыт, оценку можно менять.
        </p>
      </header>

      {routeCompetitionId == null && seats.length > 1 ? (
        <Select
          label="Фестиваль"
          placeholder="Выберите фестиваль"
          options={options}
          value={selected}
          onValueChange={setChosen}
        />
      ) : null}

      {seatsQuery.isLoading ? (
        <LoadingState label="Загружаем ваши фестивали…" />
      ) : selected === "" ? (
        <EmptyState
          title="Вас пока не пригласили в жюри"
          description="Приглашение приходит на почту от организатора фестиваля. Примите его по ссылке из письма — после этого фестиваль появится здесь."
        />
      ) : tasksQuery.isLoading ? (
        <LoadingState label="Загружаем выступления…" />
      ) : tasksQuery.isError ? (
        <EmptyState
          title="Нет доступа к оценке"
          description="Возможно, вы не входите в жюри этого фестиваля или организатор не включил онлайн-судейство."
        />
      ) : tasks.length === 0 ? (
        <EmptyState
          title="Выступлений нет"
          description="В жанрах, которые вы судите, пока нет принятых заявок."
        />
      ) : (
        <>
          {current == null ? (
            <Alert variant="info" title="Ждём ведущего">
              Сейчас ни одно выступление не открыто. Можно вернуться к уже открывавшемуся номеру из
              списка ниже.
            </Alert>
          ) : null}
          <ul className="space-y-2" aria-label="Выступления на оценку">
            {tasks.map((task) => (
              <li key={task.submissionId}>
                <TaskCard
                  task={task}
                  competitionId={selected}
                  expanded={expanded === task.submissionId}
                  onToggle={() =>
                    setExpanded(expanded === task.submissionId ? null : task.submissionId)
                  }
                />
              </li>
            ))}
          </ul>
        </>
      )}
    </div>
  );
}
