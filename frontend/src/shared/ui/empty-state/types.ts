import type * as React from "react";

export interface EmptyStateProps extends Omit<React.HTMLAttributes<HTMLElement>, "title"> {
  /** Illustration or icon node. Defaults to an `Inbox` glyph. */
  icon?: React.ReactNode;
  /** Primary heading describing the empty situation. */
  title: React.ReactNode;
  /** Optional supporting copy under the title. */
  description?: React.ReactNode;
  /** Optional action slot (e.g. a Button) rendered below the copy. */
  action?: React.ReactNode;
}
