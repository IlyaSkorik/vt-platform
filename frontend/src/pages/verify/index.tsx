import { useParams } from "react-router";
import { PageContainer, PageContent, PageDescription, PageHeader, PageTitle } from "@/shared/ui";
import { DiplomaVerification } from "@/widgets/diploma-verification";

/**
 * `/verify/:verificationToken` — the public page a printed diploma's QR points at.
 *
 * Unauthenticated by design: whoever holds the paper can check it, with no
 * account. The token in the URL is the only input.
 */
export function DiplomaVerifyPage(): React.JSX.Element {
  const { verificationToken } = useParams();
  return (
    <PageContainer size="narrow" className="px-4 py-8 md:px-8 md:py-12">
      <PageHeader>
        <PageTitle>Проверка диплома</PageTitle>
        <PageDescription>
          Подлинность документа подтверждается по его QR-коду. Ниже — данные, зафиксированные при
          выдаче диплома.
        </PageDescription>
      </PageHeader>
      <PageContent>
        <DiplomaVerification verificationToken={verificationToken} />
      </PageContent>
    </PageContainer>
  );
}
