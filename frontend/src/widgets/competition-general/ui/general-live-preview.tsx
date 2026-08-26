import { ImageIcon } from "lucide-react";
import type { GeneralInformationValues } from "@/features/competitions";
import { formatDate, resolveMediaUrl } from "@/features/competitions";
import { Badge, Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/shared/ui";

interface GeneralLivePreviewProps {
  values: GeneralInformationValues;
  statusLabel: string;
}

export function GeneralLivePreview({
  values,
  statusLabel,
}: GeneralLivePreviewProps): React.JSX.Element {
  const periodLabel = (start?: string, end?: string): string => {
    if (!start && !end) {
      return "Не задано";
    }
    if (start && end) {
      const startLabel = formatDate(start);
      const endLabel = formatDate(end);
      return startLabel === endLabel ? startLabel : `${startLabel} — ${endLabel}`;
    }
    return formatDate(start ?? end);
  };

  const posterUrl = resolveMediaUrl(values.poster);

  return (
    <Card className="shadow-none" aria-live="polite">
      <CardHeader className="pb-3">
        <CardTitle className="text-base">Превью</CardTitle>
        <CardDescription>Обновляется по мере заполнения формы.</CardDescription>
      </CardHeader>
      <CardContent className="space-y-5">
        <div className="space-y-2">
          <div className="flex flex-wrap items-center gap-2">
            <h3 className="truncate font-semibold text-lg tracking-tight">
              {values.title.trim() || "Без названия"}
            </h3>
            <Badge variant="outline" size="sm">
              {statusLabel}
            </Badge>
          </div>
          <p className="text-muted-foreground text-sm">
            {values.season.trim() || "Сезон не указан"}
          </p>
          <p className="text-sm leading-relaxed">
            {values.description?.trim() ||
              "Добавьте краткое описание для участников и сотрудников."}
          </p>
        </div>

        <div className="space-y-2">
          <p className="font-medium text-muted-foreground text-xs uppercase tracking-wide">Афиша</p>
          <div className="flex aspect-[3/4] max-h-64 items-center justify-center overflow-hidden rounded-md border bg-muted/30">
            {posterUrl ? (
              <img src={posterUrl} alt="Превью афиши" className="size-full object-contain" />
            ) : (
              <div className="flex flex-col items-center gap-1 text-muted-foreground text-xs">
                <ImageIcon className="size-5" aria-hidden="true" />
                Не загружена
              </div>
            )}
          </div>
        </div>

        <dl className="grid gap-3 text-sm sm:grid-cols-2">
          <div>
            <dt className="text-muted-foreground">Фестиваль</dt>
            <dd className="font-medium">
              {periodLabel(values.competitionStart, values.competitionEnd)}
            </dd>
          </div>
          <div>
            <dt className="text-muted-foreground">Площадка</dt>
            <dd className="font-medium">
              {values.venueName?.trim() || values.venueAddress?.trim() || "Не задано"}
            </dd>
          </div>
          <div>
            <dt className="text-muted-foreground">Соцсети</dt>
            <dd className="truncate font-medium">
              {[values.vk, values.instagram, values.telegram].filter((value) => value?.trim())
                .length > 0
                ? "Указаны"
                : "Не задано"}
            </dd>
          </div>
        </dl>
      </CardContent>
    </Card>
  );
}
