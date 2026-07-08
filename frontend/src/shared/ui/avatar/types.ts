import type { Avatar as AvatarPrimitive } from "radix-ui";
import type * as React from "react";

export type AvatarSize = "xs" | "sm" | "md" | "lg" | "xl";

export interface AvatarProps
  extends Omit<React.ComponentPropsWithoutRef<typeof AvatarPrimitive.Root>, "children"> {
  /** Image source. When it fails to load (or is absent) the fallback shows. */
  src?: string;
  /** Accessible, descriptive text for the image. */
  alt?: string;
  /** Initials or node shown while the image is loading or on error. */
  fallback?: React.ReactNode;
  /** Avatar diameter. */
  size?: AvatarSize;
}
