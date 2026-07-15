import { Download, FileText } from "lucide-react";
import { resolveMediaUrl } from "@/features/festival-catalog";
import type { FestivalDocument } from "@/features/festival-landing";
import { Button } from "@/shared/ui";
import { LandingSection } from "../landing-section";

/** Human labels for the document categories exposed publicly. */
const CATEGORY_LABELS: Record<string, string> = {
  REGULATION: "Положение",
  PROGRAM: "Программа",
  SCHEDULE: "Расписание",
  REQUISITES: "Реквизиты",
  MEMO: "Памятка",
  ACCOMMODATION: "Проживание",
  OTHER: "Документ",
};

function DocumentRow({ document }: { document: FestivalDocument }): React.JSX.Element {
  const href = resolveMediaUrl(document.fileReference);
  const category = CATEGORY_LABELS[document.category] ?? "Документ";
  return (
    <li className="flex flex-col gap-3 rounded-lg border bg-card p-4 text-card-foreground shadow-elevation-1 sm:flex-row sm:items-center sm:justify-between">
      <div className="flex items-start gap-3">
        <FileText className="mt-0.5 size-5 shrink-0 text-primary" aria-hidden="true" />
        <div className="min-w-0 space-y-0.5">
          <p className="font-medium">{document.title}</p>
          <p className="text-sm text-muted-foreground">
            {category}
            {document.description ? ` · ${document.description}` : ""}
          </p>
        </div>
      </div>
      {href ? (
        <Button asChild variant="outline" size="sm" className="shrink-0">
          <a href={href} target="_blank" rel="noopener noreferrer">
            <Download className="size-4" aria-hidden="true" />
            Скачать
          </a>
        </Button>
      ) : null}
    </li>
  );
}

interface DocumentsSectionProps {
  documents: FestivalDocument[];
}

/**
 * The DOCUMENTS block: the competition's publicly-visible documents.
 *
 * Reuses Competition Documents verbatim — only those the organizer published
 * with a public-facing visibility reach this list (the backend filters them);
 * this section renders nothing when there are none.
 */
export function DocumentsSection({ documents }: DocumentsSectionProps): React.JSX.Element | null {
  if (documents.length === 0) {
    return null;
  }
  return (
    <LandingSection id="documents" title="Документы">
      <ul className="space-y-3">
        {documents.map((document) => (
          <DocumentRow key={document.id} document={document} />
        ))}
      </ul>
    </LandingSection>
  );
}
