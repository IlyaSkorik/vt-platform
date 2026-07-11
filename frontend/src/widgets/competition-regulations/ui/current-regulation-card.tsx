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

interface CurrentRegulationCardProps {
  regulation: _Regulation | null;
  isReadOnly: boolean;
  onCreateDraft: () => void;
}

export function CurrentRegulationCard({
  regulation,
  isReadOnly,
  onCreateDraft,
}: CurrentRegulationCardProps): React.JSX.Element {
  const previewUrl = resolveMediaUrl(regulation?.fileReference);

  return (
    <Card className="shadow-none">
      <CardHeader className="pb-3">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div>
            <CardTitle className="text-base">Текущая версия</CardTitle>
            <CardDescription>
              Опубликованное положение неизменяемо. Правки вносятся новой версией.
            </CardDescription>
          </div>
          {regulation ? <Badge variant="success">Текущая</Badge> : null}
        </div>
      </CardHeader>
      <CardContent className="space-y-4">
        {regulation ? (
          <>
            <dl className="grid gap-3 sm:grid-cols-2">
              <div>
                <dt className="text-muted-foreground text-xs">Название</dt>
                <dd className="font-medium text-sm">{regulation.title}</dd>
              </div>
              <div>
                <dt className="text-muted-foreground text-xs">Версия</dt>
                <dd className="font-medium text-sm">{regulation.version}</dd>
              </div>
              <div>
                <dt className="text-muted-foreground text-xs">Дата публикации</dt>
                <dd className="font-medium text-sm">{formatDate(regulation.publicationDate)}</dd>
              </div>
            </dl>

            {previewUrl ? (
              <div className="overflow-hidden rounded-md border border-border bg-muted/20">
                <iframe
                  title={`Превью положения ${regulation.version}`}
                  src={previewUrl}
                  className="h-[28rem] w-full bg-background"
                />
                <div className="flex flex-wrap gap-2 border-border border-t px-3 py-2">
                  <Button asChild size="sm" variant="outline">
                    <a href={previewUrl} target="_blank" rel="noreferrer">
                      Открыть в новой вкладке
                    </a>
                  </Button>
                </div>
              </div>
            ) : (
              <p className="text-muted-foreground text-sm">Файл положения недоступен для превью.</p>
            )}

            {!isReadOnly ? (
              <Button type="button" variant="secondary" onClick={onCreateDraft}>
                Создать новую версию
              </Button>
            ) : null}
          </>
        ) : (
          <div className="space-y-3">
            <p className="text-muted-foreground text-sm">
              Пока нет опубликованного положения. Создайте черновик и опубликуйте первую версию.
            </p>
            {!isReadOnly ? (
              <Button type="button" onClick={onCreateDraft}>
                Создать черновик
              </Button>
            ) : null}
          </div>
        )}
      </CardContent>
    </Card>
  );
}
