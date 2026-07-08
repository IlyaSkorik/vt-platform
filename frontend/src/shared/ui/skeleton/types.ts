import type * as React from "react";

export type SkeletonVariant = "text" | "circle" | "rect";

export interface SkeletonProps extends React.HTMLAttributes<HTMLDivElement> {
  /** Placeholder shape. Text uses a shorter height and rounded corners. */
  variant?: SkeletonVariant;
}
