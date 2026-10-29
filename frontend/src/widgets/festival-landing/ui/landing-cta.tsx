import { Link } from "react-router";
import type { LandingCta } from "@/features/festival-landing";
import { cn } from "@/shared/lib";
import { Button } from "@/shared/ui";

interface LandingCtaButtonProps {
  cta: LandingCta;
  /** Registration-wizard route the actionable "Apply" CTA links to. */
  applyPath: string;
  className?: string;
}

/**
 * The page's one call to action, driven entirely by the public status: only an
 * open registration renders a link to the wizard, every other status renders
 * the same plate disabled with a status label. The CTA can therefore never
 * invite an action the festival does not allow.
 *
 * The frame draws it as a full-width «Акцентище» plate under the summary card,
 * 61px tall with its label at 28/38 — a bar rather than a button, which is why
 * it carries its own geometry instead of a `size`. No trailing arrow: the frame
 * has none, and on a plate this wide the label is already unmissable.
 */
export function LandingCtaButton({
  cta,
  applyPath,
  className,
}: LandingCtaButtonProps): React.JSX.Element {
  // `dark:bg-brand`, because `--primary` drifts lighter at night and the frame
  // keeps «Акцент светлая» `#8A2BCE` on both plates — the same pairing every primary
  // button on the public surfaces uses. `hover:bg-brand-press` rather than the
  // variant's own fade of the primary.
  // 189×37 and centred on a phone, a full-width 61px bar from `md` up. The bar
  // is the desktop card's closing edge and wants its whole width; on a phone
  // the card is the screen, and a plate across it reads as a second header.
  const plate = cn(
    "mx-auto h-[37px] w-[189px] rounded-brand font-heading font-bold text-base leading-[22px] hover:bg-brand-press md:mx-0 md:h-[61px] md:w-full md:text-[28px] md:leading-[38px] dark:bg-brand dark:text-brand-mark dark:hover:bg-brand-press",
    className,
  );

  if (cta.canApply) {
    return (
      <Button asChild size="lg" className={plate}>
        <Link to={applyPath}>{cta.ctaLabel}</Link>
      </Button>
    );
  }
  return (
    <Button size="lg" disabled className={plate}>
      {cta.ctaLabel}
    </Button>
  );
}
