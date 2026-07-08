import type { ReactNode } from "react";

/**
 * Cross-cutting utility types shared across layers.
 *
 * Domain-specific models belong to their `entities/*` slice; only truly generic
 * helpers live here.
 */

/** A value that may be `null`. */
export type Nullable<T> = T | null;

/** A value that may be absent. */
export type Maybe<T> = T | null | undefined;

/** Make the listed keys of `T` optional. */
export type PartialBy<T, K extends keyof T> = Omit<T, K> & Partial<Pick<T, K>>;

/** A React component that accepts children. */
export type WithChildren<P = unknown> = P & { children?: ReactNode };

/** Deep-readonly view of a value. */
export type DeepReadonly<T> = T extends (infer U)[]
  ? ReadonlyArray<DeepReadonly<U>>
  : T extends object
    ? { readonly [K in keyof T]: DeepReadonly<T[K]> }
    : T;
