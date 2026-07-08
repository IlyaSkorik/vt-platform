/**
 * Public API of the `shared/ui` segment — the in-repo design system.
 *
 * Components here are owned (shadcn/ui + Radix primitives), accessible by
 * default, and free of any business/domain knowledge. New primitives are added
 * via the shadcn CLI (`components.json`) or hand-authored to the same standard.
 */
export { Button, type ButtonProps, buttonVariants } from "./button";
