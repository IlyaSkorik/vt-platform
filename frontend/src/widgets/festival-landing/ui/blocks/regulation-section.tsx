import { Download, ExternalLink, FileText } from "lucide-react";
import { formatDate, resolveMediaUrl } from "@/features/festival-catalog";
import type { Regulation } from "@/features/festival-landing";
import { isExternalDocLink } from "@/shared/lib";
import { Button } from "@/shared/ui";
import { LandingSection } from "../landing-section";

interface RegulationSectionProps {
  regulation: Regulation;
}

/**
 * «Положение фестиваля» — the festival's official regulation, as one row: the
 * document on the left, the way to open it on the right.
 *
 * Surfaced from the competition's current regulation rather than copied into
 * the landing, so the page can only ever show the canonical document.
 */
export function RegulationSection({ regulation }: RegulationSectionProps): React.JSX.Element {
  const href = resolveMediaUrl(regulation.fileReference);
  const isLink = isExternalDocLink(regulation.fileReference);
  const published = formatDate(regulation.publicationDate);
  return (
    <LandingSection id="regulation" title="Положение фестиваля">
      {/* The same 19px corner the nomination cards wear — the two are the one
          family of panels in this column. */}
      <div className="flex flex-col gap-3 rounded-[19px] border border-brand-line px-3 py-3 md:flex-row md:items-center md:justify-between md:px-3.5">
        <div className="flex min-w-0 items-start gap-2">
          <FileText className="size-5 shrink-0 md:size-[23px]" aria-hidden="true" />
          <div className="min-w-0">
            <p className="break-words font-bold text-base leading-[22px] md:text-xl md:leading-[27px]">
              {regulation.title}
            </p>
            <p className="text-foreground/40 text-sm leading-[19px] md:text-base md:leading-[22px]">
              Версия {regulation.version}
              {published ? ` · от ${published}` : ""}
            </p>
          </div>
        </div>
        {href ? (
          // 33px tall on a 15px corner: a chip-sized plate beside the document,
          // not the page's full-width CTA.
          <Button
            asChild
            className="h-[30px] w-full shrink-0 rounded-brand font-heading font-bold text-sm leading-[19px] hover:bg-brand-press md:h-[33px] md:w-auto md:px-5 md:text-lg md:leading-[25px]"
          >
            <a href={href} target="_blank" rel="noopener noreferrer">
              {isLink ? (
                <ExternalLink className="size-4 md:size-5" aria-hidden="true" />
              ) : (
                <Download className="size-4 md:size-5" aria-hidden="true" />
              )}
              {isLink ? "Открыть положение" : "Скачать положение"}
            </a>
          </Button>
        ) : null}
      </div>
    </LandingSection>
  );
}
