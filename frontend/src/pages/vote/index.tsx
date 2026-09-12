import { Check } from "lucide-react";
import { useState } from "react";
import { useParams } from "react-router";

import {
  canPick,
  canVote,
  closedLabel,
  hasVoted,
  type PublicNominee,
  useCastVote,
  usePublicBallot,
  votesLeftLabel,
} from "@/features/public-voting";
import { cn } from "@/shared/lib";
import { useSeo } from "@/shared/seo";
import { Badge, Button, EmptyState, LoadingState, toast } from "@/shared/ui";

/**
 * `/vote/:slug` — the audience vote, as reached from a QR code on a poster.
 *
 * Unauthenticated by design: the slug in the URL is the only input and the only
 * credential. Nobody registers to clap.
 *
 * Built for a phone held at arm's length in a dark hall, which decides most of
 * what is here: one column, cards big enough to hit without aiming, the
 * performance number where the eye lands first (the host just read it out, and
 * that is what the audience remembers — not a name they may not have caught).
 *
 * Voting is a single tap with no confirmation step. A dialog asking "are you
 * sure?" in a hall gets dismissed by reflex, and the thing it guards against —
 * hitting the wrong card — is not worth the people it loses.
 */
export function PublicVotePage(): React.JSX.Element {
  const { slug } = useParams();
  const { data: ballot, isLoading, isError } = usePublicBallot(slug);
  const cast = useCastVote(slug ?? "");
  // Which card was tapped, so only that one shows a spinner rather than the page
  // going inert while the hall waits.
  const [pending, setPending] = useState<string | null>(null);

  // Reachable by anyone with the link, indexed by no one: the list names every
  // performing child. Being handed round the hall is the purpose; being findable
  // by a child's name is not.
  useSeo({ title: ballot?.title ?? "Зрительское голосование", robots: "noindex" });

  if (isLoading) {
    return (
      <div className="flex min-h-svh items-center justify-center bg-background p-6">
        <LoadingState label="Загружаем голосование…" />
      </div>
    );
  }

  if (isError || !ballot) {
    return (
      <div className="flex min-h-svh items-center justify-center bg-background p-6">
        <div className="w-full max-w-md">
          <EmptyState
            title="Голосование не найдено"
            description="Проверьте ссылку или отсканируйте код ещё раз. Возможно, голосование уже завершено."
          />
        </div>
      </div>
    );
  }

  const vote = (nominee: PublicNominee): void => {
    if (!canPick(ballot, nominee)) {
      return;
    }
    setPending(nominee.id);
    cast.mutate([nominee.id], {
      onSuccess: () => toast.success("Голос принят. Спасибо!"),
      onError: (error) => toast.error(error.message || "Не удалось отдать голос"),
      onSettled: () => setPending(null),
    });
  };

  const closed = closedLabel(ballot);
  const allowance = votesLeftLabel(ballot);

  return (
    <div className="min-h-svh bg-background">
      <div className="mx-auto flex w-full max-w-2xl flex-col gap-5 px-4 py-6">
        <header className="flex flex-col gap-2">
          <h1 className="font-semibold text-2xl leading-tight">{ballot.title}</h1>
          {ballot.description ? (
            <p className="text-muted-foreground text-sm">{ballot.description}</p>
          ) : null}

          {closed ? (
            <p className="rounded-md bg-muted px-3 py-2 text-sm">{closed}</p>
          ) : hasVoted(ballot) && ballot.votesLeft === 0 ? (
            <p className="rounded-md bg-success/10 px-3 py-2 text-sm text-success">
              Спасибо! Ваш голос учтён.
            </p>
          ) : (
            <p className="text-muted-foreground text-sm">
              {ballot.votesPerVoter > 1
                ? `Выберите до ${ballot.votesPerVoter} участников`
                : "Выберите одного участника"}
            </p>
          )}

          {allowance ? <p className="text-muted-foreground text-xs">{allowance}</p> : null}
        </header>

        <ul className="flex flex-col gap-3">
          {ballot.nominees.map((nominee) => {
            const pickable = canPick(ballot, nominee);
            return (
              <li key={nominee.id}>
                <button
                  type="button"
                  onClick={() => vote(nominee)}
                  disabled={!pickable || pending !== null}
                  aria-label={`Голосовать за «${nominee.title}»`}
                  className={cn(
                    // Tall enough to hit without aiming: this is tapped in the dark,
                    // one-handed, by somebody who is also applauding.
                    "flex w-full items-center gap-3 rounded-lg border p-4 text-left transition-colors",
                    "min-h-20 outline-none focus-visible:ring-2 focus-visible:ring-ring",
                    nominee.chosen
                      ? "border-success bg-success/10"
                      : pickable
                        ? "border-border hover:bg-accent"
                        : "border-border opacity-60",
                  )}
                >
                  {nominee.number !== null ? (
                    <span className="flex size-11 shrink-0 items-center justify-center rounded-md bg-primary/10 font-semibold text-lg text-primary">
                      {nominee.number}
                    </span>
                  ) : null}

                  <span className="min-w-0 flex-1">
                    <span className="block truncate font-medium">{nominee.title}</span>
                    {nominee.subtitle ? (
                      <span className="mt-0.5 block truncate text-muted-foreground text-sm">
                        {nominee.subtitle}
                      </span>
                    ) : null}
                    {nominee.city ? (
                      <span className="mt-0.5 block truncate text-muted-foreground text-xs">
                        {nominee.city}
                      </span>
                    ) : null}
                  </span>

                  {nominee.chosen ? (
                    <Check className="size-5 shrink-0 text-success" aria-label="Ваш голос" />
                  ) : null}

                  {/* Shown only when the organizer allows it — see `revealTotals`. */}
                  {nominee.votes !== null ? <Badge variant="neutral">{nominee.votes}</Badge> : null}
                </button>
              </li>
            );
          })}
        </ul>

        {ballot.nominees.length === 0 ? (
          <EmptyState
            title="Список пока пуст"
            description="Организатор ещё не добавил участников в это голосование."
          />
        ) : null}

        {ballot.revealTotals && ballot.totalVotes !== null ? (
          <p className="text-center text-muted-foreground text-sm">
            Всего голосов: {ballot.totalVotes}
          </p>
        ) : null}

        {!canVote(ballot) && !closed && hasVoted(ballot) ? (
          <Button variant="ghost" disabled>
            Вы уже проголосовали
          </Button>
        ) : null}
      </div>
    </div>
  );
}
