import { forwardRef } from "react";
import { cn } from "@/shared/lib/cn";
import type {
  PageActionsProps,
  PageContainerProps,
  PageContentProps,
  PageDescriptionProps,
  PageHeaderProps,
  PageSectionProps,
  PageTitleProps,
} from "./types";

/**
 * Page layout primitives — the reusable skeleton every screen composes inside
 * the Application Shell.
 *
 * These give pages one consistent rhythm (max width, header/content spacing,
 * heading hierarchy) so no feature hand-rolls its own layout. They are pure
 * structure: token-only styling, no business logic, theme-agnostic. Compose
 * as: `PageContainer > PageHeader (PageTitle + PageDescription + PageActions)
 * + PageContent (PageSection…)`.
 *
 * Every one of these carries `min-w-0`. A flex item is as wide as its content
 * by default, so without it a single wide descendant — a table, a preview, a
 * long unbreakable string — travels up this chain and scrolls the whole
 * document sideways, chrome and all. Pages that need something wider than the
 * viewport give it its own `overflow-x-auto` container instead.
 */

const CONTAINER_SIZES = {
  narrow: "max-w-3xl",
  default: "max-w-5xl",
  wide: "max-w-7xl",
  full: "max-w-none",
} as const;

export const PageContainer = forwardRef<HTMLDivElement, PageContainerProps>(function PageContainer(
  { className, size = "default", ...props },
  ref,
) {
  return (
    <div
      ref={ref}
      data-slot="page-container"
      className={cn("mx-auto flex w-full min-w-0 flex-col gap-6", CONTAINER_SIZES[size], className)}
      {...props}
    />
  );
});

export const PageHeader = forwardRef<HTMLDivElement, PageHeaderProps>(function PageHeader(
  { className, children, actions, ...props },
  ref,
) {
  return (
    <div
      ref={ref}
      data-slot="page-header"
      className={cn("flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between", className)}
      {...props}
    >
      <div className="flex flex-col gap-1">{children}</div>
      {actions != null && <PageActions>{actions}</PageActions>}
    </div>
  );
});

export const PageTitle = forwardRef<HTMLHeadingElement, PageTitleProps>(function PageTitle(
  { className, as: Comp = "h1", ...props },
  ref,
) {
  return (
    <Comp
      ref={ref}
      data-slot="page-title"
      className={cn("font-bold text-2xl text-foreground tracking-tight", className)}
      {...props}
    />
  );
});

export const PageDescription = forwardRef<HTMLParagraphElement, PageDescriptionProps>(
  function PageDescription({ className, ...props }, ref) {
    return (
      <p
        ref={ref}
        data-slot="page-description"
        className={cn("text-muted-foreground text-sm", className)}
        {...props}
      />
    );
  },
);

export const PageActions = forwardRef<HTMLDivElement, PageActionsProps>(function PageActions(
  { className, ...props },
  ref,
) {
  return (
    <div
      ref={ref}
      data-slot="page-actions"
      className={cn("flex shrink-0 flex-wrap items-center gap-2", className)}
      {...props}
    />
  );
});

export const PageContent = forwardRef<HTMLDivElement, PageContentProps>(function PageContent(
  { className, ...props },
  ref,
) {
  return (
    <div
      ref={ref}
      data-slot="page-content"
      className={cn("flex min-w-0 flex-col gap-6", className)}
      {...props}
    />
  );
});

export const PageSection = forwardRef<HTMLElement, PageSectionProps>(function PageSection(
  { className, title, description, actions, children, ...props },
  ref,
) {
  const hasHeader = title != null || description != null || actions != null;
  return (
    <section
      ref={ref}
      data-slot="page-section"
      className={cn("flex min-w-0 flex-col gap-4", className)}
      {...props}
    >
      {hasHeader && (
        <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
          <div className="flex flex-col gap-1">
            {title != null && (
              <h2 className="font-semibold text-foreground text-lg tracking-tight">{title}</h2>
            )}
            {description != null && <p className="text-muted-foreground text-sm">{description}</p>}
          </div>
          {actions != null && <PageActions>{actions}</PageActions>}
        </div>
      )}
      {children}
    </section>
  );
});
