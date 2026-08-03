import { cn } from "@/shared/lib/cn";
import type { BrandMarkProps } from "./types";

/**
 * BrandMark — the platform's logo on a rounded plate.
 *
 * Replaces the "ВТ" / "VT" initials the three workspace shells used to draw. Decorative:
 * every shell renders it inside a link that already carries the accessible name, so it is
 * hidden from assistive technology rather than labelled twice.
 *
 * **How the colouring works, because the artwork inverts what you would expect.**
 * `public/logo.svg` is a filled square with the comet *subtracted* from it — the mark is a
 * hole, not a shape. So it is used as a CSS mask: the mask's alpha keeps the plate and cuts
 * the comet out of it, and what shows through the cut is the element behind. That means the
 * outer `background` is the **comet's** colour and the inner one is the **plate's** — the
 * opposite of how it reads, which is why they are named here rather than left to callers.
 *
 * Masking rather than inlining the path keeps `public/logo.svg` the only copy of the
 * artwork; a second copy pasted into a module would drift the first time the logo is
 * redrawn. The cost is one cached request the shell makes anyway.
 *
 * The plate follows the theme (`primary`); the comet does not (`brand-mark`, which is the
 * light one in both themes — see the note on that token for why `primary-foreground` looks
 * right here and is not). There is deliberately no per-shell variant: if the platform
 * console ever needs its own mark, that is a prop to add then, rather than a distinction
 * inherited from a badge that no longer exists.
 *
 * Sizing and rounding come from the caller (`size-8 rounded-md`, matching whatever the
 * initials used), so this stays a mark and not a layout decision.
 */
export function BrandMark({ className, ...props }: BrandMarkProps): React.JSX.Element {
  return (
    <span
      aria-hidden="true"
      data-slot="brand-mark"
      // `overflow-hidden` is what rounds the artwork: the SVG's own edge is a hard square,
      // so the corners have to be clipped by this box rather than asked of the file.
      // The background here is what shows through the comet-shaped hole.
      className={cn("block shrink-0 overflow-hidden bg-brand-mark", className)}
      {...props}
    >
      <span
        className="block size-full bg-primary"
        style={{
          maskImage: "url('/logo.svg')",
          maskSize: "100% 100%",
          maskRepeat: "no-repeat",
          WebkitMaskImage: "url('/logo.svg')",
          WebkitMaskSize: "100% 100%",
          WebkitMaskRepeat: "no-repeat",
        }}
      />
    </span>
  );
}
