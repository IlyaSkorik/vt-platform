import type { LandingBlock } from "@/features/festival-landing";
import { LandingSection } from "../landing-section";

interface ContentSectionProps {
  block: LandingBlock;
}

/**
 * A free-form CONTENT block: an organizer-authored title and body.
 *
 * The body is rendered as plain, whitespace-preserving text regardless of the
 * configured `contentFormat` — never as raw HTML — so organizer-authored content
 * can never inject markup into the public page (XSS-safe by construction). Rich
 * rendering can be added later behind a sanitizer without touching this contract.
 */
export function ContentSection({ block }: ContentSectionProps): React.JSX.Element | null {
  const body = block.body?.trim();
  const title = block.title?.trim();
  if (!body && !title) {
    return null;
  }
  return (
    <LandingSection id={`block-${block.id}`} title={title || "Информация"}>
      {body ? (
        <div className="max-w-3xl whitespace-pre-line text-pretty leading-relaxed text-muted-foreground">
          {body}
        </div>
      ) : null}
    </LandingSection>
  );
}
