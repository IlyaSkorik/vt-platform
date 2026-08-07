import type * as React from "react";
import type { Matcher } from "react-day-picker";

/** Field anatomy shared with `Input`, so the two sit level in a form grid. */
interface FieldProps {
  id?: string;
  label?: React.ReactNode;
  description?: React.ReactNode;
  /** Error message. When set, the trigger is marked invalid and styled as error. */
  error?: React.ReactNode;
  required?: boolean;
  disabled?: boolean;
  /** Wrapper element class, for layout composition. */
  containerClassName?: string;
  className?: string;
}

export interface DatePickerProps extends FieldProps {
  /** `YYYY-MM-DD`, or empty. The same string the native `<input type="date">` gave. */
  value: string;
  onChange: (value: string) => void;
  /** Shown on the trigger when nothing is chosen. */
  placeholder?: string;
  /** Days that cannot be picked. */
  disabledDates?: Matcher | Matcher[];
  fromYear?: number;
  toYear?: number;
  /** Offer a "clear" action once a date is set. On by default. */
  clearable?: boolean;
}

export interface DateTimePickerProps extends Omit<DatePickerProps, "value" | "onChange"> {
  /** `YYYY-MM-DDTHH:mm`, or empty — as `<input type="datetime-local">` produced. */
  value: string;
  onChange: (value: string) => void;
  /** Label for the time half. Defaults to «Время». */
  timeLabel?: React.ReactNode;
}
