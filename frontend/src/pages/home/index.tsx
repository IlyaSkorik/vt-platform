import { useAuth } from "@/app/providers";
import { type Festival, selectUpcoming, usePublicFestivals } from "@/features/festival-catalog";
import { APP_NAME, ROUTES } from "@/shared/config";
import { festivalPath } from "@/shared/lib";
import { absoluteUrl, JsonLd, organizationSchema, useSeo, webSiteSchema } from "@/shared/seo";
import { PageContainer } from "@/shared/ui";
import { HomeHero, HomeOrganizersCta, HomeUpcomingFestivals } from "@/widgets/home-landing";

/** How many festivals the carousel holds before the reader is sent to the catalog. */
const CAROUSEL_LIMIT = 9;

/** The number the «Для организаторов» panel dials. */
const CONTACT_HREF = "tel:+375257506371";

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

  // `selectUpcoming` is the catalog's own shortlist rule — open or announced,
  // soonest competition date first. Reused rather than re-filtered here so the
  // landing and the catalog cannot disagree about what "ближайшие" means.
  const upcoming = selectUpcoming(festivalsQuery.data ?? [], null, CAROUSEL_LIMIT);

  // Route knowledge stays on the page: the landing widget is given finished
  // hrefs, so it never has to know that a festival may or may not have a slug.
  const hrefFor = (festival: Festival): string => festivalPath(festival, ROUTES.competitions);

  return (
    <>
      <JsonLd id="organization" data={organizationSchema()} />
      <JsonLd id="website" data={webSiteSchema()} />

      <HomeHero
        catalogPath={ROUTES.competitions}
        authPath={isAuthenticated ? ROUTES.cabinet : ROUTES.login}
      />

      {/* The public layout does not pad its outlet the way the staff and cabinet
          shells do — the hero above is deliberately full-bleed — so the page
          carries its own gutters from here down. */}
      {/* 32px of side gutter on the phone as well, not the usual 16: the frame
          insets the organisers' panel 33px from each edge of a 375px screen, and
          at 16 it read noticeably wider than drawn. The top gutter is the 30px
          between the band's bottom edge and «Ближайшие фестивали»; `gap-14` is
          the 56px the frame leaves between «Все фестивали» and the organisers'
          panel, against 64 on the desktop.

          The bottom gutter is the gap the frame measures between the organisers'
          panel and the footer — 52px on the phone, 105 on the desktop — rather
          than a symmetrical page padding.
          It is the page's own spacing because the footer belongs to the layout
          and knows nothing about which page it is closing. */}
      <PageContainer
        size="wide"
        className="max-w-336 gap-14 px-8 pt-8 pb-[52px] md:gap-16 md:pt-16 md:pb-[105px]"
      >
        <HomeUpcomingFestivals
          festivals={upcoming}
          isPending={festivalsQuery.isPending}
          allFestivalsPath={ROUTES.competitions}
          hrefFor={hrefFor}
        />
        <HomeOrganizersCta contactHref={CONTACT_HREF} />
      </PageContainer>
    </>
  );
}
