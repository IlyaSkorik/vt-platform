import type * as React from "react";

export interface PosterImageProps extends Omit<React.HTMLAttributes<HTMLDivElement>, "children"> {
  /** Image source. The caller decides what to render when there is none. */
  src: string;
  /** Accessible description. Empty (the default) marks the image decorative. */
  alt?: string;
  /** Extra classes for the visible image — hover transforms belong here. */
  imageClassName?: string;
  /** Native loading hint, forwarded to both layers. */
  loading?: "eager" | "lazy";
}
