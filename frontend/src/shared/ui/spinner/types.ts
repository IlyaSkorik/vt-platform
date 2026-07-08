import type * as React from "react";

export type SpinnerSize = "xs" | "sm" | "md" | "lg" | "xl";

export interface SpinnerProps extends React.HTMLAttributes<HTMLSpanElement> {
  /** Spinner diameter. */
  size?: SpinnerSize;
  /** Accessible label announced to assistive tech. Defaults to "Загрузка". */
  label?: string;
}
