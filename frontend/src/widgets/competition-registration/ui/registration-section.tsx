import { useMemo } from "react";
import type {
  AutosaveState,
  CompetitionSectionId,
  PublicationChecklist,
} from "@/features/competitions";
import type { CompetitionDetail } from "@/shared/api/generated/model-competitions";
import {
  Alert,
  Button,
  Card,
  CardContent,
  CardHeader,
  CardTitle,
  EmptyState,
  PageSection,
} from "@/shared/ui";
import { PublicationChecklistPanel } from "@/widgets/competition-workspace/ui/publication-checklist-panel";
import { NominationRegistration } from "./nomination-registration";

interface RegistrationSectionProps {
  competition: CompetitionDetail;
  checklist: PublicationChecklist;
  isLoading?: boolean;
  onAutosaveStateChange: (state: AutosaveState) => void;
  onNavigateSection: (sectionId: CompetitionSectionId) => void;
}

export function RegistrationSection({
  competition,
  checklist,
  onNavigateSection,
}: RegistrationSectionProps): React.JSX.Element {
  // Registration control is a live action (available after publication); only a
  // completed competition freezes it.
  const isCompleted = competition.status === "COMPLETED";

  const nominations = useMemo(
    () =>
      [...competition.categories].sort(
        (a, b) => a.sortOrder - b.sortOrder || a.name.localeCompare(b.name, "ru"),
      ),
    [competition.categories],
  );

  return (
    <div className="space-y-6">
      <div className="grid gap-6 xl:grid-cols-[minmax(0,1fr)_22rem]">
        <div className="space-y-6">
          {isCompleted ? (
            <Alert variant="warning" title="Фестиваль завершён">
              Регистрацию завершённого фестиваля изменить нельзя.
            </Alert>
          ) : null}

          <PageSection
            title="Регистрация по номинациям"
            description="Задайте окно приёма заявок для каждой номинации или остановите приём досрочно. Приём в номинации открыт только внутри её окна; общего срока регистрации нет."
          >
            <Card className="shadow-none">
              <CardHeader className="pb-3">
                <CardTitle className="text-base">Окна регистрации</CardTitle>
              </CardHeader>
              <CardContent className="space-y-3">
                {nominations.length === 0 ? (
                  <EmptyState
                    title="Номинаций пока нет"
                    description="Сначала добавьте номинации — расписание регистрации задаётся для каждой из них."
                    action={
                      <Button type="button" onClick={() => onNavigateSection("categories")}>
                        Перейти к номинациям
                      </Button>
                    }
                  />
                ) : (
                  <ul className="space-y-3" aria-label="Регистрация по номинациям">
                    {nominations.map((category) => (
                      <li key={category.id}>
                        <NominationRegistration
                          competitionId={competition.id}
                          category={category}
                          disabled={isCompleted}
                        />
                      </li>
                    ))}
                  </ul>
                )}
              </CardContent>
            </Card>
          </PageSection>
        </div>

        <aside className="space-y-4 xl:sticky xl:top-4 xl:self-start">
          <Card className="shadow-none">
            <CardHeader className="pb-3">
              <CardTitle className="text-base">Как это работает</CardTitle>
            </CardHeader>
            <CardContent className="space-y-2 text-muted-foreground text-sm">
              <p>1. У каждой номинации своё окно приёма заявок (начало и конец).</p>
              <p>2. Вне окна или до его настройки приём в номинации закрыт.</p>
              <p>3. Кнопка «Остановить регистрацию» закрывает приём досрочно, не трогая даты.</p>
            </CardContent>
          </Card>
          <PublicationChecklistPanel checklist={checklist} onNavigateSection={onNavigateSection} />
        </aside>
      </div>
    </div>
  );
}
