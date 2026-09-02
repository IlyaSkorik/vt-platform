import { cn } from "@/shared/lib/cn";
import type { PosterImageProps } from "./types";

/**
 * PosterImage — a picture shown **whole** inside a frame it does not fit.
 *
 * The festival poster ("Афиша") is authored as a portrait 3:4 sheet, and every card
 * that shows it has a landscape frame (16/10 in the catalog, 16/9 on the home page).
 * `object-cover` in that frame crops the poster's top and bottom — which is exactly
 * where a poster puts its title and its dates. So the visible layer is
 * `object-contain`: the whole sheet, at its own proportions, whatever the frame.
 *
 * That leaves empty bands beside it, and the band is what this component is really
 * about. A flat `bg-muted` reads as a rendering mistake — a small picture stranded in
 * a grey box. A blurred copy of the poster itself reads as depth instead, and it
 * carries the poster's own colours, so a card stays as loud as the artwork on it. The
 * copy costs no second request: it is the same URL the browser already has.
 *
 * Fills its parent, so the frame — aspect ratio, rounding, placeholder — stays the
 * caller's decision. It is positioned, so absolute overlays (status badges, a price
 * chip) can be siblings after it and land on top.
 */
export function PosterImage({
  src,
  alt = "",
  imageClassName,
  loading,
  className,
  ...props
}: PosterImageProps): React.JSX.Element {
  return (
    <div
      data-slot="poster-image"
      className={cn("relative size-full overflow-hidden", className)}
      {...props}
    >
      {/* `scale-110`: a blur samples past the element's edge, so an unscaled copy
          fades to transparent along the frame and lets the background through. */}
      <img
        src={src}
        alt=""
        aria-hidden="true"
        loading={loading}
        className="absolute inset-0 size-full scale-110 object-cover blur-xl"
      />
      <img
        src={src}
        alt={alt}
        loading={loading}
        className={cn("relative size-full object-contain", imageClassName)}
      />
    </div>
  );
}
