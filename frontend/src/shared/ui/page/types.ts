import type * as React from "react";

/** Root wrapper that constrains and pads a page's content. */
export interface PageContainerProps extends React.ComponentPropsWithoutRef<"div"> {
  /**
   * Max content width. `default` suits most screens; `wide` for dense tables /
   * dashboards; `narrow` for reading-oriented pages; `full` removes the cap.
   */
  size?: "narrow" | "default" | "wide" | "full";
}

/** Header band grouping the title/description and page-level actions. */
export interface PageHeaderProps extends React.ComponentPropsWithoutRef<"div"> {
  /** Trailing action slot (buttons, menus) aligned opposite the title block. */
  actions?: React.ReactNode;
}

/** The page's accessible heading. Renders an `<h1>` by default. */
export interface PageTitleProps extends React.ComponentPropsWithoutRef<"h1"> {
  as?: "h1" | "h2";
}

export type PageDescriptionProps = React.ComponentPropsWithoutRef<"p">;

export type PageActionsProps = React.ComponentPropsWithoutRef<"div">;

/** Main body region of a page. */
export type PageContentProps = React.ComponentPropsWithoutRef<"div">;

/** A titled subsection within a page's content. */
export interface PageSectionProps extends Omit<React.ComponentPropsWithoutRef<"section">, "title"> {
  title?: React.ReactNode;
  description?: React.ReactNode;
  /** Trailing action slot for the section header. */
  actions?: React.ReactNode;
}

/** Full-page empty/placeholder state (e.g. an unbuilt section). */
export interface EmptyPageProps extends Omit<React.ComponentPropsWithoutRef<"div">, "title"> {
  icon?: React.ReactNode;
  title: React.ReactNode;
  description?: React.ReactNode;
  action?: React.ReactNode;
}
