import type * as React from "react";

export interface InputProps
  extends Omit<React.InputHTMLAttributes<HTMLInputElement>, "size" | "prefix"> {
  /** Visible field label, associated with the input via `htmlFor`/`id`. */
  label?: React.ReactNode;
  /** Helper text shown beneath the field when there is no error. */
  description?: React.ReactNode;
  /** Error message. When set, the field is marked invalid and styled as error. */
  error?: React.ReactNode;
  /** Success message shown beneath the field (ignored when `error` is set). */
  success?: React.ReactNode;
  /** Non-interactive text adornment rendered inside the field, on the left. */
  prefix?: React.ReactNode;
  /** Non-interactive text adornment rendered inside the field, on the right. */
  suffix?: React.ReactNode;
  /** Icon rendered inside the field, before the text. */
  leadingIcon?: React.ReactNode;
  /** Icon rendered inside the field, after the text. */
  trailingIcon?: React.ReactNode;
  /**
   * Interactive trailing slot (e.g. a clear/reveal button). Unlike
   * `trailingIcon` it is NOT `aria-hidden`, so it stays in the a11y tree.
   */
  action?: React.ReactNode;
  /** Wrapper element class (the field container), for layout composition. */
  containerClassName?: string;
}
