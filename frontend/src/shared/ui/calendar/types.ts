import type { Matcher } from "react-day-picker";

/**
 * What the platform's calendar accepts — deliberately not the library's own props.
 *
 * `DayPickerProps` is a union discriminated on `mode`, so a wrapper that spreads
 * it cannot stay type-safe about which arm it is in (and under
 * `exactOptionalPropertyTypes` it does not type-check at all). Listing the props
 * by name costs a few lines and buys a surface that says what it supports: one
 * date, a month to open on, and a rule for what cannot be picked. Every field on
 * this platform wants exactly that — a birth date, a deadline, an opening day.
 * A range picker is a separate component the day something needs one.
 */
export interface CalendarProps {
  /** The chosen day, or nothing chosen yet. */
  selected?: Date | undefined;
  /** Called with the new day, or `undefined` when the same day is clicked again. */
  onSelect?: (date: Date | undefined) => void;
  /** Month to open on when nothing is selected. Defaults to the current one. */
  defaultMonth?: Date;
  /** Days that cannot be picked — a past deadline, say. */
  disabled?: Matcher | Matcher[];
  /** Move focus into the grid on mount. Set when opening in a popover. */
  autoFocus?: boolean;
  /** First selectable year. Defaults to a century back — birth dates live there. */
  fromYear?: number;
  /** Last selectable year. Defaults to five years out — festivals are planned ahead. */
  toYear?: number;
  className?: string;
}
