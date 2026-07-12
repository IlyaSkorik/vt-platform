import { ChevronLeft, ChevronRight } from "lucide-react";
import { useCallback, useEffect, useRef, useState } from "react";
import { resolveMediaUrl } from "@/features/festival-catalog";
import type { LandingBlock } from "@/features/festival-landing";
import { Dialog, DialogContent, DialogTitle, IconButton } from "@/shared/ui";
import { LandingSection } from "../landing-section";

interface GalleryImageView {
  id: string;
  src: string;
  caption: string | null;
}

/** Full-screen lightbox for the gallery: one image at a time, with paging. */
function GalleryLightbox({
  images,
  index,
  onClose,
  onNavigate,
}: {
  images: GalleryImageView[];
  index: number | null;
  onClose: () => void;
  onNavigate: (next: number) => void;
}): React.JSX.Element {
  const open = index !== null;
  const current = index !== null ? images[index] : undefined;
  const many = images.length > 1;

  const step = (delta: number): void => {
    if (index === null) {
      return;
    }
    onNavigate((index + delta + images.length) % images.length);
  };

  return (
    <Dialog
      open={open}
      onOpenChange={(next) => {
        if (!next) {
          onClose();
        }
      }}
    >
      {current ? (
        <DialogContent
          className="max-w-4xl gap-3 p-3 sm:p-4"
          onKeyDown={(event) => {
            if (event.key === "ArrowRight") {
              step(1);
            } else if (event.key === "ArrowLeft") {
              step(-1);
            }
          }}
        >
          <DialogTitle className="sr-only">{current.caption ?? "Просмотр фото"}</DialogTitle>
          <div className="relative flex items-center justify-center">
            <img
              src={current.src}
              alt={current.caption ?? ""}
              className="max-h-[80vh] w-full rounded-md object-contain"
            />
            {many ? (
              <>
                <IconButton
                  aria-label="Предыдущее фото"
                  icon={<ChevronLeft />}
                  variant="outline"
                  onClick={() => step(-1)}
                  className="absolute left-2 top-1/2 -translate-y-1/2 bg-background/90 shadow-elevation-2 backdrop-blur"
                />
                <IconButton
                  aria-label="Следующее фото"
                  icon={<ChevronRight />}
                  variant="outline"
                  onClick={() => step(1)}
                  className="absolute right-2 top-1/2 -translate-y-1/2 bg-background/90 shadow-elevation-2 backdrop-blur"
                />
              </>
            ) : null}
          </div>
          <div className="flex items-center justify-between gap-3 text-sm text-muted-foreground">
            <span className="truncate">{current.caption ?? ""}</span>
            {many && index !== null ? (
              <span className="shrink-0 tabular-nums">
                {index + 1} / {images.length}
              </span>
            ) : null}
          </div>
        </DialogContent>
      ) : null}
    </Dialog>
  );
}

/**
 * A horizontal, snap-scrolling gallery carousel.
 *
 * One rowful of images is a "page": the prev/next controls advance by exactly
 * the visible width, and CSS scroll-snap keeps each page aligned. Swipe / drag
 * works natively on touch; the arrows are hidden entirely when everything
 * already fits. Clicking a thumbnail opens it full-size in a lightbox.
 */
function GalleryCarousel({ images }: { images: GalleryImageView[] }): React.JSX.Element {
  const trackRef = useRef<HTMLUListElement>(null);
  const [atStart, setAtStart] = useState(true);
  const [atEnd, setAtEnd] = useState(false);
  const [scrollable, setScrollable] = useState(false);
  const [active, setActive] = useState<number | null>(null);

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
        {images.map((image, imageIndex) => (
          <li
            key={image.id}
            className="shrink-0 basis-[78%] snap-start sm:basis-[46%] lg:basis-[31%] xl:basis-[23%]"
          >
            <figure className="overflow-hidden rounded-lg border bg-muted">
              <button
                type="button"
                onClick={() => setActive(imageIndex)}
                className="group block w-full cursor-zoom-in outline-none focus-visible:ring-2 focus-visible:ring-ring"
                aria-label={image.caption ? `Открыть фото: ${image.caption}` : "Открыть фото"}
              >
                <img
                  src={image.src}
                  alt={image.caption ?? ""}
                  loading="lazy"
                  className="aspect-[4/3] size-full object-cover transition-transform duration-300 group-hover:scale-105"
                />
              </button>
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

      <GalleryLightbox
        images={images}
        index={active}
        onClose={() => setActive(null)}
        onNavigate={setActive}
      />
    </div>
  );
}

interface GallerySectionProps {
  block: LandingBlock;
}

/** The GALLERY block: images shown as a paged carousel with a lightbox. */
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
