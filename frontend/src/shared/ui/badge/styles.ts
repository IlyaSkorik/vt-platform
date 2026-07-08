import { cva } from "class-variance-authority";

/**
 * Badge visual contract. Colours resolve through semantic status tokens
 * (subtle `*-surface` background + readable status text), never raw palette
 * values — so a theme switch restyles every badge without touching this file.
 */
export const badgeVariants = cva(
  "inline-flex items-center gap-1 whitespace-nowrap rounded-full border font-medium select-none [&_svg]:pointer-events-none [&_svg]:shrink-0",
  {
    variants: {
      variant: {
        primary: "border-transparent bg-primary text-primary-foreground",
        secondary: "border-transparent bg-secondary text-secondary-foreground",
        success: "border-transparent bg-success-surface text-success",
        warning: "border-transparent bg-warning-surface text-warning",
        danger: "border-transparent bg-danger-surface text-danger",
        info: "border-transparent bg-info-surface text-info",
        outline: "border-border bg-background text-foreground",
        neutral: "border-transparent bg-muted text-muted-foreground",
      },
      size: {
        sm: "h-5 px-2 text-xs [&_svg]:size-3",
        md: "h-6 px-2.5 text-xs [&_svg]:size-3.5",
      },
    },
    defaultVariants: {
      variant: "neutral",
      size: "md",
    },
  },
);
