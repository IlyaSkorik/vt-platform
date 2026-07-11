import { formatDate, resolveMediaUrl } from "@/features/competitions";
import type { _Regulation } from "@/shared/api/generated/model-competitions";
import {
  Badge,
  Button,
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/shared/ui";

interface RegulationVersionHistoryProps {
  regulations: _Regulation[];
  isReadOnly: boolean;
  makingCurrentId: string | null;
  removingId: string | null;
  onMakeCurrent: (regulationId: string) => void;
  onRemove: (regulationId: string) => void;
  onPreview: (regulation: _Regulation) => void;
}

export function RegulationVersionHistory({
  regulations,
  isReadOnly,
  makingCurrentId,
  removingId,
  onMakeCurrent,
  onRemove,
  onPreview,
}: RegulationVersionHistoryProps): React.JSX.Element {
  return (
    <Card className="shadow-none">
      <CardHeader className="pb-3">
        <CardTitle className="text-base">История версий</CardTitle>
        <CardDescription>
          Все опубликованные версии. Можно назначить текущую или удалить лишнюю.
        </CardDescription>
      </CardHeader>
      <CardContent>
        {regulations.length === 0 ? (
          <p className="text-muted-foreground text-sm">Опубликованных версий пока нет.</p>
        ) : (
          <ul className="space-y-3" aria-label="История версий положения">
            {regulations.map((regulation) => {
              const previewUrl = resolveMediaUrl(regulation.fileReference);
              return (
                <li key={regulation.id} className="rounded-md border border-border px-3 py-3">
                  <div className="flex flex-wrap items-start justify-between gap-3">
                    <div className="min-w-0 space-y-1">
                      <div className="flex flex-wrap items-center gap-2">
                        <span className="font-medium text-sm">v{regulation.version}</span>
                        {regulation.isCurrent ? <Badge variant="success">Текущая</Badge> : null}
                      </div>
                      <p className="truncate text-sm">{regulation.title}</p>
                      <p className="text-muted-foreground text-xs">
                        Опубликовано: {formatDate(regulation.publicationDate)}
                      </p>
                    </div>
                    <div className="flex flex-wrap gap-2">
                      {previewUrl ? (
                        <Button
                          type="button"
                          size="sm"
                          variant="outline"
                          onClick={() => onPreview(regulation)}
                        >
                          Превью
                        </Button>
                      ) : null}
                      {!isReadOnly && !regulation.isCurrent ? (
                        <Button
                          type="button"
                          size="sm"
                          variant="secondary"
                          loading={makingCurrentId === regulation.id}
                          onClick={() => onMakeCurrent(regulation.id)}
                        >
                          Сделать текущей
                        </Button>
                      ) : null}
                      {!isReadOnly ? (
                        <Button
                          type="button"
                          size="sm"
                          variant="danger"
                          loading={removingId === regulation.id}
                          onClick={() => onRemove(regulation.id)}
                        >
                          Удалить
                        </Button>
                      ) : null}
                    </div>
                  </div>
                </li>
              );
            })}
          </ul>
        )}
      </CardContent>
    </Card>
  );
}
