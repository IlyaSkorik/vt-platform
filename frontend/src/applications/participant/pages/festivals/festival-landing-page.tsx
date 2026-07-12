import { useParams } from "react-router";
import { PageContainer, PageContent } from "@/shared/ui";
import { FestivalLanding } from "@/widgets/festival-landing";

/**
 * Public Competition Landing Page.
 *
 * Mounted at `/cabinet/competitions/:festivalId`, reached from the Festival
 * Catalog. Thin by design — the page owns the container; the
 * {@link FestivalLanding} widget owns data, block rendering and every UI state.
 */
export function FestivalLandingPage(): React.JSX.Element {
  const { festivalId } = useParams();
  return (
    <PageContainer size="wide">
      <PageContent>
        <FestivalLanding festivalId={festivalId} />
      </PageContent>
    </PageContainer>
  );
}
