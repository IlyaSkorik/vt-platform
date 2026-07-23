import { Link, useParams } from "react-router";
import { useDiplomaTemplate, useTemplateLayout } from "@/features/diplomas";
import { ROUTES } from "@/shared/config";
import { Button, EmptyState, PageContainer, Skeleton } from "@/shared/ui";
import { TemplateConstructorLayout } from "@/widgets/diplomas-template-constructor";

const TEMPLATES_PATH = `${ROUTES.staffDiplomas}?section=templates`;

export function StaffDiplomaTemplateConstructorPage(): React.JSX.Element {
  const { templateId } = useParams<{ templateId: string }>();
  const { template, isLoading, isError, refetch } = useDiplomaTemplate(templateId);
  // Restore the saved layout before mounting the editor (Template → GET Fields → Overlay).
  const layoutQuery = useTemplateLayout(templateId);

  if (isLoading || layoutQuery.isLoading) {
    return (
      <PageContainer size="full">
        <div role="status" aria-label="Загрузка конструктора" className="space-y-4">
          <Skeleton className="h-16 w-full" />
          <div className="grid gap-4 lg:grid-cols-[16rem_1fr_18rem]">
            <Skeleton className="h-96 w-full" />
            <Skeleton className="h-96 w-full" />
            <Skeleton className="h-96 w-full" />
          </div>
        </div>
      </PageContainer>
    );
  }

  if (isError || !template || layoutQuery.isError || !layoutQuery.data) {
    return (
      <PageContainer size="narrow">
        <EmptyState
          title="Шаблон не найден"
          description="Шаблон мог быть удалён, либо у вас нет доступа."
          action={
            <div className="flex flex-wrap gap-2">
              {isError ? <Button onClick={refetch}>Повторить</Button> : null}
              {layoutQuery.isError ? (
                <Button onClick={() => void layoutQuery.refetch()}>Повторить</Button>
              ) : null}
              <Button asChild variant="outline">
                <Link to={TEMPLATES_PATH}>К шаблонам</Link>
              </Button>
            </div>
          }
        />
      </PageContainer>
    );
  }

  return (
    <PageContainer size="full" className="gap-0">
      <TemplateConstructorLayout
        key={template.id}
        template={template}
        initialFields={layoutQuery.data.fields}
      />
    </PageContainer>
  );
}
