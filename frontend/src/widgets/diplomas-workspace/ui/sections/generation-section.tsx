import { FileArchive, FileCheck2, Sparkles } from "lucide-react";
import { Badge, Card, CardContent, CardHeader, CardTitle } from "@/shared/ui";

const UPCOMING = [
  {
    icon: FileCheck2,
    title: "Выбор конкурса и предпросмотр",
    description: "Выбор конкурса, проверка назначенных шаблонов и охвата участников.",
  },
  {
    icon: Sparkles,
    title: "Генерация дипломов",
    description: "Массовое формирование PDF по назначенным шаблонам.",
  },
  {
    icon: FileArchive,
    title: "ZIP-архив и статистика",
    description: "Скачивание пакета одним файлом и сводка по выпущенным дипломам.",
  },
];

export function GenerationSection(): React.JSX.Element {
  return (
    <div className="flex flex-col gap-6">
      <div className="rounded-lg border border-border border-dashed bg-muted/30 p-6 text-center">
        <span className="mx-auto flex size-12 items-center justify-center rounded-full bg-primary/10 text-primary">
          <Sparkles className="size-6" aria-hidden="true" />
        </span>
        <h3 className="mt-3 font-semibold text-foreground text-lg">Генерация скоро появится</h3>
        <p className="mx-auto mt-1 max-w-md text-muted-foreground text-sm">
          Здесь можно будет выбрать конкурс и сформировать дипломы по назначенным шаблонам, а затем
          скачать их архивом. Сейчас раздел в разработке.
        </p>
        <Badge variant="secondary" className="mt-4">
          В разработке
        </Badge>
      </div>
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {UPCOMING.map((item) => {
          const Icon = item.icon;
          return (
            <Card key={item.title}>
              <CardHeader className="flex-row items-center gap-3 space-y-0">
                <span className="flex size-9 shrink-0 items-center justify-center rounded-md bg-accent text-accent-foreground">
                  <Icon className="size-4" aria-hidden="true" />
                </span>
                <CardTitle className="text-base">{item.title}</CardTitle>
              </CardHeader>
              <CardContent className="pt-0 text-muted-foreground text-sm">
                {item.description}
              </CardContent>
            </Card>
          );
        })}
      </div>
    </div>
  );
}
