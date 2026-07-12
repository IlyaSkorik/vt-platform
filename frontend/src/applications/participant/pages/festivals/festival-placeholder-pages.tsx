import { ArrowLeft, ClipboardList } from "lucide-react";
import { Link, useParams } from "react-router";
import { ROUTES } from "@/shared/config";
import { Button, EmptyPage, PageContainer, PageContent } from "@/shared/ui";

/**
 * Prepared navigation target for the catalog/landing "Apply" action. The
 * Registration Wizard is implemented later; this keeps the route live (no 404)
 * and carries the selected `:festivalId` through so wiring it up later is a
 * drop-in replacement. (The Competition Landing Page itself has shipped — see
 * {@link FestivalLandingPage}.)
 */

function BackToCatalog(): React.JSX.Element {
  return (
    <Button asChild variant="outline" leftIcon={<ArrowLeft aria-hidden="true" />}>
      <Link to={ROUTES.cabinetCompetitions}>К каталогу</Link>
    </Button>
  );
}

export function FestivalApplyPlaceholderPage(): React.JSX.Element {
  useParams();
  return (
    <PageContainer>
      <PageContent>
        <EmptyPage
          icon={<ClipboardList aria-hidden="true" />}
          title="Подача заявки скоро откроется"
          description="Здесь появится мастер регистрации: выбор номинации, участников и оплата."
          action={<BackToCatalog />}
        />
      </PageContent>
    </PageContainer>
  );
}
