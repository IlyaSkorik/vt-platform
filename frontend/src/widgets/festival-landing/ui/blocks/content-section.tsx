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
 * frame sets it in «Темный текст» like everything else on the panel.
 */
export function ContentSection({ block }: ContentSectionProps): React.JSX.Element | null {
  const body = block.body?.trim();
  const title = block.title?.trim();
  if (!body && !title) {
    return null;
  }
  return (
    <LandingSection id={`block-${block.id}`} title={title || "О фестивале"}>
      {body ? (
        // `break-words`: organiser text routinely carries a bare URL, and one
        // unbreakable token is enough to stretch the column past the screen.
        <div className="whitespace-pre-line break-words text-pretty text-foreground text-sm leading-[19px] md:text-lg md:leading-[25px]">
          {body}
        </div>
      ) : null}
    </LandingSection>
  );
}
