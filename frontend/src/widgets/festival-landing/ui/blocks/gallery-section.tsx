import { resolveMediaUrl } from "@/features/festival-catalog";
import type { LandingBlock } from "@/features/festival-landing";
import { LandingSection } from "../landing-section";

interface GallerySectionProps {
  block: LandingBlock;
}

/** The GALLERY block: a responsive image grid with optional captions. */
export function GallerySection({ block }: GallerySectionProps): React.JSX.Element | null {
  const images = block.images
    .map((image) => ({ ...image, src: resolveMediaUrl(image.url) }))
    .filter((image) => image.src != null);
  if (images.length === 0) {
    return null;
  }
  return (
    <LandingSection id={`block-${block.id}`} title="Галерея">
      <ul className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-4">
        {images.map((image) => (
          <li key={image.id}>
            <figure className="overflow-hidden rounded-lg border bg-muted">
              <img
                src={image.src ?? ""}
                alt={image.caption ?? ""}
                loading="lazy"
                className="aspect-square size-full object-cover transition-transform duration-300 hover:scale-105"
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
    </LandingSection>
  );
}
