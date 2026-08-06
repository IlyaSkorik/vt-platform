import { CalendarDays, FileCheck2, MapPin, Sparkles } from "lucide-react";
import { Link } from "react-router";
import { useAuth } from "@/app/providers";
import {
  catalogStatusConfig,
  type Festival,
  formatDate,
  formatPeriod,
  parseApiDate,
  participationModeLabel,
  resolveMediaUrl,
  usePublicFestivals,
} from "@/features/festival-catalog";
import { APP_NAME, ROUTES } from "@/shared/config";
import { festivalPath } from "@/shared/lib";
import { absoluteUrl, JsonLd, organizationSchema, useSeo, webSiteSchema } from "@/shared/seo";
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

function firstModeLabel(festival: Festival): string {
  const mode = festival.modes[0];
  return mode ? participationModeLabel(mode) : "Формат уточняется";
}

function isUpcoming(festival: Festival, now: Date): boolean {
  const start = parseApiDate(festival.competitionStart);
  return start != null && start.getTime() > now.getTime();
}

export function HomePage(): React.JSX.Element {
  // The home page is the one that competes on the brand name itself, so it wears
  // the site name as its whole title rather than "Главная — Взлёт талантов": the
  // word "Главная" is dead weight in a result list.
  useSeo({
    title: `${APP_NAME} — фестивали и конкурсы детского творчества`,
    standaloneTitle: true,
    description:
      "Афиша детских творческих фестивалей и конкурсов: условия участия, номинации, сроки подачи заявок и результаты. Подайте заявку онлайн на платформе «Взлёт талантов».",
    image: absoluteUrl("/home-hero-bg.png"),
    imageAlt: "Юные участники творческого фестиваля на сцене",
    canonicalPath: "/",
  });

  const { isAuthenticated } = useAuth();
  const festivalsQuery = usePublicFestivals();
  const festivals = festivalsQuery.data ?? [];
  const now = new Date();

  const activeFestivals = festivals
    .filter((festival) => festival.status === "REGISTRATION_OPEN" || festival.status === "RUNNING")
    .slice(0, 6);
  const upcomingFestivals = festivals.filter((festival) => isUpcoming(festival, now)).slice(0, 5);
  const latestResults = festivals
    .filter((festival) => festival.status === "COMPLETED" || festival.status === "RUNNING")
    .slice()
    .sort(
      (a, b) =>
        (parseApiDate(b.updatedAt)?.getTime() ?? 0) - (parseApiDate(a.updatedAt)?.getTime() ?? 0),
    )
    .slice(0, 5);
  const authPath = isAuthenticated ? ROUTES.cabinet : ROUTES.login;

  return (
    <>
      <JsonLd id="organization" data={organizationSchema()} />
      <JsonLd id="website" data={webSiteSchema()} />
      {/* No bottom border: the glow below is the separator now, and a hairline on top of
          it made the hand-off into the page read as a cut rather than as a fade. */}
      <section className="relative min-h-screen w-full overflow-hidden">
        <div
          aria-hidden="true"
          className="absolute inset-0 bg-cover bg-center bg-no-repeat"
          style={{ backgroundImage: "url('/home-hero-bg.png')" }}
        />
        {/* Darkens the photograph so the copy reads against it. Theme-invariant:
            in the light theme this used to tint the image with the page's white
            and left the hero glaring. */}
        <div
          aria-hidden="true"
          className="absolute inset-0 bg-gradient-to-b from-scrim-media/65 via-scrim-media/80 to-scrim-media/90"
        />
        {/* Separate layer for the hand-off: only the bottom quarter blends into
            the page, so the scrim above it stays at full strength. */}
        <div
          aria-hidden="true"
          className="absolute inset-0 bg-gradient-to-b from-transparent from-75% to-background"
        />
        {/* The brand glow above the bottom edge. Above the hand-off layer on purpose:
            below it, the fade to `--background` washed it out to nothing.

            `glow-on-media` rather than `primary`: the light theme's brand blue is deep
            enough to read as a shadow on a white page rather than as light. The token
            carries the per-theme adjustment so this stays one gesture — see the note in
            vt-light.css.

            Transparent at *both* ends, peaking mid-band: a gradient that peaked at the
            edge put its brightest pixel exactly where the hero stops, drawing the seam it
            was meant to dissolve. */}
        <div
          aria-hidden="true"
          className="pointer-events-none absolute inset-x-0 bottom-0 h-64 bg-gradient-to-t from-transparent via-glow-on-media/40 to-transparent md:h-80"
        />
        <div className="relative mx-auto flex min-h-screen w-full max-w-336 items-center px-4 md:px-8">
          <div className="space-y-5 text-on-scrim">
            <Badge variant="outline" size="sm" icon={<Sparkles className="size-3.5" />}>
              Платформа творческих мероприятий
            </Badge>
            <div className="max-w-4xl space-y-4">
              <h1 className="text-balance text-4xl font-bold tracking-tight sm:text-5xl md:text-6xl">
                Взлёт талантов
              </h1>
              <p className="max-w-2xl text-pretty text-base text-on-scrim-muted sm:text-lg">
                Здесь проходят детские творческие фестивали: находите мероприятия, подавайте заявки,
                смотрите результаты и скачивайте дипломы.
              </p>
            </div>
            <div className="flex flex-wrap items-center gap-2.5 pt-1">
              <Button asChild size="lg" className="min-w-[13.5rem]">
                <a href="#active-events">Найти мероприятие</a>
              </Button>
              <Button asChild size="lg" variant="outline" className="min-w-[9rem]">
                <Link to={authPath}>{isAuthenticated ? "Личный кабинет" : "Войти"}</Link>
              </Button>
            </div>
          </div>
        </div>
      </section>

      {/* The public layout does not pad its outlet the way the staff and cabinet
          shells do — the hero above is deliberately full-bleed — so pages under it
          carry their own gutters. Without these the copy ran into both edges on a
          phone. */}
      <PageContainer size="wide" className="px-4 md:px-8">
        <PageContent className="space-y-16 py-10 md:py-14">
          <section id="active-events" className="scroll-mt-24 space-y-5">
            <div className="flex flex-wrap items-end justify-between gap-3">
              <div className="space-y-1">
                <h2 className="text-3xl font-semibold tracking-tight">Активные мероприятия</h2>
                <p className="text-muted-foreground">Главные события, которые идут прямо сейчас.</p>
              </div>
              <Button asChild variant="outline" size="sm">
                <Link to={ROUTES.competitions}>Все мероприятия</Link>
              </Button>
            </div>
            {festivalsQuery.isPending ? (
              <LoadingState label="Загружаем активные мероприятия…" />
            ) : (
              // `rise-in` on the container, not on each card: the list arrives as one
              // thing once the query resolves, and staggering it would draw attention to
              // the loading rather than away from it.
              <div className="grid animate-rise-in gap-5 md:grid-cols-2 xl:grid-cols-3">
                {activeFestivals.map((festival) => {
                  const status = catalogStatusConfig(festival.status);
                  const detailPath = festivalPath(festival, ROUTES.competitions);
                  return (
                    <Card
                      key={festival.id}
                      // Lifts on hover, because this card *does* lead somewhere. The
                      // non-interactive cards further down deliberately do not — a card
                      // that rises under the cursor and then does nothing is a lie.
                      className="shadow-none transition-[box-shadow,transform] duration-[var(--duration-normal)] ease-standard hover:-translate-y-0.5 hover:shadow-md"
                    >
                      <div className="aspect-[16/9] overflow-hidden rounded-t-xl bg-muted">
                        {resolveMediaUrl(festival.coverImage) ? (
                          <img
                            src={resolveMediaUrl(festival.coverImage) ?? ""}
                            alt={`Афиша мероприятия ${festival.title}`}
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
                        <div className="flex items-start justify-between gap-2">
                          <CardTitle className="line-clamp-2 text-base">{festival.title}</CardTitle>
                          <Badge variant={status.badgeVariant} size="sm">
                            {status.label}
                          </Badge>
                        </div>
                        <CardDescription className="line-clamp-1">
                          {festival.organizer.name}
                        </CardDescription>
                      </CardHeader>
                      <CardContent className="space-y-3">
                        <p className="inline-flex items-center gap-1 text-xs text-muted-foreground">
                          <CalendarDays className="size-3.5" aria-hidden="true" />
                          {formatPeriod(festival.competitionStart, festival.competitionEnd) ??
                            "Даты уточняются"}
                        </p>
                        <p className="inline-flex items-center gap-1 text-xs text-muted-foreground">
                          <MapPin className="size-3.5" aria-hidden="true" />
                          {[festival.city, firstModeLabel(festival)].filter(Boolean).join(" · ")}
                        </p>
                        <p className="line-clamp-2 text-sm text-muted-foreground">
                          {festival.description || "Подробности доступны на странице мероприятия."}
                        </p>
                        <div className="grid gap-2">
                          <Button asChild size="sm" className="w-full">
                            <Link to={detailPath}>Открыть мероприятие</Link>
                          </Button>
                          {status.apply.visible ? (
                            <Button asChild variant="outline" size="sm" className="w-full">
                              <Link to={detailPath}>Подать заявку</Link>
                            </Button>
                          ) : (
                            <Button asChild variant="outline" size="sm" className="w-full">
                              <Link to={detailPath}>Смотреть результаты</Link>
                            </Button>
                          )}
                        </div>
                      </CardContent>
                    </Card>
                  );
                })}
              </div>
            )}
          </section>

          <section className="space-y-5">
            <div className="space-y-1">
              <h2 className="text-3xl font-semibold tracking-tight">
                Что можно сделать на платформе
              </h2>
            </div>
            <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
              <Card className="shadow-none">
                <CardHeader>
                  <CardTitle className="text-base">Найти мероприятие</CardTitle>
                </CardHeader>
                <CardContent className="text-sm text-muted-foreground">
                  Выберите фестиваль по дате, формату и городу.
                </CardContent>
              </Card>
              <Card className="shadow-none">
                <CardHeader>
                  <CardTitle className="text-base">Подать заявку</CardTitle>
                </CardHeader>
                <CardContent className="text-sm text-muted-foreground">
                  Зарегистрируйтесь и отправьте заявку на выбранное мероприятие онлайн.
                </CardContent>
              </Card>
              <Card className="shadow-none">
                <CardHeader>
                  <CardTitle className="text-base">Посмотреть результаты</CardTitle>
                </CardHeader>
                <CardContent className="text-sm text-muted-foreground">
                  Следите за публикацией итогов жанров и протоколов.
                </CardContent>
              </Card>
              <Card className="shadow-none">
                <CardHeader>
                  <CardTitle className="text-base">Скачать диплом</CardTitle>
                </CardHeader>
                <CardContent className="text-sm text-muted-foreground">
                  Получите дипломы и сертификаты после публикации результатов.
                </CardContent>
              </Card>
            </div>
          </section>

          <section className="space-y-5">
            <div className="flex flex-wrap items-end justify-between gap-3">
              <div className="space-y-1">
                <h2 className="text-3xl font-semibold tracking-tight">Ближайшие мероприятия</h2>
                <p className="text-muted-foreground">
                  События, которые стартуют в ближайшее время.
                </p>
              </div>
              <Button asChild variant="outline" size="sm">
                <Link to={ROUTES.competitions}>Весь календарь</Link>
              </Button>
            </div>
            {festivalsQuery.isPending ? (
              <LoadingState label="Загружаем ближайшие мероприятия…" />
            ) : (
              <div className="grid animate-rise-in gap-3 md:grid-cols-2">
                {upcomingFestivals.map((festival) => (
                  <Card key={festival.id} className="shadow-none">
                    <CardContent className="flex items-center justify-between gap-3 pt-5">
                      <div className="min-w-0">
                        <p className="truncate text-sm font-medium">{festival.title}</p>
                        <p className="text-xs text-muted-foreground">
                          {formatPeriod(festival.competitionStart, festival.competitionEnd) ??
                            "Дата уточняется"}{" "}
                          · {firstModeLabel(festival)}
                        </p>
                      </div>
                      <Button asChild variant="outline" size="sm">
                        <Link to={festivalPath(festival, ROUTES.competitions)}>Открыть</Link>
                      </Button>
                    </CardContent>
                  </Card>
                ))}
              </div>
            )}
          </section>

          <section className="space-y-5">
            <div className="space-y-1">
              <h2 className="text-3xl font-semibold tracking-tight">Последние результаты</h2>
              <p className="text-muted-foreground">Недавно опубликованные итоги мероприятий.</p>
            </div>
            {festivalsQuery.isPending ? (
              <LoadingState label="Загружаем последние результаты…" />
            ) : (
              <div className="grid animate-rise-in gap-3 md:grid-cols-2">
                {latestResults.map((festival) => (
                  <Card key={festival.id} className="shadow-none">
                    <CardContent className="flex items-center justify-between gap-3 pt-5">
                      <div className="min-w-0">
                        <p className="truncate text-sm font-medium">{festival.title}</p>
                        <p className="inline-flex items-center gap-1 text-xs text-muted-foreground">
                          <FileCheck2 className="size-3.5" aria-hidden="true" />
                          Опубликовано: {formatDate(festival.updatedAt) ?? "дата уточняется"}
                        </p>
                      </div>
                      <Button asChild variant="outline" size="sm">
                        <Link to={festivalPath(festival, ROUTES.competitions)}>Смотреть</Link>
                      </Button>
                    </CardContent>
                  </Card>
                ))}
              </div>
            )}
          </section>

          <section className="rounded-2xl border border-border bg-card p-8 md:p-10">
            <div className="max-w-3xl space-y-4">
              <h2 className="text-3xl font-semibold tracking-tight">Для организаторов</h2>
              <p className="text-muted-foreground">
                Проводите собственные фестивали? Используйте платформу «Взлёт талантов» для
                автоматизации проведения мероприятий.
              </p>
              <Button asChild size="lg">
                <Link to="tel:+375257506371">Свяжитесь с нами</Link>
              </Button>
            </div>
          </section>
        </PageContent>
      </PageContainer>
    </>
  );
}
