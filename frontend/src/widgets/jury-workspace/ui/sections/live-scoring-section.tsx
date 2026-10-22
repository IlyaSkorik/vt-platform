import { CircleDot, Lock, Play, SkipForward, Square } from "lucide-react";

import {
  formatScore,
  type RunningOrderEntry,
  SCORING_STATUS_LABELS,
  useCloseScoring,
  useJudgingSetup,
  useOpenScoring,
  useRunningOrder,
} from "@/features/judging";
import { ApiError } from "@/shared/api";
import { cn } from "@/shared/lib";
import { Badge, Button, Card, CardContent, EmptyState, LoadingState, toast } from "@/shared/ui";

import { useCompetitionPicker } from "./competition-picker";

/**
 * Ход судейства — the screen the host drives the day from.
 *
 * One act is "on stage" at a time and every judge's tablet follows it, which is the
 * arrangement the organizer chose: the host leads, and a judge may still go back to a
 * number they missed. Opening the next act closes the one before, because that is what
 * pressing «следующий номер» means.
 *
 * The list is the **programme**, in programme order. It used to be the tally, which
 * sorts by score — so every act walked up the screen the moment it was marked, and the
 * host was hunting for the next number in a list that reshuffled under them.
 *
 * Closing is what freezes the marks — and, on a board set to «после закрытия», what
 * puts them on the screen in the hall. So the button says what it does rather than
 * being labelled "готово".
 *
 * Polls while visible: a second organizer at the back of the room may be driving the
 * same programme from their own laptop, and a stale "сейчас на сцене" is how two people
 * close each other's acts.
 */

function statusBadge(status: RunningOrderEntry["status"]): "success" | "secondary" | "warning" {
  if (status === "OPEN") return "success";
  if (status === "CLOSED") return "secondary";
  return "warning";
}

/** «№ 12 · Вокал» — what the host reads out, in one line. */
function actSubtitle(act: RunningOrderEntry): string {
  return [act.categoryName, act.disciplineName, act.ageCategoryName, act.organization]
    .filter(Boolean)
    .join(" · ");
}

export function LiveScoringSection(): React.JSX.Element {
  const { competitionId, picker } = useCompetitionPicker();
  const setupQuery = useJudgingSetup(competitionId || undefined);
  const orderQuery = useRunningOrder(competitionId || undefined, { live: true });
  const open = useOpenScoring(competitionId);
  const close = useCloseScoring(competitionId);

  const setup = setupQuery.data;
  const acts = orderQuery.data ?? [];
  const currentIndex = acts.findIndex((act) => act.status === "OPEN");
  const current = currentIndex === -1 ? undefined : acts[currentIndex];
  // The next act the host has not finished with. From after the open one when there is
  // one, from the top otherwise — so «Следующий номер» resumes a programme picked back
  // up after an interval instead of jumping to its end.
  const next =
    acts.slice(currentIndex + 1).find((act) => act.status !== "CLOSED") ??
    acts.find((act) => act.status === "PENDING");

  const run = async (
    action: typeof open | typeof close,
    submissionId: string,
    message: string,
  ): Promise<void> => {
    try {
      await action.mutateAsync({ competitionId, submissionId });
      toast.success(message);
    } catch (error) {
      toast.error(error instanceof ApiError ? error.message : "Не удалось изменить выступление");
    }
  };

  if (competitionId === "") {
    return <div className="space-y-4">{picker}</div>;
  }

  if (setup != null && !setup.onlineJudging) {
    return (
      <div className="space-y-4">
        {picker}
        <EmptyState
          title="Фестиваль судится вне платформы"
          description="Ведение дня нужно только при онлайн-судействе. Включите его в настройках фестиваля, в разделе «Правила участия»."
        />
      </div>
    );
  }

  if (orderQuery.isLoading) {
    return (
      <div className="space-y-4">
        {picker}
        <LoadingState label="Загружаем программу…" />
      </div>
    );
  }

  if (acts.length === 0) {
    return (
      <div className="space-y-4">
        {picker}
        <EmptyState
          title="Выступлений нет"
          description="Судить нечего: в фестивале нет принятых заявок с выступлениями."
        />
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {picker}

      {current != null ? (
        <Card className="border-primary shadow-none">
          <CardContent className="flex flex-wrap items-center gap-4 py-4">
            <CircleDot className="size-5 shrink-0 text-primary" aria-hidden="true" />
            <div className="min-w-0 flex-1">
              <p className="text-muted-foreground text-xs uppercase tracking-wide">
                Сейчас на сцене
              </p>
              <p className="truncate font-semibold text-lg">
                {current.number > 0 ? `№ ${current.number} · ` : ""}
                {current.title}
              </p>
              <p className="text-muted-foreground text-sm">
                Оценили {current.submittedCount} из {current.expectedJudges}
                {current.score != null ? ` · ${formatScore(current.score)}` : ""}
              </p>
            </div>
            <Button
              type="button"
              variant="outline"
              loading={close.isPending}
              onClick={() => void run(close, current.submissionId, "Выступление закрыто")}
            >
              <Square className="size-4" aria-hidden="true" />
              Закрыть оценку
            </Button>
            {next != null ? (
              // Opening the next act closes this one on the server, so this is one
              // press rather than two — which is what it is in the hall.
              <Button
                type="button"
                loading={open.isPending}
                onClick={() =>
                  void run(
                    open,
                    next.submissionId,
                    `Открыт номер ${next.number > 0 ? next.number : ""} — ${next.title}`.trim(),
                  )
                }
              >
                <SkipForward className="size-4" aria-hidden="true" />
                Следующий номер
              </Button>
            ) : null}
          </CardContent>
        </Card>
      ) : (
        <Card className="shadow-none">
          <CardContent className="flex flex-wrap items-center gap-4 py-4">
            <div className="min-w-0 flex-1">
              <p className="font-medium">Сейчас никто не оценивается</p>
              <p className="text-muted-foreground text-sm">
                {next != null
                  ? `Следующий по программе — ${next.number > 0 ? `№ ${next.number}, ` : ""}«${next.title}».`
                  : "Все номера программы закрыты."}
              </p>
            </div>
            {next != null ? (
              <Button
                type="button"
                loading={open.isPending}
                onClick={() => void run(open, next.submissionId, "Выступление открыто")}
              >
                <Play className="size-4" aria-hidden="true" />
                Открыть номер
              </Button>
            ) : null}
          </CardContent>
        </Card>
      )}

      <ul className="space-y-1.5" aria-label="Программа фестиваля">
        {acts.map((act) => (
          <li key={act.submissionId}>
            <Card
              className={cn(
                "shadow-none",
                act.status === "OPEN" && "border-primary",
                act.status === "CLOSED" && "opacity-80",
              )}
            >
              <CardContent className="flex flex-wrap items-center gap-3 py-2.5">
                <span className="w-8 shrink-0 text-center font-semibold text-muted-foreground text-sm tabular-nums">
                  {act.number > 0 ? act.number : "—"}
                </span>
                <div className="min-w-0 flex-1">
                  <p className="truncate font-medium text-sm">{act.title}</p>
                  <p className="truncate text-muted-foreground text-xs">
                    {actSubtitle(act) || "—"} · оценили {act.submittedCount} из {act.expectedJudges}
                  </p>
                </div>
                <Badge variant={statusBadge(act.status)}>{SCORING_STATUS_LABELS[act.status]}</Badge>
                {act.score != null ? (
                  <span className="font-semibold tabular-nums">{formatScore(act.score)}</span>
                ) : null}
                {act.status === "OPEN" ? (
                  <Button
                    type="button"
                    size="sm"
                    variant="outline"
                    loading={close.isPending}
                    onClick={() => void run(close, act.submissionId, "Выступление закрыто")}
                  >
                    <Lock className="size-4" aria-hidden="true" />
                    Закрыть
                  </Button>
                ) : (
                  <Button
                    type="button"
                    size="sm"
                    loading={open.isPending}
                    onClick={() =>
                      void run(
                        open,
                        act.submissionId,
                        act.status === "CLOSED"
                          ? "Выступление открыто заново"
                          : "Выступление открыто",
                      )
                    }
                  >
                    <Play className="size-4" aria-hidden="true" />
                    {act.status === "CLOSED" ? "Открыть заново" : "Открыть"}
                  </Button>
                )}
              </CardContent>
            </Card>
          </li>
        ))}
      </ul>
    </div>
  );
}
