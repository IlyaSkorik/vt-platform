import { cva } from "class-variance-authority";

/**
 * Alert visual contract. Every colour resolves through semantic status tokens
 * (surface + text + border), so each variant themes automatically and never
 * hard-codes a palette value (WCAG 2.1 AA).
 */
export const alertVariants = cva(
  "relative flex w-full items-start gap-3 rounded-md border px-4 py-3 text-sm",
  {
    variants: {
      variant: {
        info: "border-info/30 bg-info-surface text-info",
        success: "border-success/30 bg-success-surface text-success",
        warning: "border-warning/30 bg-warning-surface text-warning",
        danger: "border-danger/30 bg-danger-surface text-danger",
      },
    },
    defaultVariants: {
      variant: "info",
    },
  },
);
