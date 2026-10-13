import { Download } from "lucide-react";
import { formatDate, resolveMediaUrl } from "@/features/festival-catalog";
import type { Regulation } from "@/features/festival-landing";
import { isExternalDocLink } from "@/shared/lib";
import { Button, DocumentIcon, OpenInNewIcon } from "@/shared/ui";
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
          {/* 15.33×19.17 inside the frame's 23px slot, and 14×17.5 in the 21px
              one a phone gives it — the glyph's own size, not the slot's. */}
          <DocumentIcon
            className="mt-0.5 h-[17.5px] w-3.5 shrink-0 md:h-[19.17px] md:w-[15.33px]"
            aria-hidden="true"
          />
          <div className="min-w-0">
            <p className="break-words font-bold text-base leading-[22px] md:text-xl md:leading-[27px]">
              {regulation.title}
            </p>
            <p className="text-foreground/40 text-sm leading-[19px] md:text-base md:leading-[22px] dark:text-foreground/70">
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
            className="h-[30px] w-[194px] shrink-0 justify-between rounded-brand px-3 font-heading font-bold text-sm leading-[19px] hover:bg-brand-press md:h-[33px] md:w-auto md:justify-center md:px-5 md:text-lg md:leading-[25px] dark:bg-brand dark:text-brand-mark dark:hover:bg-brand-press"
          >
            <a href={href} target="_blank" rel="noopener noreferrer">
              {/* 14.25, the same mark at the same size as on the map links —
                  the export draws it 3% wider here (14.71×14.25) and that is
                  Figma stretching one glyph, not a second icon. */}
              {isLink ? (
                <OpenInNewIcon className="size-[14.25px]" aria-hidden="true" />
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
