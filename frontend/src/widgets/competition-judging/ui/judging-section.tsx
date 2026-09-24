import { ArrowRight, Gavel } from "lucide-react";

import {
  type CompetitionSectionId,
  isOnlineJudging,
  type PublicationChecklist,
} from "@/features/competitions";
import { judgingReadiness, useJudgingSetup } from "@/features/judging";
import type { CompetitionDetail } from "@/shared/api/generated/model-competitions";
import { Alert, Button, EmptyState, LoadingState, PageSection } from "@/shared/ui";
import { PublicationChecklistPanel } from "@/widgets/competition-workspace/ui/publication-checklist-panel";
import { AwardScaleCard } from "./award-scale-card";
import { CriteriaCard } from "./criteria-card";
import { BoardSettingsCard, ScoringRulesCard, TallyScopeCard } from "./scoring-rules-card";

/**
 * «Судейство» — how the festival decides who won.
 *
 * The section is always present, whichever mode the festival is on, because one card
 * in it is: the award scale is the vocabulary protocols are written in, and an
 * organizer who hands out "1 место" rather than "Лауреат I степени" needs it whether
 * or not their jury ever logs in.
 *
 * Everything else appears only under online judging, and is deliberately *absent*
 * rather than disabled when it is off — a screen full of greyed-out controls reads as
 * a broken feature, where an explanation and one button reads as a choice.
 */

interface JudgingSectionProps {
  competition: CompetitionDetail;
  checklist: PublicationChecklist;
  isLoading?: boolean;
  onNavigateSection: (sectionId: CompetitionSectionId) => void;
}

export function JudgingSection({
  competition,
  checklist,
  isLoading = false,
  onNavigateSection,
}: JudgingSectionProps): React.JSX.Element {
  const isReadOnly = competition.status === "COMPLETED";
  const online = isOnlineJudging(competition.settings);
  const setupQuery = useJudgingSetup(competition.id);
  const setup = setupQuery.data;

  if (isLoading || setupQuery.isLoading) {
    return (
      <div className="flex min-h-64 items-center justify-center">
        <LoadingState label="Загружаем настройки судейства…" />
      </div>
    );
  }

  if (setup == null) {
    return (
      <EmptyState
        title="Не удалось загрузить судейство"
        description="Обновите страницу. Если не поможет — напишите в поддержку."
      />
    );
  }

  const readiness = judgingReadiness(setup);

  return (
    <div className="grid gap-6 xl:grid-cols-[minmax(0,1fr)_22rem]">
      <div className="min-w-0 space-y-4">
        <PageSection
          title="Судейство"
          description="Шкала наград, критерии оценки, правила подсчёта и табло в зале."
        >
          {isReadOnly ? (
            <Alert variant="warning" title="Фестиваль в архиве">
              Настройки судейства доступны только для просмотра.
            </Alert>
          ) : null}

          <div className="space-y-4">
            {!online ? (
              <Alert variant="info" title="Судейство идёт вне платформы">
                Сейчас фестиваль работает в режиме протоколов: жюри судит как привыкло, а результаты
                вы вносите сами. Шкала наград ниже всё равно нужна — из неё заполняется выпадающий
                список наград в протоколе.
                {!isReadOnly ? (
                  <div className="mt-3">
                    <Button
                      type="button"
                      size="sm"
                      variant="outline"
                      onClick={() => onNavigateSection("settings")}
                    >
                      <Gavel className="size-4" aria-hidden="true" />
                      Включить онлайн-судейство
                      <ArrowRight className="size-4" aria-hidden="true" />
                    </Button>
                  </div>
                ) : null}
              </Alert>
            ) : readiness.ready ? (
              <Alert variant="success" title="Фестиваль готов к онлайн-судейству">
                Критерии заданы, шкала наград с диапазонами, жюри на месте. Ведение дня — во вкладке
                «Жюри».
              </Alert>
            ) : (
              <Alert variant="warning" title="Онлайн-судейство ещё не настроено">
                <ul className="mt-1 list-disc space-y-1 pl-4">
                  {readiness.problems.map((problem) => (
                    <li key={problem}>{problem}</li>
                  ))}
                </ul>
              </Alert>
            )}

            <AwardScaleCard setup={setup} readOnly={isReadOnly} />

            {online ? (
              <>
                <CriteriaCard setup={setup} readOnly={isReadOnly} />
                <ScoringRulesCard setup={setup} readOnly={isReadOnly} />
                <TallyScopeCard setup={setup} readOnly={isReadOnly} />
                <BoardSettingsCard setup={setup} readOnly={isReadOnly} />
              </>
            ) : null}
          </div>
        </PageSection>
      </div>

      <aside className="space-y-4 xl:sticky xl:top-4 xl:self-start">
        <PublicationChecklistPanel checklist={checklist} onNavigateSection={onNavigateSection} />
      </aside>
    </div>
  );
}
