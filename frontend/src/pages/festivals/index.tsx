import { useParams } from "react-router";
import { usePublicFestivals } from "@/features/festival-catalog";
import { usePublicFestival } from "@/features/festival-landing";
import { ROUTES } from "@/shared/config";
import { resolveMediaUrl } from "@/shared/lib";
import {
  breadcrumbSchema,
  festivalEventSchema,
  festivalListSchema,
  JsonLd,
  useSeo,
} from "@/shared/seo";
import { PageContainer, PageContent } from "@/shared/ui";
import { FestivalCatalog } from "@/widgets/festival-catalog";
import { FestivalLanding } from "@/widgets/festival-landing";

export function PublicFestivalCatalogPage(): React.JSX.Element {
  useSeo({
    title: "Фестивали и конкурсы детского творчества",
    description:
      "Каталог открытых творческих фестивалей и конкурсов: номинации, возрастные категории, сроки регистрации и стоимость участия. Заявка подаётся онлайн.",
  });

  // The same cached read the catalog widget performs, so listing the festivals
  // for search costs no extra request. An empty list yields an empty ItemList,
  // which is valid and honest — better than claiming a catalog that isn't there.
  const festivals = usePublicFestivals().data ?? [];

  return (
    // 27px of air under the header before the filters panel and the title
    // beside it, as the frame measures it. `PageContainer` has no vertical
    // padding of its own, so without this the catalogue began flush against the
    // bar.
    // `max-w-336`, matching the public header's own container. `size="wide"`
    // alone is `max-w-7xl` — 64px narrower — and the page then sat visibly inset
    // from the bar above it, which reads as a misalignment rather than as a
    // margin. 36px of air under the bar before the search band on a phone and 27
    // before the filters panel on a desktop, and 32 under
    // the pagination before the footer — 55 on a phone, where the strip is the
    // last thing on a long scroll and needs the room to stop reading as part of
    // the footer — as the frame measures them;
    // `PageContainer` carries no vertical padding of its own. 14px of side gutter
    // on a phone, which is where the frame starts the search and filter bands —
    // the cards sit further in again and carry that inset themselves.
    <PageContainer
      size="wide"
      className="max-w-336 px-3.5 pt-9 pb-[55px] md:px-8 md:pt-[27px] md:pb-8"
    >
      <JsonLd
        id="festival-list"
        data={festivalListSchema(festivals, { basePath: ROUTES.competitions })}
      />
      <JsonLd
        id="breadcrumbs"
        data={breadcrumbSchema([
          { name: "Главная", path: ROUTES.home },
          { name: "Фестивали", path: ROUTES.competitions },
        ])}
      />
      {/* No `PageHeader` here. The frame sets the title inside the results
          column, level with the top of the filters panel — across the page it
          would read as a heading for the filters as much as for the grid. The
          widget renders it, so it stays in the column it titles. */}
      <PageContent>
        <FestivalCatalog detailBasePath={ROUTES.competitions} title="Активные фестивали" />
      </PageContent>
    </PageContainer>
  );
}

/**
 * A one-sentence summary for search, from whatever the organizer filled in.
 *
 * Falls back to the facts the projection always carries rather than to a generic
 * line, because a description repeated across every festival is the same as no
 * description: search collapses duplicates and picks its own snippet.
 */
function landingDescription(festival: {
  title: string;
  season: string;
  description: string | null;
  city: string | null;
}): string {
  const own = festival.description?.trim();
  if (own) return own.length > 300 ? `${own.slice(0, 297).trimEnd()}…` : own;
  const where = festival.city ? ` в городе ${festival.city}` : "";
  return `«${festival.title}» — творческий фестиваль сезона ${festival.season}${where}. Жанры, сроки регистрации, стоимость участия и подача заявки онлайн.`;
}

export function PublicFestivalLandingPage(): React.JSX.Element {
  const { festivalId } = useParams();
  // The landing widget reads the same query; React Query serves both from one
  // cache entry, so owning the page's meta here costs a hook, not a request.
  // SEO deliberately lives in the page and not in the widget: the same widget
  // renders inside the cabinet, where none of this belongs.
  const festival = usePublicFestival(festivalId).data;
  const path = `${ROUTES.competitions}/${festivalId ?? ""}`;

  useSeo(
    festival
      ? {
          title: `${festival.title} — ${festival.season}`,
          description: landingDescription(festival),
          image: resolveMediaUrl(festival.coverImage) ?? undefined,
          imageAlt: `Афиша фестиваля «${festival.title}»`,
          type: "article",
          canonicalPath: path,
        }
      : // Until the read lands — and for a festival that turns out not to exist —
        // the page must not advertise itself under a title it cannot back up.
        { title: "Фестиваль", robots: "noindex" },
  );

  return (
    // Same container as the catalogue and the header — see the note there, with
    // one difference: 30px of air under the bar before the poster, at every
    // width. The catalogue opens with a filters panel and a search band, which
    // are chrome and can sit closer; this page opens with artwork, and the
    // frame gives it the same margin on a phone as on a desktop.
    <PageContainer size="wide" className="max-w-336 px-3.5 pt-[30px] pb-[55px] md:px-8 md:pb-8">
      {festival ? (
        <>
          <JsonLd id="festival-event" data={festivalEventSchema(festival, { path })} />
          <JsonLd
            id="breadcrumbs"
            data={breadcrumbSchema([
              { name: "Главная", path: ROUTES.home },
              { name: "Фестивали", path: ROUTES.competitions },
              { name: festival.title, path },
            ])}
          />
        </>
      ) : null}
      <PageContent>
        <FestivalLanding festivalId={festivalId} catalogPath={ROUTES.competitions} />
      </PageContent>
    </PageContainer>
  );
}
