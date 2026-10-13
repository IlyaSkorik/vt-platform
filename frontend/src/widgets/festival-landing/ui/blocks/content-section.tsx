import type { LandingBlock } from "@/features/festival-landing";
import { LandingSection } from "../landing-section";

interface ContentSectionProps {
  block: LandingBlock;
}

/**
 * A free-form CONTENT block — «О фестивале» and anything else the organiser
 * writes: their own title and body.
 *
 * The body is rendered as plain, whitespace-preserving text regardless of the
 * configured `contentFormat` — never as raw HTML — so organiser-authored
 * content cannot inject markup into the public page (XSS-safe by
 * construction). Rich rendering can be added later behind a sanitiser without
 * touching this contract.
 *
 * Full-strength text, not `muted-foreground`: this is the page's prose, and the
 * frame sets it in «Темный текст» like everything else on the panel. It eases
 * to 80% of «свет» at night — the same step the FAQ's answers take, and for the
 * same reason: a long paragraph at full strength over `#110B12` glares.
 */
export function ContentSection({ block }: ContentSectionProps): React.JSX.Element | null {
  const body = block.body?.trim();
  const title = block.title?.trim();
  if (!body && !title) {
    return null;
  }
  return (
    <LandingSection
      id={`block-${block.id}`}
      title={title || "О фестивале"}
      headingGap="mb-[18px] md:mb-5"
    >
      {body ? (
        // `break-words`: organiser text routinely carries a bare URL, and one
        // unbreakable token is enough to stretch the column past the screen.
        /* 18/25 at both widths. This is the page's one piece of prose, and the
           frame does not shrink it on a phone the way it shrinks the chrome. */
        <div className="whitespace-pre-line break-words text-pretty text-foreground text-lg leading-[25px] dark:text-foreground/80">
          {body}
        </div>
      ) : null}
    </LandingSection>
  );
}
