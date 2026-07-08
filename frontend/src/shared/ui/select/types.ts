import type { Select as SelectPrimitive } from "radix-ui";
import type * as React from "react";

export type SelectSize = "sm" | "md";

export interface SelectTriggerProps
  extends React.ComponentPropsWithoutRef<typeof SelectPrimitive.Trigger> {
  /** Trigger height/padding preset. */
  size?: SelectSize;
  /** Marks the trigger invalid and styles it as error. */
  invalid?: boolean;
}

export interface SelectContentProps
  extends React.ComponentPropsWithoutRef<typeof SelectPrimitive.Content> {}

export interface SelectItemProps
  extends React.ComponentPropsWithoutRef<typeof SelectPrimitive.Item> {}

export interface SelectLabelProps
  extends React.ComponentPropsWithoutRef<typeof SelectPrimitive.Label> {}

export interface SelectSeparatorProps
  extends React.ComponentPropsWithoutRef<typeof SelectPrimitive.Separator> {}

/** A single selectable option for the convenience {@link Select} API. */
export interface SelectOption {
  /** Submitted value; must be unique within the option set. */
  value: string;
  /** Visible option text. */
  label: React.ReactNode;
  /** Prevents selection of this option. */
  disabled?: boolean;
}

/** A titled cluster of options for the convenience {@link Select} API. */
export interface SelectOptionGroup {
  /** Group heading. */
  label: React.ReactNode;
  /** Options within the group. */
  options: SelectOption[];
}

export interface SelectProps
  extends Omit<React.ComponentPropsWithoutRef<typeof SelectPrimitive.Root>, "children"> {
  /** Options, either flat or grouped. */
  options: SelectOption[] | SelectOptionGroup[];
  /** Placeholder shown when no value is selected. */
  placeholder?: string;
  /** Visible field label, associated with the trigger. */
  label?: React.ReactNode;
  /** Helper text shown beneath the field when there is no error. */
  description?: React.ReactNode;
  /** Error message. When set, the trigger is marked invalid and styled as error. */
  error?: React.ReactNode;
  /** Marks the field as required (renders an asterisk). */
  required?: boolean;
  /** Trigger size. */
  size?: SelectSize;
  /** Trigger element class. */
  className?: string;
  /** Wrapper element class, for layout composition. */
  containerClassName?: string;
  /** Explicit trigger id (defaults to a generated one). */
  id?: string;
  /** Extra ids to append to the trigger's `aria-describedby`. */
  "aria-describedby"?: string;
}
