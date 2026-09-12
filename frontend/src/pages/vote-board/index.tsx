import { useParams } from "react-router";

import { barWidth, closedLabel, ranked, usePublicBallot } from "@/features/public-voting";
import { useSeo } from "@/shared/seo";
import { EmptyState, LoadingState } from "@/shared/ui";

/**
 * `/vote/:slug/board` — the scoreboard for the projector beside the stage.
 *
 * The same ballot as the voting page and a deliberately different screen. Nobody
 * touches this one: it is read from the back of a hall, so there is nothing to tap,
 * the type is large, and the whole thing is one column of bars that can be taken in
 * at a glance while the next act is being announced.
 *
 * It keeps polling while out of sight, unlike a voter's phone. Nothing ever brings
 * a projector back to the foreground, and it has to be right whenever somebody
 * looks up at it.
 *
 * If the ballot hides its count, this page says so rather than showing zeroes: a
 * board full of noughts reads as "nobody voted", which is a lie about a vote that
 * is deliberately being kept quiet.
 */
export function PublicVoteBoardPage(): React.JSX.Element {
  const { slug } = useParams();
  const { data: ballot, isLoading, isError } = usePublicBallot(slug, { live: true });

  useSeo({ title: ballot?.title ?? "Результаты голосования", robots: "noindex" });

  if (isLoading) {
    return (
      <div className="flex min-h-svh items-center justify-center bg-background p-10">
        <LoadingState label="Загружаем табло…" />
      </div>
    );
  }

  if (isError || !ballot) {
    return (
      <div className="flex min-h-svh items-center justify-center bg-background p-10">
        <div className="w-full max-w-lg">
          <EmptyState title="Голосование не найдено" description="Проверьте ссылку на табло." />
        </div>
      </div>
    );
  }

  const rows = ranked(ballot.nominees);
  const closed = closedLabel(ballot);

  return (
    <div className="min-h-svh bg-background">
      <div className="mx-auto flex w-full max-w-5xl flex-col gap-8 px-8 py-10">
        <header className="flex flex-col gap-2 text-center">
          <h1 className="font-semibold text-4xl leading-tight">{ballot.title}</h1>
          {closed ? (
            <p className="text-muted-foreground text-xl">{closed}</p>
          ) : (
            <p className="text-muted-foreground text-xl">Идёт голосование</p>
          )}
        </header>

        {!ballot.revealTotals ? (
          <EmptyState
            title="Результаты скрыты до завершения"
            description="Организатор откроет счёт, когда голосование закончится."
          />
        ) : (
          <ol className="flex flex-col gap-4">
            {rows.map((nominee, index) => (
              <li key={nominee.id} className="flex items-center gap-5">
                <span className="w-12 shrink-0 text-right font-semibold text-3xl text-muted-foreground tabular-nums">
                  {index + 1}
                </span>
                <span className="min-w-0 flex-1">
                  <span className="flex items-baseline justify-between gap-4">
                    <span className="truncate font-medium text-2xl">
                      {nominee.number !== null ? `${nominee.number}. ` : ""}
                      {nominee.title}
                    </span>
                    <span className="shrink-0 font-semibold text-3xl tabular-nums">
                      {nominee.votes ?? 0}
                    </span>
                  </span>
                  {nominee.subtitle ? (
                    <span className="mt-1 block truncate text-muted-foreground text-lg">
                      {nominee.subtitle}
                    </span>
                  ) : null}
                  {/* Bars are scaled to the leader, not to the total: a bar chart is
                      read by comparing lengths, and scaling to the total leaves every
                      bar short and indistinguishable when the field is wide. */}
                  <span className="mt-2 block h-3 w-full overflow-hidden rounded-full bg-muted">
                    <span
                      className="block h-full rounded-full bg-primary transition-[width] duration-500"
                      style={{ width: `${barWidth(nominee, rows)}%` }}
                    />
                  </span>
                </span>
              </li>
            ))}
          </ol>
        )}

        {ballot.revealTotals && ballot.totalVotes !== null ? (
          <p className="text-center text-muted-foreground text-xl">
            Всего голосов: {ballot.totalVotes}
          </p>
        ) : null}
      </div>
    </div>
  );
}
