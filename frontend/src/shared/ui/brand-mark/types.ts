import type * as React from "react";

/**
 * The mark takes no colour props: the plate is `primary` and the comet is `brand-mark`,
 * decided once in the component. Size and corner radius come through `className`.
 */
export interface BrandMarkProps extends Omit<React.ComponentPropsWithoutRef<"span">, "children"> {}
