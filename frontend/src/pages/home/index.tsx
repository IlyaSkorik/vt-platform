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
        {/* One artwork per theme, swapped by the `.dark` class rather than by state:
            the theme flips in CSS, and a background chosen in JS would lag it by a
            render. Both files live in `public/`, so the paths are absolute and Vite
            leaves them alone. */}
        <div
          aria-hidden="true"
          className="absolute inset-0 bg-[url('/home-hero-bg.png')] bg-cover bg-center bg-no-repeat dark:bg-[url('/home-hero-bg-dark.png')]"
        />
        {/* Dark theme only, and lighter than it was. The scrim used to be
            theme-invariant, on the rule that a photograph needs the same darkening
            whatever the UI around it does — true while both themes shared one image.
            They no longer do: the light artwork is a near-white illustration that a
            scrim only dirties, and the copy over it is dark rather than light, so
            there is nothing to darken *for*. */}
        <div
          aria-hidden="true"
          className="absolute inset-0 hidden bg-gradient-to-b from-scrim-media/25 via-scrim-media/40 to-scrim-media/60 dark:block"
        />
        {/* The hand-off into the page, kept on its own layer so it does not eat into
            the artwork above it. Short on purpose — the brand glow below is what
            should be visible at the bottom edge, not a long slide into the page
            background. */}
        <div
          aria-hidden="true"
          className="absolute inset-0 bg-gradient-to-b from-transparent from-90% to-background"
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
          className="pointer-events-none absolute inset-x-0 bottom-0 h-72 bg-gradient-to-t from-transparent via-glow-on-media/25 to-transparent md:h-88 dark:via-glow-on-media/50"
        />
        {/* The block sits above the optical centre: a hero that is centred by
            arithmetic reads as sitting low, because the bottom of the frame is glow
            rather than content. */}
        <div className="relative mx-auto flex min-h-screen w-full max-w-336 items-center px-4 pb-20 md:px-8 md:pb-28">
          {/* Dark copy on the light artwork, light copy on the dark one. `on-scrim`
              alone was right while every hero sat under a scrim; on a near-white
              illustration it prints white on white. */}
          <div className="space-y-5 text-foreground dark:text-on-scrim">
            {/* Not the `outline` variant: its page-coloured fill printed a solid chip
                onto the artwork. Glass instead — the image stays visible through it,
                and the brand glow rings it to the same colour as the band at the
                bottom of the hero. Tinted with the copy colour, so it darkens the
                light theme and lightens the dark one. */}
            <Badge
              variant="outline"
              size="md"
              icon={<Sparkles />}
              className="h-8 gap-2 border-current/20 bg-current/8 px-3.5 text-[0.8125rem] tracking-wide shadow-[0_0_28px_-8px_var(--color-glow-on-media)] backdrop-blur-md [&_svg]:size-4 [&_svg]:text-glow-on-media"
            >
              Платформа творческих мероприятий
            </Badge>
            {/* Carries its own contrast so the scrim does not have to: a soft halo
                behind the glyphs holds the copy legible over a busy patch of the
                artwork without veiling the whole frame. `--background` rather than
                `--scrim-media` because the halo has to oppose the copy — white behind
                dark text in the light theme, near-black behind light text in the dark
                one — which is exactly how that token already moves. */}
            <div className="max-w-4xl space-y-4 [text-shadow:0_2px_18px_var(--background)]">
              <h1 className="text-balance text-4xl font-bold tracking-tight sm:text-5xl md:text-6xl">
                Взлёт талантов
              </h1>
              <p className="max-w-2xl text-pretty text-base text-muted-foreground sm:text-lg dark:text-on-scrim-muted">
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
