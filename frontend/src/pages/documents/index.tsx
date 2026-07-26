import { PageContainer, PageContent, PageDescription, PageHeader, PageTitle } from "@/shared/ui";
import { MyDocuments } from "@/widgets/my-documents";

/**
 * `/cabinet/documents` — "Мои документы".
 *
 * Everything the platform has issued to this participant, in one place. Read-only
 * by design: documents appear on their own as organizers generate them, so there is
 * nothing here to submit or request.
 */
export function MyDocumentsPage(): React.JSX.Element {
  return (
    <PageContainer>
      <PageHeader>
        <PageTitle>Мои документы</PageTitle>
        <PageDescription>
          Дипломы и благодарности, выданные по вашим заявкам. Появляются автоматически — запрашивать
          их не нужно.
        </PageDescription>
      </PageHeader>
      <PageContent>
        <MyDocuments />
      </PageContent>
    </PageContainer>
  );
}
