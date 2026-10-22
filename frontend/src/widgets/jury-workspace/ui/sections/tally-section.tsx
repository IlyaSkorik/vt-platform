import { ChevronDown, FileDown, MessageSquare } from "lucide-react";
import { useState } from "react";

import {
  AGGREGATION_LABELS,
  formatScore,
  useApplyTallyToProtocols,
  useJudgingSetup,
  useTally,
} from "@/features/judging";
import { ApiError } from "@/shared/api";
import { cn } from "@/shared/lib";
import {
  Alert,
  Badge,
  Button,
  Card,
  CardContent,
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  EmptyState,
  LoadingState,
  toast,
} from "@/shared/ui";

import { useCompetitionPicker } from "./competition-picker";

/**
 * Итоги — every act reckoned, and the one button that turns that into protocols.
 *
 * The screen an organizer reads during the interval, so it leads with what is *wrong*:
 * acts that scored but fell into no band, and acts still waiting on a judge. Those are
 * the two things somebody has to act on before a ceremony, and burying them under a
 * table of numbers is how a festival announces a result it did not mean to.
 *
 * Each act expands to the individual sheets, including the comments judges left for the
 * organizer. Those comments go no further: not to the participant, not to the public
 * page, not to the hall's board.
 *
 * Pressing «Перенести в протоколы» is repeatable and does not publish anything: it
 * writes the computed award onto each act's row and leaves the protocol editable, so a
 * hand correction survives until somebody deliberately presses this again.
 *
 * A genre with no protocol open is reported by name rather than counted as "nothing to
 * change" — that conflation is how an organizer reaches a ceremony with empty protocols
 * believing the tally landed. The second press opens those protocols from the programme
 * and writes into them.
 */
export function TallySection(): React.JSX.Element {
  const { competitionId, picker } = useCompetitionPicker();
  const setupQuery = useJudgingSetup(competitionId || undefined);
  const tallyQuery = useTally(competitionId || undefined, { live: true });
  const apply = useApplyTallyToProtocols(competitionId);

  const [expanded, setExpanded] = useState<string | null>(null);
  const [confirming, setConfirming] = useState(false);
  //: Genres the last push found no protocol for — what the second press would open.
  const [missing, setMissing] = useState<string[]>([]);

  const setup = setupQuery.data;
  const tally = tallyQuery.data;
  const groups = tally?.groups ?? [];
  const acts = groups.flatMap((group) => group.tallies);
  const incomplete = acts.filter(
    (act) => act.expectedJudges > 0 && act.submittedCount < act.expectedJudges,
  ).length;

  const handleApply = async (createMissing: boolean): Promise<void> => {
    try {
      const result = await apply.mutateAsync({ createMissing });
      setMissing(result.missingProtocols);
      if (result.missingProtocols.length > 0) {
        // Not an error and not a success: the push did what it could, and the rest has
        // nowhere to land yet. The dialog stays open with the offer to open them.
        toast.warning(`Нет протокола: ${result.missingProtocols.join(", ")}`);
        return;
      }
      const opened =
        result.protocolsCreated > 0 ? `Создано протоколов: ${result.protocolsCreated}. ` : "";
      toast.success(
        result.rowsChanged === 0
          ? `${opened}Изменять нечего: строки протоколов уже совпадают с итогами`
          : `${opened}Обновлено строк в протоколах: ${result.rowsChanged}`,
      );
      setConfirming(false);
    } catch (error) {
      toast.error(error instanceof ApiError ? error.message : "Не удалось перенести итоги");
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
          description="Итоги считаются по оценкам жюри, а их здесь нет. Результаты этого фестиваля ведутся в разделе «Протоколы»."
        />
      </div>
    );
  }

  if (tallyQuery.isLoading) {
    return (
      <div className="space-y-4">
        {picker}
        <LoadingState label="Считаем итоги…" />
      </div>
    );
  }

  if (tally == null || acts.length === 0) {
    return (
      <div className="space-y-4">
        {picker}
        <EmptyState
          title="Считать нечего"
          description="В фестивале нет принятых заявок с выступлениями либо жюри ещё не выставило ни одной оценки."
        />
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {picker}

      <div className="flex flex-wrap items-center justify-between gap-2">
        <p className="text-muted-foreground text-sm">
          {AGGREGATION_LABELS[tally.aggregation]} · выступлений: {acts.length}
        </p>
        <Button
          type="button"
          onClick={() => {
            setMissing([]);
            setConfirming(true);
          }}
        >
          <FileDown className="size-4" aria-hidden="true" />
          Перенести в протоколы
        </Button>
      </div>

      {!tally.scaleIsBanded ? (
        <Alert variant="warning" title="Награды не определяются">
          В шкале наград не заданы диапазоны баллов, поэтому у выступлений есть баллы, но нет
          наград. Задайте диапазоны в настройках фестиваля, раздел «Судейство».
        </Alert>
      ) : tally.unawardedCount > 0 ? (
        <Alert variant="warning" title={`Без награды: ${tally.unawardedCount}`}>
          Эти выступления набрали баллы, но не попали ни в один диапазон шкалы. Так и задумано, если
          фестиваль награждает не всех, — иначе проверьте нижнюю границу шкалы.
        </Alert>
      ) : null}

      {incomplete > 0 ? (
        <Alert variant="info" title={`Оценены не всеми: ${incomplete}`}>
          Кто-то из жюри ещё не отправил лист. Итог считается по тем оценкам, что есть, и
          пересчитается, когда придут остальные.
        </Alert>
      ) : null}

      {groups.map((group) => (
        <section key={group.key} className="space-y-2">
          <h3 className="font-semibold text-sm">{group.heading}</h3>
          <ul className="space-y-1.5" aria-label={`Итоги: ${group.heading}`}>
            {group.tallies.map((act) => {
              const isOpen = expanded === act.submissionId;
              const complete = act.expectedJudges > 0 && act.submittedCount >= act.expectedJudges;
              return (
                <li key={act.submissionId}>
                  <Card className="shadow-none">
                    <CardContent className="p-0">
                      <button
                        type="button"
                        className="flex w-full flex-wrap items-center gap-3 p-3 text-left"
                        onClick={() => setExpanded(isOpen ? null : act.submissionId)}
                        aria-expanded={isOpen}
                      >
                        <ChevronDown
                          className={cn(
                            "size-4 shrink-0 transition-transform",
                            isOpen && "rotate-180",
                          )}
                          aria-hidden="true"
                        />
                        <span className="w-8 shrink-0 text-center font-semibold text-muted-foreground text-sm">
                          {act.number || "—"}
                        </span>
                        <span className="min-w-0 flex-1">
                          <span className="block truncate font-medium text-sm">{act.title}</span>
                          <span className="block truncate text-muted-foreground text-xs">
                            {act.organization ?? "—"} · оценили {act.submittedCount} из{" "}
                            {act.expectedJudges}
                          </span>
                        </span>
                        {act.awardLabel != null ? (
                          <Badge variant="success">{act.awardLabel}</Badge>
                        ) : act.score != null ? (
                          <Badge variant="warning">без награды</Badge>
                        ) : null}
                        <span
                          className={cn(
                            "w-24 shrink-0 text-right font-semibold tabular-nums",
                            !complete && "text-muted-foreground",
                          )}
                        >
                          {formatScore(act.score)}
                          <span className="ml-1 font-normal text-muted-foreground text-xs">
                            / {formatScore(act.maxScore)}
                          </span>
                        </span>
                      </button>

                      {isOpen ? (
                        <div className="space-y-2 border-border border-t p-3">
                          {act.scorecards.length === 0 ? (
                            <p className="text-muted-foreground text-sm">
                              Ни один судья ещё не отправил лист.
                            </p>
                          ) : (
                            <ul className="space-y-1.5">
                              {act.scorecards.map((card) => (
                                <li
                                  key={card.juryMemberId}
                                  className="flex flex-wrap items-start gap-2 text-sm"
                                >
                                  <span className="min-w-0 flex-1">
                                    {card.juryMemberName}
                                    {!card.submitted ? (
                                      <span className="ml-2 text-muted-foreground text-xs">
                                        не отправлено
                                      </span>
                                    ) : null}
                                    {card.comment != null ? (
                                      <span className="mt-0.5 flex items-start gap-1.5 text-muted-foreground text-xs">
                                        <MessageSquare
                                          className="mt-0.5 size-3 shrink-0"
                                          aria-hidden="true"
                                        />
                                        {card.comment}
                                      </span>
                                    ) : null}
                                  </span>
                                  <span className="font-semibold tabular-nums">
                                    {card.submitted ? formatScore(card.total) : "—"}
                                  </span>
                                </li>
                              ))}
                            </ul>
                          )}
                        </div>
                      ) : null}
                    </CardContent>
                  </Card>
                </li>
              );
            })}
          </ul>
        </section>
      ))}

      <Dialog open={confirming} onOpenChange={setConfirming}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Перенести итоги в протоколы?</DialogTitle>
            <DialogDescription>
              В протокол каждого жанра запишутся награды, рассчитанные по баллам. Ничего не
              публикуется: протоколы останутся черновиками и их можно будет поправить руками. Если
              вы уже правили награду вручную, перенос её перезапишет.
            </DialogDescription>
          </DialogHeader>
          {missing.length > 0 ? (
            <Alert variant="warning" title="Протокол ещё не создан">
              Переносить некуда в жанрах: {missing.join(", ")}. Можно создать эти протоколы по
              программе и сразу записать в них итоги — строки возьмутся из порядка выступлений.
            </Alert>
          ) : null}
          <DialogFooter>
            <Button type="button" variant="outline" onClick={() => setConfirming(false)}>
              Отмена
            </Button>
            {missing.length > 0 ? (
              <Button
                type="button"
                loading={apply.isPending}
                onClick={() => void handleApply(true)}
              >
                Создать протоколы и перенести
              </Button>
            ) : (
              <Button
                type="button"
                loading={apply.isPending}
                onClick={() => void handleApply(false)}
              >
                Перенести
              </Button>
            )}
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
