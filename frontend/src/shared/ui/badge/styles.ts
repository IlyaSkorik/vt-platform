import { cva } from "class-variance-authority";

/**
 * Badge visual contract. Colours resolve through semantic status tokens
 * (subtle `*-surface` background + readable status text), never raw palette
 * values — so a theme switch restyles every badge without touching this file.
 *
 * The pill never grows past its container: `max-w-full` caps it and the label
 * inside `Badge` truncates, so a long organisation name can no longer push the
 * badge outside the card that holds it.
 */
export const badgeVariants = cva(
  "inline-flex max-w-full items-center gap-1 overflow-hidden whitespace-nowrap rounded-full border font-medium select-none [&_svg]:pointer-events-none [&_svg]:shrink-0",
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
        /**
         * The brand chip: a transparent capsule outlined in `светлый акцент`, cut
         * to the brand's 15px corner rather than fully rounded.
         *
         * Not a status, which is why it is here beside `outline` rather than in
         * that family — it labels what a thing *is* (a nomination, a genre, a
         * format), so it carries no semantic colour to be read as good or bad.
         * The two-pixel line is what makes it legible as a chip at all once the
         * fill is gone; at one pixel against a pale page it reads as a text box.
         */
        brand: "rounded-brand border-2 border-brand-line-soft bg-transparent text-foreground",
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
