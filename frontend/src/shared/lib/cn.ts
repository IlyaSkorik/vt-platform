import { type ClassValue, clsx } from "clsx";
import { twMerge } from "tailwind-merge";

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
