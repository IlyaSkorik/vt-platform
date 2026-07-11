import { Layers3 } from "lucide-react";
import type { CompetitionSectionId, PublicationChecklist } from "@/features/competitions";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/shared/ui";
import { PublicationChecklistPanel } from "./publication-checklist-panel";

interface SectionPlaceholderProps {
  title: string;
  checklist: PublicationChecklist;
  onNavigateSection: (sectionId: CompetitionSectionId) => void;
}

export function SectionPlaceholder({
  title,
  checklist,
  onNavigateSection,
}: SectionPlaceholderProps): React.JSX.Element {
  return (
    <div className="grid gap-6 xl:grid-cols-[minmax(0,1fr)_22rem]">
      <Card className="shadow-none">
        <CardHeader>
          <div className="flex items-start gap-3">
            <div className="flex size-10 items-center justify-center rounded-md bg-muted text-muted-foreground">
              <Layers3 className="size-4" aria-hidden="true" />
            </div>
            <div>
              <CardTitle>{title}</CardTitle>
              <CardDescription>Этот раздел будет реализован в следующей итерации.</CardDescription>
            </div>
          </div>
        </CardHeader>
        <CardContent>
          <p className="text-muted-foreground text-sm leading-relaxed">
            Оболочка рабочего пространства и навигация уже готовы. В следующих релизах здесь
            появится полноценное редактирование для раздела «{title}».
          </p>
        </CardContent>
      </Card>
      <aside className="xl:sticky xl:top-4 xl:self-start">
        <PublicationChecklistPanel checklist={checklist} onNavigateSection={onNavigateSection} />
      </aside>
    </div>
  );
}
