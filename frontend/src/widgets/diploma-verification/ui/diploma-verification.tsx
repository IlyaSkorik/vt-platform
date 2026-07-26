import { useVerifyDiploma } from "@/features/diploma-verification";
import { ConfirmationPanel } from "./confirmation-panel";
import { OfficialPdfDownload } from "./official-pdf-download";
import { RegistryEntry } from "./registry-entry";
import { VerificationNote } from "./verification-note";
import {
  VerificationNotFound,
  VerificationSkeleton,
  VerificationUnavailable,
} from "./verification-states";

interface DiplomaVerificationProps {
  /** The token from the printed QR link (`/verify/{verificationToken}`). */
  verificationToken: string | undefined;
}

/**
 * The public register entry for one diploma.
 *
 * Everything shown is the diploma's own frozen snapshot, read through a single
 * unauthenticated request — so the page states exactly what the paper states and
 * cannot drift from it. Reads top to bottom as an official record does: the sealed
 * verdict, the recorded facts, the document itself, then the provenance of the
 * check.
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
      <VerificationUnavailable onRetry={() => void query.refetch()} retrying={query.isFetching} />
    );
  }

  const diploma = query.data;
  const officialPdfUrl = diploma.officialPdfUrl?.trim();
  // When the register actually answered. Taken from the query rather than a fresh
  // `new Date()` so the stamp records the check, not the latest re-render.
  const checkedAt = new Date(query.dataUpdatedAt || Date.now());

  return (
    <div className="space-y-6">
      <ConfirmationPanel />
      <RegistryEntry diploma={diploma} />
      {officialPdfUrl ? (
        <div className="flex justify-center sm:justify-start">
          <OfficialPdfDownload reference={officialPdfUrl} />
        </div>
      ) : null}
      <VerificationNote checkedAt={checkedAt} />
    </div>
  );
}
