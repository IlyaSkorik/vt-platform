import { CheckCircle2, Circle } from "lucide-react";
import type { CompetitionSectionId, PublicationChecklist } from "@/features/competitions";
import { cn } from "@/shared/lib";
import { Button, Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/shared/ui";

interface PublicationChecklistPanelProps {
  checklist: PublicationChecklist;
  onNavigateSection: (sectionId: CompetitionSectionId) => void;
}

export function PublicationChecklistPanel({
  checklist,
  onNavigateSection,
}: PublicationChecklistPanelProps): React.JSX.Element {
  return (
    <Card className="shadow-none">
      <CardHeader className="pb-3">
        <CardTitle className="text-base">Чек-лист публикации</CardTitle>
        <CardDescription>
          {checklist.isPublishable
            ? "Все обязательные пункты выполнены. Можно отметить готовность и опубликовать."
            : `Осталось обязательных пунктов: ${checklist.blockingIncomplete}.`}
        </CardDescription>
      </CardHeader>
      <CardContent>
        <ul className="space-y-2" aria-label="Чек-лист публикации">
          {checklist.items.map((item) => (
            <li key={item.id}>
              <Button
                type="button"
                variant="ghost"
                className="h-auto w-full justify-start gap-2 px-2 py-2 text-left font-normal"
                onClick={() => onNavigateSection(item.sectionId)}
              >
                {item.done ? (
                  <CheckCircle2 className="size-4 shrink-0 text-success" aria-hidden="true" />
                ) : (
                  <Circle
                    className={cn(
                      "size-4 shrink-0",
                      item.blocking ? "text-warning" : "text-muted-foreground",
                    )}
                    aria-hidden="true"
                  />
                )}
                <span className="min-w-0 flex-1">
                  <span className="block truncate text-sm">{item.label}</span>
                  <span className="block text-muted-foreground text-xs">
                    {item.done ? "Готово" : item.blocking ? "Обязательно" : "Рекомендуется"}
                  </span>
                </span>
              </Button>
            </li>
          ))}
        </ul>
      </CardContent>
    </Card>
  );
}
