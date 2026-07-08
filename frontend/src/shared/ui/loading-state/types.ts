import type * as React from "react";

export type LoadingStateSize = "sm" | "md" | "lg";

export interface LoadingStateProps extends React.HTMLAttributes<HTMLDivElement> {
  /** Optional visible label rendered beside the spinner. */
  label?: React.ReactNode;
  /** Spinner diameter preset. */
  size?: LoadingStateSize;
  /**
   * Accessible name announced by assistive tech. Defaults to "Загрузка" and is
   * used as the visually-hidden status text when no visible `label` is given.
   */
  srLabel?: string;
}
