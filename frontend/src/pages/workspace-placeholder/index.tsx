import { PageContainer, PageContent, PageDescription, PageHeader, PageTitle } from "@/shared/ui";

type WorkspacePlaceholderPageProps = {
  title: string;
  description: string;
};

export function WorkspacePlaceholderPage({
  title,
  description,
}: WorkspacePlaceholderPageProps): React.JSX.Element {
  return (
    <PageContainer>
      <PageHeader>
        <PageTitle>{title}</PageTitle>
        <PageDescription>{description}</PageDescription>
      </PageHeader>
      <PageContent>
        <div className="rounded-md border border-dashed border-slate-300 bg-white p-6 text-sm text-slate-600">
          Раздел готов к подключению бизнес-сценариев.
        </div>
      </PageContent>
    </PageContainer>
  );
}
