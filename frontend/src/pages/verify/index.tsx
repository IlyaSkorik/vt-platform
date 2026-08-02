import { useParams } from "react-router";
import { APP_NAME } from "@/shared/config";
import { useSeo } from "@/shared/seo";
import { PageContainer } from "@/shared/ui";
import { DiplomaVerification } from "@/widgets/diploma-verification";

/**
 * `/verify/:verificationToken` — the official register entry a printed diploma's
 * QR code opens.
 *
 * Unauthenticated by design: whoever holds the paper can check it, with no
 * account. The token in the URL is the only input.
 *
 * The header names the institution before the verdict, because that is what makes
 * the verdict worth anything: the eyebrow establishes *which* register answered,
 * the `h1` names the service, and each result card carries its own `h2`.
 */
export function DiplomaVerifyPage(): React.JSX.Element {
  const { verificationToken } = useParams();
  // Closed to crawlers: the whole address is a token, and what it opens is a
  // named child's award. Public in the sense that anyone holding the paper can
  // check it — not in the sense that it belongs in a search index.
  useSeo({ title: "Проверка подлинности диплома", robots: "noindex" });

  return (
    <PageContainer size="narrow" className="gap-8 px-4 py-10 sm:px-6 md:py-14">
      <header className="space-y-2 text-center">
        <p className="font-medium text-muted-foreground text-xs uppercase tracking-[0.18em]">
          Официальный реестр дипломов
        </p>
        <h1 className="font-bold text-3xl text-foreground tracking-tight sm:text-4xl">
          Проверка подлинности
        </h1>
        {/* Valid whatever the register answers — the "frozen at issue" promise
            belongs with the facts it describes, not in a header that also sits
            above a not-found result. */}
        <p className="mx-auto max-w-lg text-balance text-muted-foreground text-sm">
          Сервис проверки документов платформы «{APP_NAME}».
        </p>
      </header>
      <DiplomaVerification verificationToken={verificationToken} />
    </PageContainer>
  );
}
