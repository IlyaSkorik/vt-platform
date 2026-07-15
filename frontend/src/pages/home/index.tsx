import { ArrowRight, CheckCircle2, Sparkles } from "lucide-react";
import { Link } from "react-router";
import { useAuth } from "@/app/providers";
import { formatPeriod, resolveMediaUrl, usePublicFestivals } from "@/features/festival-catalog";
import { ROUTES } from "@/shared/config";
import {
  Badge,
  Button,
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
  LoadingState,
  PageContainer,
  PageContent,
} from "@/shared/ui";

/**
 * Public marketing + conversion page.
 */
export function HomePage(): React.JSX.Element {
  const { isAuthenticated } = useAuth();
  const festivalsQuery = usePublicFestivals();
  const featured = (festivalsQuery.data ?? []).slice(0, 3);
  const cabinetCatalogPath = ROUTES.cabinetCompetitions;
  const primaryCta = isAuthenticated
    ? cabinetCatalogPath
    : `${ROUTES.login}?next=${encodeURIComponent(cabinetCatalogPath)}`;

  return (
    <>
      <section className="relative isolate overflow-hidden border-border border-b bg-gradient-to-br from-primary/10 via-background to-secondary/10">
        <div className="absolute inset-0">
          <div className="absolute -top-8 -right-8 h-40 w-40 rounded-full bg-primary/10 blur-3xl" />
          <div className="absolute -bottom-10 -left-10 h-48 w-48 rounded-full bg-secondary/10 blur-3xl" />
        </div>
        <div className="mx-auto flex min-h-[calc(100svh-4rem)] w-full max-w-7xl items-center px-4 py-10 md:px-8 md:py-14">
          <div className="relative max-w-3xl space-y-5">
            <Badge variant="outline" icon={<Sparkles className="size-3.5" />}>
              Платформа фестивалей
            </Badge>
            <h1 className="text-balance font-bold text-4xl tracking-tight sm:text-5xl md:text-6xl">
              Взлёт талантов
            </h1>
            <p className="text-pretty text-lg text-muted-foreground md:text-xl">
              Выбирайте фестиваль, подавайте заявку онлайн и отслеживайте статус в личном кабинете
              без бумажной рутины.
            </p>
            <div className="flex flex-wrap items-center gap-3">
              <Button asChild size="lg">
                <Link to={primaryCta}>
                  Найти фестиваль
                  <ArrowRight className="size-4" aria-hidden="true" />
                </Link>
              </Button>
              <Button asChild size="lg" variant="outline">
                <Link to={ROUTES.competitions}>Публичный каталог</Link>
              </Button>
            </div>
            <div className="flex flex-wrap gap-2 pt-1">
              <Badge variant="secondary">Онлайн-подача заявок</Badge>
              <Badge variant="secondary">Прозрачные статусы</Badge>
              <Badge variant="secondary">Педагоги и участники в одном кабинете</Badge>
            </div>
          </div>
        </div>
      </section>

      <PageContainer size="wide">
        <PageContent className="space-y-16 py-10 md:py-14">
        <section className="space-y-5">
          <div className="space-y-1">
            <h2 className="text-2xl font-semibold tracking-tight">Как это работает</h2>
            <p className="text-muted-foreground">
              Простой путь от регистрации до отправленной заявки.
            </p>
          </div>
          <div className="grid gap-4 md:grid-cols-4">
            {[
              { title: "Регистрация", text: "Создайте аккаунт и подтвердите email." },
              { title: "Выбор фестиваля", text: "Откройте каталог и сравните условия." },
              { title: "Заполнение заявки", text: "Добавьте выступления, услуги и согласия." },
              { title: "Отслеживание", text: "Смотрите статус заявки в кабинете." },
            ].map((step, index) => (
              <Card key={step.title} className="shadow-none">
                <CardHeader className="pb-2">
                  <CardDescription>Шаг {index + 1}</CardDescription>
                  <CardTitle className="text-base">{step.title}</CardTitle>
                </CardHeader>
                <CardContent className="text-sm text-muted-foreground">{step.text}</CardContent>
              </Card>
            ))}
          </div>
        </section>

        <section className="space-y-5">
          <div className="flex flex-wrap items-end justify-between gap-3">
            <div className="space-y-1">
              <h2 className="text-2xl font-semibold tracking-tight">Актуальные фестивали</h2>
              <p className="text-muted-foreground">
                Открывайте карточки фестивалей и переходите к подаче заявки.
              </p>
            </div>
            <Button asChild variant="outline" size="sm">
              <Link to={ROUTES.competitions}>Смотреть все</Link>
            </Button>
          </div>
          {festivalsQuery.isPending ? (
            <LoadingState label="Загружаем фестивали…" />
          ) : (
            <div className="grid gap-4 md:grid-cols-3">
              {featured.map((festival) => (
                <Card key={festival.id} className="shadow-none">
                  <div className="aspect-[16/9] overflow-hidden rounded-t-xl bg-muted">
                    {resolveMediaUrl(festival.coverImage) ? (
                      <img
                        src={resolveMediaUrl(festival.coverImage) ?? ""}
                        alt={`Афиша фестиваля ${festival.title}`}
                        className="size-full object-cover"
                        loading="lazy"
                      />
                    ) : (
                      <div className="flex size-full items-center justify-center text-xs text-muted-foreground">
                        Афиша скоро появится
                      </div>
                    )}
                  </div>
                  <CardHeader className="space-y-1">
                    <CardTitle className="line-clamp-2 text-base">{festival.title}</CardTitle>
                    <CardDescription className="line-clamp-1">
                      {festival.organizer.name}
                    </CardDescription>
                  </CardHeader>
                  <CardContent className="space-y-3">
                    <p className="text-xs text-muted-foreground">
                      {formatPeriod(festival.competitionStart, festival.competitionEnd) ?? "Даты уточняются"}
                    </p>
                    <p className="line-clamp-2 text-sm text-muted-foreground">
                      {festival.description || "Подробности доступны на странице фестиваля."}
                    </p>
                    <Button asChild variant="outline" size="sm" className="w-full">
                      <Link to={`${ROUTES.competitions}/${festival.id}`}>Открыть фестиваль</Link>
                    </Button>
                  </CardContent>
                </Card>
              ))}
            </div>
          )}
        </section>

        <section className="space-y-5">
          <div className="space-y-1">
            <h2 className="text-2xl font-semibold tracking-tight">Кому подходит платформа</h2>
            <p className="text-muted-foreground">
              Один сервис для всех ролей в фестивальном процессе.
            </p>
          </div>
          <div className="grid gap-4 md:grid-cols-3">
            <Card className="shadow-none">
              <CardHeader>
                <CardTitle className="text-base">Участникам</CardTitle>
              </CardHeader>
              <CardContent className="text-sm text-muted-foreground">
                Быстрая подача заявок, хранение данных профиля и понятный статус по каждому
                фестивалю.
              </CardContent>
            </Card>
            <Card className="shadow-none">
              <CardHeader>
                <CardTitle className="text-base">Педагогам</CardTitle>
              </CardHeader>
              <CardContent className="text-sm text-muted-foreground">
                Удобное сопровождение учеников и работа с заявками без дублей и ручных таблиц.
              </CardContent>
            </Card>
            <Card className="shadow-none">
              <CardHeader>
                <CardTitle className="text-base">Организаторам</CardTitle>
              </CardHeader>
              <CardContent className="text-sm text-muted-foreground">
                Единое рабочее пространство фестиваля: структура, правила, публичная страница и
                приём заявок.
              </CardContent>
            </Card>
          </div>
        </section>

        <section className="space-y-5">
          <div className="space-y-1">
            <h2 className="text-2xl font-semibold tracking-tight">Частые вопросы</h2>
          </div>
          <div className="grid gap-3 md:grid-cols-2">
            {[
              "Можно ли смотреть фестивали без регистрации? Да, каталог и страницы фестивалей открыты.",
              "Когда нужна регистрация? Только для подачи и управления заявками.",
              "Можно ли отредактировать заявку? Да, пока она в статусе черновика.",
              "Где смотреть документы? Внизу сайта доступны политика ПДн и cookies.",
            ].map((item) => (
              <div key={item} className="rounded-lg border border-border bg-card px-4 py-3 text-sm">
                {item}
              </div>
            ))}
          </div>
        </section>

        <section className="rounded-2xl border border-border bg-card p-8 text-center md:p-10">
          <div className="mx-auto max-w-2xl space-y-4">
            <Badge variant="success" icon={<CheckCircle2 className="size-3.5" />}>
              Всё готово для старта
            </Badge>
            <h2 className="text-balance text-3xl font-semibold tracking-tight">
              Начните с выбора фестиваля
            </h2>
            <p className="text-muted-foreground">
              Откройте каталог, сравните условия и переходите к подаче заявки.
            </p>
            <div className="flex flex-wrap items-center justify-center gap-3 pt-1">
              <Button asChild size="lg">
                <Link to={primaryCta}>
                  Перейти к фестивалям
                  <ArrowRight className="size-4" aria-hidden="true" />
                </Link>
              </Button>
              <Button asChild size="lg" variant="outline">
                <Link to={isAuthenticated ? ROUTES.cabinet : ROUTES.register}>
                  {isAuthenticated ? "Открыть кабинет" : "Создать аккаунт"}
                </Link>
              </Button>
            </div>
          </div>
        </section>
        </PageContent>
      </PageContainer>
    </>
  );
}
