import type { RegulationChangeLogEntry } from "@/features/competitions";
import { formatDate } from "@/features/competitions";
import { Badge, Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/shared/ui";

interface RegulationChangeLogProps {
  entries: RegulationChangeLogEntry[];
}

export function RegulationChangeLog({ entries }: RegulationChangeLogProps): React.JSX.Element {
  return (
    <Card className="shadow-none">
      <CardHeader className="pb-3">
        <CardTitle className="text-base">Журнал изменений</CardTitle>
        <CardDescription>
          Каждая публикация — новая неизменяемая запись. Редактирование прошлых версий невозможно.
        </CardDescription>
      </CardHeader>
      <CardContent>
        {entries.length === 0 ? (
          <p className="text-muted-foreground text-sm">Записей пока нет.</p>
        ) : (
          <ol className="space-y-4" aria-label="Журнал изменений положения">
            {entries.map((entry) => (
              <li key={entry.id} className="relative border-border border-l-2 pl-4">
                <div className="mb-1 flex flex-wrap items-center gap-2">
                  <span className="font-medium text-sm">v{entry.version}</span>
                  {entry.isCurrent ? <Badge variant="success">Текущая</Badge> : null}
                  <span className="text-muted-foreground text-xs">
                    {formatDate(entry.publicationDate)}
                  </span>
                </div>
                <p className="text-sm">{entry.title}</p>
                <p className="text-muted-foreground text-xs">{entry.summary}</p>
                {entry.changeNote ? (
                  <p className="mt-1 text-sm italic">{entry.changeNote}</p>
                ) : null}
              </li>
            ))}
          </ol>
        )}
      </CardContent>
    </Card>
  );
}
