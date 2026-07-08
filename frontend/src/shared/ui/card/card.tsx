import { forwardRef } from "react";
import { cn } from "@/shared/lib/cn";
import type {
  CardContentProps,
  CardDescriptionProps,
  CardFooterProps,
  CardHeaderProps,
  CardProps,
  CardTitleProps,
} from "./types";

/**
 * Card — a composable surface container. Colours flow through semantic card
 * tokens with layered elevation, so it themes automatically. Compose with
 * `CardHeader`, `CardTitle`, `CardDescription`, `CardContent` and `CardFooter`.
 */
export const Card = forwardRef<HTMLDivElement, CardProps>(function Card(
  { className, ...props },
  ref,
) {
  return (
    <div
      ref={ref}
      data-slot="card"
      className={cn(
        "flex flex-col rounded-lg border bg-card text-card-foreground shadow-elevation-1",
        className,
      )}
      {...props}
    />
  );
});

/** Header region — groups the title and description with consistent padding. */
export const CardHeader = forwardRef<HTMLDivElement, CardHeaderProps>(function CardHeader(
  { className, ...props },
  ref,
) {
  return (
    <div
      ref={ref}
      data-slot="card-header"
      className={cn("flex flex-col gap-1.5 p-6", className)}
      {...props}
    />
  );
});

/** Card title — a semantic heading. */
export const CardTitle = forwardRef<HTMLHeadingElement, CardTitleProps>(function CardTitle(
  { className, ...props },
  ref,
) {
  return (
    <h3
      ref={ref}
      data-slot="card-title"
      className={cn("text-lg font-semibold leading-none tracking-tight", className)}
      {...props}
    />
  );
});

/** Supporting description text below the title. */
export const CardDescription = forwardRef<HTMLParagraphElement, CardDescriptionProps>(
  function CardDescription({ className, ...props }, ref) {
    return (
      <p
        ref={ref}
        data-slot="card-description"
        className={cn("text-sm text-muted-foreground", className)}
        {...props}
      />
    );
  },
);

/** Main body region of the card. */
export const CardContent = forwardRef<HTMLDivElement, CardContentProps>(function CardContent(
  { className, ...props },
  ref,
) {
  return (
    <div ref={ref} data-slot="card-content" className={cn("p-6 pt-0", className)} {...props} />
  );
});

/** Footer region — a flex row for actions, aligned to the content padding. */
export const CardFooter = forwardRef<HTMLDivElement, CardFooterProps>(function CardFooter(
  { className, ...props },
  ref,
) {
  return (
    <div
      ref={ref}
      data-slot="card-footer"
      className={cn("flex items-center p-6 pt-0", className)}
      {...props}
    />
  );
});
