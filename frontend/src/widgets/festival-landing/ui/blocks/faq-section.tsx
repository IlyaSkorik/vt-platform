import { ChevronDown } from "lucide-react";
import type { LandingBlock } from "@/features/festival-landing";
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
    <LandingSection id={`block-${block.id}`} title="Часто задаваемые вопросы">
      <ul className="space-y-2">
        {block.faq.map((item) => (
          <li key={item.id}>
            <details className="group rounded-brand border border-brand-line px-4 py-4 md:px-6 md:py-6">
              <summary className="flex cursor-pointer list-none items-center justify-between gap-4 font-bold text-base leading-[22px] outline-none focus-visible:ring-2 focus-visible:ring-ring md:text-lg md:leading-[25px]">
                <span className="min-w-0 break-words">{item.question}</span>
                <ChevronDown
                  className="size-5 shrink-0 transition-transform group-open:rotate-180 md:size-6"
                  aria-hidden="true"
                />
              </summary>
              <p className="mt-3 whitespace-pre-line break-words text-pretty text-sm leading-[19px] md:text-base md:leading-[22px]">
                {item.answer}
              </p>
            </details>
          </li>
        ))}
      </ul>
    </LandingSection>
  );
}
