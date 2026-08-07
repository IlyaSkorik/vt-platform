import type * as React from "react";

export interface TimePickerProps {
  /** `HH:mm`, or empty. The same string `<input type="time">` produced. */
  value: string;
  /** Called with a normalised `HH:mm`, or `""` once the field is cleared. */
  onChange: (value: string) => void;
  id?: string;
  label?: React.ReactNode;
  description?: React.ReactNode;
  /** Error message. When set, the field is marked invalid and styled as error. */
  error?: React.ReactNode;
  required?: boolean;
  disabled?: boolean;
  /** Minutes offered in the picker's second column. 5 by default. */
  minuteStep?: number;
  /** Wrapper element class, for layout composition. */
  containerClassName?: string;
  className?: string;
}
