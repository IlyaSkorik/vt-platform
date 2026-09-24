import { useParams } from "react-router";

import { type BoardEntry, formatScore, useBoard } from "@/features/judging";
import { cn } from "@/shared/lib";
import { useSeo } from "@/shared/seo";
import { EmptyState, LoadingState } from "@/shared/ui";

/**
 * `/board/:slug` — the screen beside the stage.
 *
 * The same idea as the audience vote's board and a different screen: nobody touches it,
 * it is read from the back of a hall, the type is large, and it keeps polling while out
 * of sight because nothing ever brings a projector back to the foreground.
 *
 * What it shows is **not decided here**. A board configured for totals only has no
 * per-judge marks in the payload at all, and one set to «после закрытия» has no score
 * until the host closes the act. That filtering lives on the server, so no amount of
 * fiddling with this page can reveal what the organizer chose to keep quiet.
 */

function Entry({ entry, large }: { entry: BoardEntry; large: boolean }): React.JSX.Element {
  const waiting = entry.score == null;
  return (
    <div
      className={cn(
        "rounded-2xl border bg-card px-8 py-6",
        large ? "border-primary" : "border-border opacity-90",
      )}
    >
      <div className="flex flex-wrap items-baseline gap-x-4 gap-y-1">
        <span
          className={cn(
            "font-semibold text-muted-foreground tabular-nums",
            large ? "text-4xl" : "text-2xl",
          )}
        >
          {entry.number || "—"}
        </span>
        <span className={cn("min-w-0 flex-1 font-semibold", large ? "text-5xl" : "text-3xl")}>
          {entry.title}
        </span>
        {waiting ? (
          <span className={cn("text-muted-foreground", large ? "text-3xl" : "text-xl")}>
            {entry.submittedCount} / {entry.expectedJudges}
          </span>
        ) : (
          <span className={cn("font-bold tabular-nums", large ? "text-6xl" : "text-4xl")}>
            {formatScore(entry.score)}
          </span>
        )}
      </div>

      <p className={cn("mt-1 text-muted-foreground", large ? "text-2xl" : "text-lg")}>
        {[entry.categoryName, entry.ageCategoryName, entry.organization]
          .filter(Boolean)
          .join(" · ")}
      </p>

      {entry.awardLabel != null ? (
        <p className={cn("mt-3 font-semibold text-primary", large ? "text-4xl" : "text-2xl")}>
          {entry.awardLabel}
        </p>
      ) : null}

      {entry.judges.length > 0 ? (
        <ul
          className={cn("mt-4 flex flex-wrap gap-x-8 gap-y-2", large ? "text-2xl" : "text-lg")}
          aria-label="Оценки судей"
        >
          {entry.judges.map((judge) => (
            <li key={judge.name} className="flex items-baseline gap-2">
              <span className="text-muted-foreground">{judge.name}</span>
              <span className="font-semibold tabular-nums">{formatScore(judge.total)}</span>
            </li>
          ))}
        </ul>
      ) : null}

      {waiting && entry.judges.length === 0 ? (
        <p className={cn("mt-3 text-muted-foreground", large ? "text-2xl" : "text-lg")}>
          Идёт оценка…
        </p>
      ) : null}
    </div>
  );
}

export function JudgingBoardPage(): React.JSX.Element {
  const { slug } = useParams();
  const { data: board, isLoading, isError } = useBoard(slug);

  useSeo({ title: board?.competitionTitle ?? "Табло судейства", robots: "noindex" });

  if (isLoading) {
    return (
      <div className="flex min-h-svh items-center justify-center bg-background p-10">
        <LoadingState label="Загружаем табло…" />
      </div>
    );
  }

  if (isError || board == null) {
    return (
      <div className="flex min-h-svh items-center justify-center bg-background p-10">
        <div className="w-full max-w-lg">
          <EmptyState
            title="Табло не найдено"
            description="Проверьте ссылку. Табло перестаёт открываться, когда организатор его выключает."
          />
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-svh bg-background">
      <div className="mx-auto flex w-full max-w-6xl flex-col gap-6 px-8 py-10">
        <header className="text-center">
          <h1 className="font-semibold text-4xl leading-tight">{board.competitionTitle}</h1>
        </header>

        {board.current != null ? (
          <Entry entry={board.current} large />
        ) : (
          <div className="rounded-2xl border border-border bg-card px-8 py-10 text-center">
            <p className="text-3xl text-muted-foreground">Ожидание следующего номера</p>
          </div>
        )}

        {board.recent.length > 0 ? (
          <section className="space-y-3">
            <h2 className="text-center text-2xl text-muted-foreground">Уже оценены</h2>
            <ul className="space-y-3" aria-label="Предыдущие выступления">
              {board.recent.map((entry) => (
                <li key={`${entry.number}-${entry.title}`}>
                  <Entry entry={entry} large={false} />
                </li>
              ))}
            </ul>
          </section>
        ) : null}
      </div>
    </div>
  );
}
