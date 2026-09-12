import { cva } from "class-variance-authority";

/**
 * Button visual contract. All colours resolve through semantic Tailwind
 * utilities (which are wired to `var(--…)` tokens), never raw palette values —
 * so a theme switch restyles every button without touching this file.
 *
 * **Which variant.** The one rule worth knowing, because it has been got wrong
 * twice: `ghost` is text until it is hovered, and a touch screen never hovers.
 * So it belongs only where the surrounding context already says "control" —
 * an icon in a toolbar or a dense list row, a link in a navigation bar, a
 * "see all" beside a card heading. Anything a person has to *find* in order to
 * act — delete, reset, copy, download, add, cancel — is `outline` at least.
 * If in doubt, ask whether the control is still discoverable with the mouse
 * across the room; `ghost` is not.
 *
 * Motion: the transition covers shadow and transform as well as colour, and a press
 * shrinks the button very slightly. This is the one place worth spending motion on —
 * it is the control the reader actually touches, and the acknowledgement is what makes
 * a tap feel received rather than merely registered. Kept at 2% so it reads as give,
 * not as bounce; the global reduced-motion reset removes it entirely.
 */
export const buttonVariants = cva(
  "inline-flex cursor-pointer items-center justify-center gap-2 whitespace-nowrap rounded-md font-medium transition-[color,background-color,border-color,box-shadow,transform] duration-[var(--duration-fast)] ease-standard active:scale-[0.98] outline-none focus-visible:ring-[3px] focus-visible:ring-ring/50 disabled:pointer-events-none disabled:opacity-50 disabled:active:scale-100 aria-disabled:pointer-events-none aria-disabled:opacity-50 aria-disabled:active:scale-100 shrink-0 select-none [&_svg]:pointer-events-none [&_svg]:shrink-0",
  {
    variants: {
      variant: {
        primary: "bg-primary text-primary-foreground shadow-elevation-1 hover:bg-primary/90",
        // Bordered, not merely filled. The fill is one step off the surface it sits
        // on (0.17 against a 0.135 card in the dark theme), and the only other thing
        // marking it as a control is a drop shadow — which a dark surface does not
        // show at all. On light the shadow carried it; on dark the button simply
        // disappeared. The border is the affordance that works in both.
        secondary:
          "border border-border bg-secondary text-secondary-foreground shadow-elevation-1 hover:bg-secondary/80",
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
