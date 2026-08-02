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
import { PageContainer, PageContent, PageDescription, PageHeader, PageTitle } from "@/shared/ui";
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
    <PageContainer size="wide">
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
      <PageHeader>
        <PageTitle>Фестивали</PageTitle>
        <PageDescription>
          Каталог творческих фестивалей: изучайте условия и подавайте заявку после входа.
        </PageDescription>
      </PageHeader>
      <PageContent>
        <FestivalCatalog detailBasePath={ROUTES.competitions} />
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
  return `«${festival.title}» — творческий фестиваль сезона ${festival.season}${where}. Номинации, сроки регистрации, стоимость участия и подача заявки онлайн.`;
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
    <PageContainer size="wide">
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
