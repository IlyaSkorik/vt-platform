import type * as React from "react";

export interface TextareaProps extends React.TextareaHTMLAttributes<HTMLTextAreaElement> {
  /** Visible field label, associated with the control via `htmlFor`/`id`. */
  label?: React.ReactNode;
  /** Helper text shown beneath the field when there is no error. */
  description?: React.ReactNode;
  /** Error message. When set, the field is marked invalid and styled as error. */
  error?: React.ReactNode;
  /** Success message shown beneath the field (ignored when `error` is set). */
  success?: React.ReactNode;
  /** Wrapper element class, for layout composition. */
  containerClassName?: string;
}
