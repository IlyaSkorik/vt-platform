import { PageContainer, PageContent, PageDescription, PageHeader, PageTitle } from "@/shared/ui";
import { FestivalCatalog } from "@/widgets/festival-catalog";

/**
 * Participant Portal entry point: the public festival catalog.
 *
 * Mounted at `/cabinet/competitions`. Thin by design — the page owns the
 * heading and container; the {@link FestivalCatalog} widget owns data,
 * search/filter/sort and every UI state.
 */
export function FestivalCatalogPage(): React.JSX.Element {
  return (
    <PageContainer size="wide">
      <PageHeader>
        <PageTitle>Фестивали</PageTitle>
        <PageDescription>
          Каталог творческих фестивалей: найдите событие, изучите условия и подайте заявку.
        </PageDescription>
      </PageHeader>
      <PageContent>
        <FestivalCatalog />
      </PageContent>
    </PageContainer>
  );
}
