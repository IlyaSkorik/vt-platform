import type { LandingBlock } from "@/features/festival-landing";
import { ChevronDownIcon } from "@/shared/ui";
import { LandingSection } from "../landing-section";

interface FaqSectionProps {
  block: LandingBlock;
}

/**
 * «Часто задаваемые вопросы» — native `<details>` disclosures, one per item.
 *
 * Native rather than a scripted accordion: it opens with no JavaScript, it is
 * keyboard-operable and announced correctly for free, and the browser's own
 * find-in-page can open a collapsed answer to show a match.
 */
export function FaqSection({ block }: FaqSectionProps): React.JSX.Element | null {
  if (block.faq.length === 0) {
    return null;
  }
  return (
    <LandingSection
      id={`block-${block.id}`}
      title="Часто задаваемые вопросы"
      headingGap="mb-4 md:mb-5"
    >
      <ul className="space-y-2">
        {block.faq.map((item) => (
          <li key={item.id}>
            {/* Two pixels on a phone, one on a desktop: a hairline across a
                375px screen stops reading as an edge at all. */}
            <details className="group rounded-brand border-2 border-brand-line px-4 py-4 md:border md:px-6 md:py-6">
              <summary className="flex cursor-pointer list-none items-center justify-between gap-4 font-bold text-base leading-[22px] outline-none focus-visible:ring-2 focus-visible:ring-ring md:text-lg md:leading-[25px]">
                <span className="min-w-0 break-words">{item.question}</span>
                {/* 25×14 — the frame's own wedge, wide and shallow, not a
                    stroked Lucide chevron. Sized on both axes for that reason. */}
                <ChevronDownIcon
                  className="h-2.5 w-[18px] shrink-0 transition-transform group-open:rotate-180 md:h-3.5 md:w-[25px]"
                  aria-hidden="true"
                />
              </summary>
              {/* 80% of «свет» at night: an answer is secondary to the question
                  above it, and at full strength the two read as one block. */}
              <p className="mt-3 whitespace-pre-line break-words text-pretty text-sm leading-[19px] md:text-base md:leading-[22px] dark:text-foreground/80">
                {item.answer}
              </p>
            </details>
          </li>
        ))}
      </ul>
    </LandingSection>
  );
}
