import { type ClassValue, clsx } from "clsx";
import { extendTailwindMerge } from "tailwind-merge";

/**
 * tailwind-merge ships with Tailwind's stock scales and nothing else. A project
 * token that adds a *name* to a scale — `rounded-brand`, `shadow-elevation-1` —
 * is invisible to it: it cannot tell the class belongs to the border-radius
 * group, so it does not drop the `rounded-md` sitting beside it and both survive
 * into the DOM. Whichever rule the stylesheet happens to emit last then wins,
 * which is how a `rounded-brand` passed to a Button lost silently to the
 * variant's own `rounded-md` and every radius on the landing looked the same.
 *
 * Naming the extra scale values here is what makes them behave like any other
 * utility: last one wins, the rest are dropped. Anything added to the `--radius-*`
 * or `--shadow-*` namespaces in `shared/theme` belongs in this list too.
 */
const twMerge = extendTailwindMerge({
  extend: {
    theme: {
      radius: ["brand"],
      shadow: [
        "elevation-1",
        "elevation-2",
        "elevation-3",
        "glow-primary",
        "glow-soft",
        "glow-strong",
      ],
    },
  },
});

/**
 * Merge conditional class names and de-duplicate conflicting Tailwind
 * utilities (later classes win). The canonical helper used by every in-repo
 * shadcn/ui component.
 *
 * @example cn("px-2", condition && "px-4") // => "px-4"
 */
export function cn(...inputs: ClassValue[]): string {
  return twMerge(clsx(inputs));
}
