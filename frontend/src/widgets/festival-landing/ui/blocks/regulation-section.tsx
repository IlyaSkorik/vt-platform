import { Download, FileText } from "lucide-react";
import { formatDate, resolveMediaUrl } from "@/features/festival-catalog";
import type { Regulation } from "@/features/festival-landing";
import { Button } from "@/shared/ui";
import { LandingSection } from "./landing-section";

interface RegulationSectionProps {
  regulation: Regulation;
}

/**
 * The "Положение фестиваля" section — the competition's official regulation.
 *
 * A prominent document card with the current version, publication date and a
 * download link. Surfaced from the Competition (its current regulation), so it
 * is always the single canonical document, never a copy.
 */
export function RegulationSection({ regulation }: RegulationSectionProps): React.JSX.Element {
  const href = resolveMediaUrl(regulation.fileReference);
  const published = formatDate(regulation.publicationDate);
  return (
    <LandingSection id="regulation" title="Положение фестиваля">
      <div className="flex flex-col gap-4 rounded-lg border bg-card p-5 text-card-foreground shadow-elevation-1 sm:flex-row sm:items-center sm:justify-between">
        <div className="flex items-start gap-3">
          <FileText className="mt-0.5 size-6 shrink-0 text-primary" aria-hidden="true" />
          <div className="space-y-0.5">
            <p className="font-medium">{regulation.title}</p>
            <p className="text-sm text-muted-foreground">
              Версия {regulation.version}
              {published ? ` · от ${published}` : ""}
            </p>
          </div>
        </div>
        {href ? (
          <Button asChild className="shrink-0">
            <a href={href} target="_blank" rel="noopener noreferrer">
              <Download className="size-4" aria-hidden="true" />
              Скачать положение
            </a>
          </Button>
        ) : null}
      </div>
    </LandingSection>
  );
}
