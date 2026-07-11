import { cva } from "class-variance-authority";

/**
 * Button visual contract. All colours resolve through semantic Tailwind
 * utilities (which are wired to `var(--…)` tokens), never raw palette values —
 * so a theme switch restyles every button without touching this file.
 */
export const buttonVariants = cva(
  "inline-flex cursor-pointer items-center justify-center gap-2 whitespace-nowrap rounded-md font-medium transition-colors outline-none focus-visible:ring-[3px] focus-visible:ring-ring/50 disabled:pointer-events-none disabled:opacity-50 aria-disabled:pointer-events-none aria-disabled:opacity-50 shrink-0 select-none [&_svg]:pointer-events-none [&_svg]:shrink-0",
  {
    variants: {
      variant: {
        primary: "bg-primary text-primary-foreground shadow-elevation-1 hover:bg-primary/90",
        secondary:
          "bg-secondary text-secondary-foreground shadow-elevation-1 hover:bg-secondary/80",
        outline:
          "border border-input bg-background text-foreground shadow-elevation-1 hover:bg-accent hover:text-accent-foreground",
        ghost: "text-foreground hover:bg-accent hover:text-accent-foreground",
        danger: "bg-danger text-danger-foreground shadow-elevation-1 hover:bg-danger/90",
        success: "bg-success text-success-foreground shadow-elevation-1 hover:bg-success/90",
      },
      size: {
        xs: "h-7 gap-1.5 px-2.5 text-xs [&_svg]:size-3.5",
        sm: "h-8 px-3 text-sm [&_svg]:size-4",
        md: "h-9 px-4 text-sm [&_svg]:size-4",
        lg: "h-10 px-5 text-base [&_svg]:size-5",
        xl: "h-12 px-6 text-base [&_svg]:size-5",
      },
      iconOnly: {
        true: "px-0 aspect-square",
        false: "",
      },
    },
    compoundVariants: [
      { iconOnly: true, size: "xs", class: "size-7" },
      { iconOnly: true, size: "sm", class: "size-8" },
      { iconOnly: true, size: "md", class: "size-9" },
      { iconOnly: true, size: "lg", class: "size-10" },
      { iconOnly: true, size: "xl", class: "size-12" },
    ],
    defaultVariants: {
      variant: "primary",
      size: "md",
      iconOnly: false,
    },
  },
);
