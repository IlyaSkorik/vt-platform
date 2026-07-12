import { ArrowRight } from "lucide-react";
import { Link } from "react-router";
import type { LandingCta } from "@/features/festival-landing";
import { Button, type ButtonProps } from "@/shared/ui";

interface LandingCtaButtonProps {
  cta: LandingCta;
  /** Registration-wizard route the actionable "Apply" CTA links to. */
  applyPath: string;
  size?: ButtonProps["size"];
  className?: string;
}

/**
 * The primary call-to-action, driven entirely by the public status.
 *
 * Only an open registration renders an actionable link to the registration
 * wizard; every other status renders the same button disabled with a status
 * label, so the CTA can never invite an action the competition does not allow.
 */
export function LandingCtaButton({
  cta,
  applyPath,
  size = "lg",
  className,
}: LandingCtaButtonProps): React.JSX.Element {
  if (cta.canApply) {
    return (
      <Button asChild size={size} className={className}>
        <Link to={applyPath}>
          {cta.ctaLabel}
          <ArrowRight className="size-4" aria-hidden="true" />
        </Link>
      </Button>
    );
  }
  return (
    <Button size={size} disabled className={className}>
      {cta.ctaLabel}
    </Button>
  );
}
