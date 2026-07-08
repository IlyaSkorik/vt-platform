import { Link, useLocation } from "react-router";
import { ROUTES, resolveBreadcrumbs } from "@/shared/config";
import { Button, EmptyPage, PageContainer, PageContent, PageHeader, PageTitle } from "@/shared/ui";

/**
 * Placeholder page for app-shell sections whose feature has not shipped yet.
 *
 * Renders inside the Application Shell so every sidebar link resolves to a
 * coherent screen. The title is derived from the navigation model, so no
 * per-section wiring is needed. Replaced by the real page when its feature
 * lands (bootstrap scope: no business content).
 */
export function PlaceholderPage(): React.JSX.Element {
  const { pathname } = useLocation();
  const trail = resolveBreadcrumbs(pathname);
  const title = trail.at(-1)?.label ?? "Раздел";

  return (
    <PageContainer>
      <PageHeader>
        <PageTitle>{title}</PageTitle>
      </PageHeader>
      <PageContent>
        <EmptyPage
          title="Раздел в разработке"
          description="Этот раздел появится в одном из ближайших релизов платформы."
          action={
            <Button asChild variant="outline">
              <Link to={ROUTES.dashboard}>Вернуться на панель</Link>
            </Button>
          }
        />
      </PageContent>
    </PageContainer>
  );
}
