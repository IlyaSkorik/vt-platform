import { useState } from "react";

import {
  JURY_STATUS_LABELS,
  useAssignJuryMember,
  useJudgingSetup,
  useJury,
} from "@/features/judging";
import { ApiError } from "@/shared/api";
import {
  Alert,
  Badge,
  Button,
  Card,
  CardContent,
  Checkbox,
  EmptyState,
  LoadingState,
  toast,
} from "@/shared/ui";

import { useCompetitionPicker } from "./competition-picker";

/**
 * Назначения — which genres each judge sits for.
 *
 * Empty means the whole festival, and that is the default rather than a special case:
 * a small panel judges everything, and making an organizer tick every genre for every
 * judge to express "all of them" would be a form standing in for a shrug.
 *
 * What the assignment actually does is two things, and the screen says both: it decides
 * which acts reach a judge's tablet, and it decides how many sheets an act is *expected*
 * to get — so a judge seated only for вокал does not leave every хореография act reading
 * "3 из 4" all festival.
 */
export function JuryAssignmentsSection(): React.JSX.Element {
  const { competitionId, picker } = useCompetitionPicker();
  const setupQuery = useJudgingSetup(competitionId || undefined);
  const juryQuery = useJury(competitionId || undefined);
  const assign = useAssignJuryMember(competitionId);

  /** Ids being saved right now, so only the row in flight shows a spinner. */
  const [pending, setPending] = useState<string | null>(null);

  const setup = setupQuery.data;
  const members = (juryQuery.data ?? []).filter((member) => member.status !== "REVOKED");

  const toggle = async (memberId: string, categoryId: string, on: boolean): Promise<void> => {
    const member = members.find((item) => item.id === memberId);
    if (member == null) return;
    const next = on
      ? [...new Set([...member.categoryIds, categoryId])]
      : member.categoryIds.filter((item) => item !== categoryId);
    setPending(memberId);
    try {
      await assign.mutateAsync({ memberId, categoryIds: next });
    } catch (error) {
      toast.error(error instanceof ApiError ? error.message : "Не удалось сохранить назначение");
    } finally {
      setPending(null);
    }
  };

  const clearAll = async (memberId: string): Promise<void> => {
    setPending(memberId);
    try {
      await assign.mutateAsync({ memberId, categoryIds: [] });
      toast.success("Судит все жанры");
    } catch (error) {
      toast.error(error instanceof ApiError ? error.message : "Не удалось сохранить назначение");
    } finally {
      setPending(null);
    }
  };

  if (competitionId === "") {
    return <div className="space-y-4">{picker}</div>;
  }

  if (juryQuery.isLoading || setupQuery.isLoading) {
    return (
      <div className="space-y-4">
        {picker}
        <LoadingState label="Загружаем назначения…" />
      </div>
    );
  }

  if (setup != null && setup.nominations.length === 0) {
    return (
      <div className="space-y-4">
        {picker}
        <EmptyState
          title="У фестиваля нет жанров"
          description="Назначать судей не на что. Добавьте жанры в настройках фестиваля, раздел «Жанры и номинации»."
        />
      </div>
    );
  }

  if (members.length === 0) {
    return (
      <div className="space-y-4">
        {picker}
        <EmptyState
          title="Жюри ещё не собрано"
          description="Сначала пригласите судей в разделе «Состав жюри» — потом распределите их по жанрам."
        />
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {picker}

      <Alert variant="info" title="Пусто — значит весь фестиваль">
        Если у судьи не отмечен ни один жанр, он судит все. Отмечайте жанры только тогда, когда жюри
        разделено: от этого зависит и что видит судья, и сколько оценок ждут от каждого номера.
      </Alert>

      <ul className="space-y-2" aria-label="Назначения жюри по жанрам">
        {members.map((member) => (
          <li key={member.id}>
            <Card className="shadow-none">
              <CardContent className="space-y-3 py-3">
                <div className="flex flex-wrap items-center gap-2">
                  <p className="min-w-0 flex-1 font-medium text-sm">
                    {member.fullName}
                    {member.isChair ? (
                      <Badge variant="secondary" className="ml-2">
                        председатель
                      </Badge>
                    ) : null}
                  </p>
                  <Badge variant={member.status === "ACTIVE" ? "success" : "warning"}>
                    {JURY_STATUS_LABELS[member.status]}
                  </Badge>
                  {member.categoryIds.length > 0 ? (
                    <Button
                      type="button"
                      size="sm"
                      variant="ghost"
                      loading={pending === member.id}
                      onClick={() => void clearAll(member.id)}
                    >
                      Судит все жанры
                    </Button>
                  ) : null}
                </div>

                <div className="flex flex-wrap gap-x-6 gap-y-2">
                  {(setup?.nominations ?? []).map((nomination) => (
                    <Checkbox
                      key={nomination.categoryId}
                      label={nomination.name}
                      checked={member.categoryIds.includes(nomination.categoryId)}
                      disabled={pending === member.id}
                      onCheckedChange={(next) =>
                        void toggle(member.id, nomination.categoryId, Boolean(next))
                      }
                    />
                  ))}
                </div>

                {member.categoryIds.length === 0 ? (
                  <p className="text-muted-foreground text-xs">Сейчас судит все жанры.</p>
                ) : null}
              </CardContent>
            </Card>
          </li>
        ))}
      </ul>
    </div>
  );
}
