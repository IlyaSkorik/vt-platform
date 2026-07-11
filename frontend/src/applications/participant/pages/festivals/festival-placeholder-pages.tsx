import { ArrowLeft, ClipboardList, LayoutTemplate } from "lucide-react";
import { Link, useParams } from "react-router";
import { ROUTES } from "@/shared/config";
import { Button, EmptyPage, PageContainer, PageContent } from "@/shared/ui";

/**
 * Prepared navigation targets for the catalog's "More details" and "Apply"
 * actions. The Competition Landing Page and the Registration Wizard are
 * implemented later; these keep the routes live (no 404) and carry the selected
 * `:festivalId` through so wiring them up later is a drop-in replacement.
 */

function BackToCatalog(): React.JSX.Element {
  return (
    <Button asChild variant="outline" leftIcon={<ArrowLeft aria-hidden="true" />}>
      <Link to={ROUTES.cabinetCompetitions}>К каталогу</Link>
    </Button>
  );
}

export function FestivalLandingPlaceholderPage(): React.JSX.Element {
  useParams();
  return (
    <PageContainer>
      <PageContent>
        <EmptyPage
          icon={<LayoutTemplate aria-hidden="true" />}
          title="Страница фестиваля скоро появится"
          description="Здесь будет публичная страница фестиваля с программой, условиями и составом жюри."
          action={<BackToCatalog />}
        />
      </PageContent>
    </PageContainer>
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
