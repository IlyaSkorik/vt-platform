import { ChevronLeft, ChevronRight } from "lucide-react";
import { useCallback, useEffect, useRef, useState } from "react";
import { resolveMediaUrl } from "@/features/festival-catalog";
import type { LandingBlock } from "@/features/festival-landing";
import { IconButton } from "@/shared/ui";
import { LandingSection } from "../landing-section";

interface GalleryImageView {
  id: string;
  src: string;
  caption: string | null;
}

/**
 * A horizontal, snap-scrolling gallery carousel.
 *
 * One rowful of images is a "page": the prev/next controls advance by exactly
 * the visible width, and CSS scroll-snap keeps each page aligned. Swipe / drag
 * works natively on touch; the arrows are hidden entirely when everything
 * already fits (nothing to page through).
 */
function GalleryCarousel({ images }: { images: GalleryImageView[] }): React.JSX.Element {
  const trackRef = useRef<HTMLUListElement>(null);
  const [atStart, setAtStart] = useState(true);
  const [atEnd, setAtEnd] = useState(false);
  const [scrollable, setScrollable] = useState(false);

  const sync = useCallback(() => {
    const el = trackRef.current;
    if (!el) {
      return;
    }
    const max = el.scrollWidth - el.clientWidth;
    setScrollable(max > 1);
    setAtStart(el.scrollLeft <= 1);
    setAtEnd(el.scrollLeft >= max - 1);
  }, []);

  useEffect(() => {
    sync();
    const el = trackRef.current;
    if (!el) {
      return;
    }
    el.addEventListener("scroll", sync, { passive: true });
    window.addEventListener("resize", sync);
    return () => {
      el.removeEventListener("scroll", sync);
      window.removeEventListener("resize", sync);
    };
  }, [sync]);

  const page = (direction: 1 | -1): void => {
    const el = trackRef.current;
    if (el) {
      el.scrollBy({ left: direction * el.clientWidth, behavior: "smooth" });
    }
  };

  return (
    <div className="relative">
      <ul
        ref={trackRef}
        className="flex snap-x snap-mandatory gap-3 overflow-x-auto pb-1 [-ms-overflow-style:none] [scrollbar-width:none] [&::-webkit-scrollbar]:hidden"
      >
        {images.map((image) => (
          <li
            key={image.id}
            className="shrink-0 basis-[78%] snap-start sm:basis-[46%] lg:basis-[31%] xl:basis-[23%]"
          >
            <figure className="overflow-hidden rounded-lg border bg-muted">
              <img
                src={image.src}
                alt={image.caption ?? ""}
                loading="lazy"
                className="aspect-[4/3] size-full object-cover"
              />
              {image.caption ? (
                <figcaption className="truncate px-2 py-1.5 text-xs text-muted-foreground">
                  {image.caption}
                </figcaption>
              ) : null}
            </figure>
          </li>
        ))}
      </ul>

      {scrollable ? (
        <>
          <IconButton
            aria-label="Предыдущие фото"
            icon={<ChevronLeft />}
            variant="outline"
            size="sm"
            onClick={() => page(-1)}
            disabled={atStart}
            className="absolute left-2 top-1/2 -translate-y-1/2 bg-background/90 shadow-elevation-2 backdrop-blur disabled:opacity-0"
          />
          <IconButton
            aria-label="Следующие фото"
            icon={<ChevronRight />}
            variant="outline"
            size="sm"
            onClick={() => page(1)}
            disabled={atEnd}
            className="absolute right-2 top-1/2 -translate-y-1/2 bg-background/90 shadow-elevation-2 backdrop-blur disabled:opacity-0"
          />
        </>
      ) : null}
    </div>
  );
}

interface GallerySectionProps {
  block: LandingBlock;
}

/** The GALLERY block: images shown as a paged, snap-scrolling carousel. */
export function GallerySection({ block }: GallerySectionProps): React.JSX.Element | null {
  const images = block.images
    .map((image) => ({ id: image.id, src: resolveMediaUrl(image.url), caption: image.caption }))
    .filter((image): image is GalleryImageView => image.src != null);
  if (images.length === 0) {
    return null;
  }
  return (
    <LandingSection id={`block-${block.id}`} title="Галерея">
      <GalleryCarousel images={images} />
    </LandingSection>
  );
}
