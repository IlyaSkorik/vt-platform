import { ChevronDown } from "lucide-react";
import type { LandingBlock } from "@/features/festival-landing";
import { LandingSection } from "../landing-section";

interface FaqSectionProps {
  block: LandingBlock;
}

/** The FAQ block: a list of native disclosure (question/answer) items. */
export function FaqSection({ block }: FaqSectionProps): React.JSX.Element | null {
  if (block.faq.length === 0) {
    return null;
  }
  return (
    <LandingSection id={`block-${block.id}`} title="Частые вопросы">
      <ul className="space-y-3">
        {block.faq.map((item) => (
          <li key={item.id}>
            <details className="group rounded-lg border bg-card px-4 py-3 text-card-foreground shadow-elevation-1">
              <summary className="flex cursor-pointer list-none items-center justify-between gap-3 font-medium outline-none focus-visible:ring-2 focus-visible:ring-ring">
                <span className="min-w-0 break-words">{item.question}</span>
                <ChevronDown
                  className="size-4 shrink-0 text-muted-foreground transition-transform group-open:rotate-180"
                  aria-hidden="true"
                />
              </summary>
              <p className="mt-2 whitespace-pre-line break-words text-pretty text-sm leading-relaxed text-muted-foreground">
                {item.answer}
              </p>
            </details>
          </li>
        ))}
      </ul>
    </LandingSection>
  );
}
