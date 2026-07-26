import { CheckCircle2, Download } from "lucide-react";
import type { VerifiedDiploma } from "@/features/diploma-verification";
import { diplomaFactRows, useVerifyDiploma } from "@/features/diploma-verification";
import { resolveMediaUrl } from "@/shared/lib";
import { Button, Card, CardContent } from "@/shared/ui";
import {
  VerificationError,
  VerificationNotFound,
  VerificationSkeleton,
} from "./verification-states";

/** The confirmation banner — the first thing a visitor scanning a QR should read. */
function VerifiedBanner(): React.JSX.Element {
  return (
    <p className="flex items-center gap-2 font-semibold text-success text-lg">
      <CheckCircle2 className="size-6 shrink-0" aria-hidden="true" />
      Диплом подтверждён
    </p>
  );
}

/**
 * The official PDF download.
 *
 * Rendered only once `officialPdfUrl` exists — before the ceremony there is no
 * official document to hand out, and a dead button would misrepresent that. The
 * stored `/media/…` reference is resolved against the API origin.
 */
function OfficialPdfDownload({ reference }: { reference: string }): React.JSX.Element | null {
  const href = resolveMediaUrl(reference);
  if (href == null) {
    return null;
  }
  return (
    <Button asChild variant="outline" className="w-full sm:w-auto">
      <a href={href} target="_blank" rel="noopener noreferrer">
        <Download className="size-4" aria-hidden="true" />
        Скачать официальный диплом
      </a>
    </Button>
  );
}

function DiplomaFacts({ diploma }: { diploma: VerifiedDiploma }): React.JSX.Element {
  return (
    <dl className="divide-y divide-border">
      {diplomaFactRows(diploma).map((row) => (
        <div key={row.key} className="grid gap-1 py-3 sm:grid-cols-[10rem_1fr] sm:gap-4">
          <dt className="text-muted-foreground text-sm">{row.label}</dt>
          <dd
            className={
              row.pending
                ? "text-muted-foreground text-sm italic"
                : "font-medium text-foreground text-sm"
            }
          >
            {row.value}
          </dd>
        </div>
      ))}
    </dl>
  );
}

interface DiplomaVerificationProps {
  /** The token from the printed QR link (`/verify/{verificationToken}`). */
  verificationToken: string | undefined;
}

/**
 * The public diploma authenticity page.
 *
 * Everything shown is the diploma's own frozen snapshot, read through one
 * unauthenticated request — so the page states exactly what the paper states and
 * cannot drift from it. Two facts are deliberately conditional: an unawarded
 * degree reads as "результаты ещё не опубликованы" (a pending process, not
 * missing data), and the download button exists only once the official PDF does.
 */
export function DiplomaVerification({
  verificationToken,
}: DiplomaVerificationProps): React.JSX.Element {
  const query = useVerifyDiploma(verificationToken);

  if (verificationToken == null || verificationToken.trim() === "") {
    return <VerificationNotFound />;
  }
  if (query.isPending) {
    return <VerificationSkeleton />;
  }
  if (query.isError) {
    return query.error.status === 404 ? (
      <VerificationNotFound />
    ) : (
      <VerificationError onRetry={() => void query.refetch()} retrying={query.isFetching} />
    );
  }

  const diploma = query.data;
  const officialPdfUrl = diploma.officialPdfUrl?.trim();

  return (
    <Card>
      <CardContent className="space-y-5 py-6">
        <VerifiedBanner />
        <DiplomaFacts diploma={diploma} />
        {officialPdfUrl ? <OfficialPdfDownload reference={officialPdfUrl} /> : null}
      </CardContent>
    </Card>
  );
}
