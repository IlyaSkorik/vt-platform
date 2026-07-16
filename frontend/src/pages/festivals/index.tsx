import { useParams } from "react-router";
import { ROUTES } from "@/shared/config";
import { PageContainer, PageContent, PageDescription, PageHeader, PageTitle } from "@/shared/ui";
import { FestivalCatalog } from "@/widgets/festival-catalog";
import { FestivalLanding } from "@/widgets/festival-landing";

export function PublicFestivalCatalogPage(): React.JSX.Element {
  return (
    <PageContainer size="wide">
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

export function PublicFestivalLandingPage(): React.JSX.Element {
  const { festivalId } = useParams();
  return (
    <PageContainer size="wide">
      <PageContent>
        <FestivalLanding festivalId={festivalId} catalogPath={ROUTES.competitions} />
      </PageContent>
    </PageContainer>
  );
}
