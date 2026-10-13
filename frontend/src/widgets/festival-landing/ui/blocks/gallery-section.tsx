import { ChevronLeft, ChevronRight } from "lucide-react";
import { useState } from "react";
import { resolveMediaUrl } from "@/features/festival-catalog";
import type { LandingBlock } from "@/features/festival-landing";
import { Dialog, DialogContent, DialogTitle, IconButton } from "@/shared/ui";
import { LandingCarousel } from "../landing-carousel";
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
 * One tile: the photograph on the frame's 4:3 plate, and a click opens it
 * full-size. The caption is not printed on the tile — the frame draws a clean
 * row of pictures — but it is still the button's accessible name and the
 * lightbox's heading, so it is carried rather than dropped.
 */
function GalleryTile({
  image,
  onOpen,
}: {
  image: GalleryImageView;
  onOpen: () => void;
}): React.JSX.Element {
  return (
    <button
      type="button"
      onClick={onOpen}
      aria-label={image.caption ? `Открыть фото: ${image.caption}` : "Открыть фото"}
      className="group block aspect-[291/221] w-full cursor-zoom-in overflow-hidden rounded-brand bg-media-placeholder outline-none focus-visible:ring-2 focus-visible:ring-ring"
    >
      {/* Still lazy — a gallery can run to dozens of photographs — but decoded
          off the main thread, so the decode of the next screen cannot land
          inside the scroll animation that asked for it. */}
      <img
        src={image.src}
        alt={image.caption ?? ""}
        loading="lazy"
        decoding="async"
        className="size-full object-cover transition-transform duration-300 group-hover:scale-105"
      />
    </button>
  );
}

interface GallerySectionProps {
  block: LandingBlock;
}

/** The GALLERY block: a paged carousel of photographs, four to a screen, with
 * a lightbox behind every tile. */
export function GallerySection({ block }: GallerySectionProps): React.JSX.Element | null {
  const [active, setActive] = useState<number | null>(null);
  const images = block.images
    .map((image) => ({ id: image.id, src: resolveMediaUrl(image.url), caption: image.caption }))
    .filter((image): image is GalleryImageView => image.src != null);
  if (images.length === 0) {
    return null;
  }
  return (
    <LandingSection
      id={`block-${block.id}`}
      title="Галерея"
      align="center"
      headingGap="mb-5 md:mb-[26px]"
    >
      <LandingCarousel
        label="Галерея"
        items={images.map((image, index) => ({
          id: image.id,
          content: (
            <GalleryTile
              image={image}
              onOpen={() => {
                setActive(index);
              }}
            />
          ),
        }))}
        // 8px between tiles, so four of them plus three gaps fill the track —
        // the basis below has to stay in step with this gap.
        gapClassName="gap-2"
        sideGapClassName="gap-4 md:gap-3.5"
        itemClassName="basis-full sm:basis-[calc((100%-0.5rem)/2)] lg:basis-[calc((100%-1rem)/3)] xl:basis-[calc((100%-1.5rem)/4)]"
      />
      <GalleryLightbox
        images={images}
        index={active}
        onClose={() => {
          setActive(null);
        }}
        onNavigate={setActive}
      />
    </LandingSection>
  );
}
